from swagger_server import logger_config as log
import swagger_server.mal2.db.model.db_model as db_model
import swagger_server.mal2.sources.fakeshopdb.fake_shop_db_utils as fakeshopdb_utils
import requests
import json
import datetime as dt
from typing import List
import numpy as np
import os, sys
import pandas as pd

FAKE_SHOP_API_HOST =  "https://db.malzwei.at/"
FAKE_SHOP_API_HOST_DEV =  "https://db-dev.malzwei.at/"

def load_api_token():
        #load api key for fake-shop db interaction from disk - default token provided in repo
        try:
            api_key_loc = os.path.abspath(os.getcwd())+"/swagger_server/resources/data/fakeshopdb_api_access_token.txt".replace('/',os.path.sep)
            with open(api_key_loc) as f:
                api_key = f.read()
            return api_key
        except:
            log.mal2_fakeshop_db_log.warn("load_api_token failed - location: %s exists: %s ",api_key_loc, os.path.exists(api_key_loc))
            raise None

def submit_result_for_inspection(site,*model_scores):
    """aggregates the model(s) prediction(s) and posts the site to mal2 website database of potential fake-shops for further manual expert evaluation)
    
    Arguments:
        site {Str} -- site to push to fake-shop website database for e.g. "elektronio.de"
        model_score {Float} -- risk_score of beeing fake determined by the mal2 prediction model

    Returns:
        submission_resp {Str} -- human readable response of status
    """

    def translate_model_score(model_score):
        #translates score to fake-shop db risk_types very low, low, below average, above average, high, very high, unknown
        #https://db-dev.malzwei.at/admin/mal2_db/websiteriskscore/
        range_low = np.arange(1, 100, 0.01)
        score = model_score * 100
        if np.logical_and(score >= 0, score < 10):
            #id for very low
            return 5
        elif np.logical_and(score >= 10, score < 25):
            #id for low
            return 1
        elif np.logical_and(score >= 25, score < 50):
            #id for below average
            return 2
        elif np.logical_and(score >= 50, score < 80):
            #id for above average
            return 7
        elif np.logical_and(score >= 80, score < 90):
            #id for high
            return 3
        elif np.logical_and(score >= 90, score <=100):
            #id for very high
            return 6
        else:
            #id for unknown
            return 4

    def convert_to_url(url):
        if url.startswith('file://'):
            return url
        if url.startswith('www.'):
            url = 'http://' + url[len('www.'):]
        if url.startswith('http://www.'):
            url = 'http://' + url[len('http://www.'):]
        if url.startswith('https://www.'):
            url= 'http://' + url[len('https://www.'):]
        if url.startswith('https://'):
            url = 'http://' + url[len('https://'):]
        if not url.startswith('http://'):
            url = 'http://' + url
        return url

    #combine the predictions (xgboost + random_forest) to aggregated score
    fake_score = 0
    model_count = 0
    for model_score in model_scores:
        fake_score += model_score
        model_count += 1
    fake_score = fake_score / model_count

    #swagger-api: https://db.malzwei.at/api/
    api_url = FAKE_SHOP_API_HOST+'api/v1/website/'
    api_token = load_api_token()

    #reported_by https://db-dev.malzwei.at/admin/mal2_db/websitereportedby/
    json_data = {"url": "{}".format(convert_to_url(site)), "risk_score": translate_model_score(fake_score), "reported_by": 2}
    submission_resp = ""

    log.mal2_fakeshop_db_log.info("submitting result for inspection {} with risk-score {} to: {}".format(site,'%.2f' % fake_score,api_url))

    headers = {'content-type': 'application/json', 'Authorization':'Token {}'.format(api_token) }
    resp = requests.post(api_url, data=json.dumps(json_data), headers=headers, timeout=10)

    #parse response
    if resp.status_code == 201:
        resp_dict= resp.json()
        #there should be a create_at entry in the response json
        if resp_dict['created_at']:
            #record date as return message
            submission_resp = dt.datetime.fromisoformat(resp_dict['created_at'])
            submission_resp = dt.datetime.strftime(submission_resp,"%d.%m.%Y %H:%M")
            log.mal2_fakeshop_db_log.info("recorded website id: {}, creation date: {}, url: {}".format(resp_dict['id'],submission_resp,resp_dict['url']))
        else:
            log.mal2_fakeshop_db_log.exception("errors parsing the API response")
    #in case website already existed
    elif resp.status_code == 400:
        submission_resp = "website previously recorded for manual inspection"
        log.mal2_fakeshop_db_log.info("existing website in fake-shop-db - skipping result submission")
    elif resp.status_code == 403:
        log.mal2_fakeshop_db_log.warn("invalid credentials status: %s text: %s",resp.status_code,resp.text)
    else:
        log.mal2_fakeshop_db_log.warn("error status: %s text: %s",resp.status_code,resp.text)

    return submission_resp


def get_all_blacklist_entries(limit_imported_items:int=-1):
    """queries the mal2 central fake-shop db for all website entries of the type Markenfälscher and Fake-Shop
    returns a pandas dataframe with [url, created_at, website_type]
    """
    #note: "-created_at" sorting desc i.e. newest elements first
    fake_shop_api_url = FAKE_SHOP_API_HOST+'api/v1/website/fake_shop/?ordering=-created_at'
    brand_counterfeiter_api_url = FAKE_SHOP_API_HOST+'api/v1/website/brand_counterfeiter/?ordering=-created_at'
    api_token = load_api_token()
    ret = []

    log.mal2_fakeshop_db_log.info("checking fakeshopdb for blacklist entries (Fake-Shop and brand_counterfeiters)")
    #fetch all fake_shops 
    ret = fakeshopdb_utils.get_website_entry_list(fake_shop_api_url,api_token,ret,fetch_screenshots=True,limit_imported_items=limit_imported_items)
    #fetch all counterfeit shops and append
    ret = fakeshopdb_utils.get_website_entry_list(brand_counterfeiter_api_url,api_token,ret,fetch_screenshots=True,limit_imported_items=limit_imported_items)
    
    if len(ret) < 1:
        df = pd.DataFrame(columns={'url','website_type','created_at'})
    else:    
        df = pd.DataFrame(ret) 
        df['website_type'] = df['website_type'].apply(fakeshopdb_utils.translate_blacklist_type)
    
    log.mal2_fakeshop_db_log.info("returning element count: %s",df.size)
    return df

def get_all_ignored_entries(limit_imported_items:int=-1):
    """queries the mal2 central fake-shop db for all website entries of the tye "Keine Überprüfung notwendig" as well as "checked and not fake"
    that shell be added to the list of ignored domains for the plugin. e.g. orf.at, amazon.at
    returns a pandas dataframe with [url, created_at, website_type]
    """
    #note: "-created_at" sorting desc i.e. newest elements first
    no_verification_requ_api_url = FAKE_SHOP_API_HOST+'api/v1/website/no_verification_required/?ordering=-created_at'
    verified_no_fake_api_url = FAKE_SHOP_API_HOST+'api/v1/db/no_fake/?ordering=-created_at'
    api_token = load_api_token()
    ret = []

    log.mal2_fakeshop_db_log.info("checking fakeshopdb for ignored domain entries")
    #fetch all websites that require no verification 
    ret = fakeshopdb_utils.get_website_entry_list(no_verification_requ_api_url,api_token,ret,limit_imported_items=limit_imported_items)
    #fetch all websites that are verified no fakes 
    ret = fakeshopdb_utils.get_website_entry_list(verified_no_fake_api_url,api_token,ret,limit_imported_items=limit_imported_items)

    if len(ret) < 1:
        df = pd.DataFrame(columns={'url','company_type','created_at'})
    else:    
        df = pd.DataFrame(ret) 
        df['company_type'] = df['company_type'].apply(fakeshopdb_utils.translate_ignorelist_category)
        # only select others than web-shops, as web-shops are Whitelisted all others Ignorelisted
        df = df[df.company_type != db_model.EnumIgnoreListCategory.ecommerce]

    log.mal2_fakeshop_db_log.info("returning element count: %s",df.size)
    return df

def get_all_whitelist_entries(limit_imported_items:int=-1):
    """queries the mal2 central fake-shop db for all website entries of the tye "Keine Überprüfung notwendig" as well as "checked and not fake"
    that shell be added to the list of whitelisted domains for the plugin. e.g. happysocks.com
    returns a pandas dataframe with [url, created_at, company_type]
    """
    #note: "-created_at" sorting desc i.e. newest elements first
    no_verification_requ_api_url = FAKE_SHOP_API_HOST+'api/v1/website/no_verification_required/?ordering=-created_at'
    verified_no_fake_api_url = FAKE_SHOP_API_HOST+'api/v1/db/no_fake/?ordering=-created_at'
    api_token = load_api_token()
    ret = []

    log.mal2_fakeshop_db_log.info("checking fakeshopdb for ignored domain entries")
    #fetch all websites that require no verification 
    ret = fakeshopdb_utils.get_website_entry_list(no_verification_requ_api_url,api_token,ret,limit_imported_items=limit_imported_items)
    #fetch all websites that are verified no fakes 
    ret = fakeshopdb_utils.get_website_entry_list(verified_no_fake_api_url,api_token,ret,limit_imported_items=limit_imported_items)

    if len(ret) < 1:
        df = pd.DataFrame(columns={'url','created_at'})
    else:    
        df = pd.DataFrame(ret) 
        df['company_type'] = df['company_type'].apply(fakeshopdb_utils.translate_ignorelist_category)
        # only select web-shops, all others Ignorelisted
        df = df[df.company_type == db_model.EnumIgnoreListCategory.ecommerce]
        #required field company_name for whitelist, but as not in db we need to add one
        df['company_name'] = df['url'].apply(lambda x: ' '.join(x.split('.')[:-1]))
        

    log.mal2_fakeshop_db_log.info("returning element count: %s",df.size)
    return df
