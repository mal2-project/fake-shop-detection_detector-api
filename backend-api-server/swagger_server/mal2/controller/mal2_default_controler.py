import swagger_server.controllers.plugin_controller as api
import swagger_server.mal2.verify.verify_site as mal2_verify
import swagger_server.mal2.db.handler.db_handler as db
import swagger_server.mal2.db.model.db_model as db_model
import swagger_server.mal2.sources.fakeshopdb.fake_shop_db as mal2_fakeshopdb
import swagger_server.mal2.sources.waybackmachine.internet_archive as waybackmachine
from swagger_server import logger_config as log
import numpy as np
import datetime as dt
from typing import List
from w3lib.url import url_query_cleaner
from url_normalize import url_normalize
from w3lib.url import url_query_cleaner
from urllib.parse import urlparse
#import urllib.request
import requests
import random
from time import sleep

def extract_base_url(url):
    """validity of http url is checked by swagger - extracts the netloc from the url, removes trailing path or www
    and returns the baseurl e.g. google.at

    """
    #validity of url is checked by swagger
    url = url_normalize(url)
    #removes http https etc
    url = urlparse(url).netloc
    #but not query params
    url = url.replace("www.","")
    if url.endswith('/'):
        url = url[:-1]
    return url

def check_db_load_ok():
    #https://stackoverflow.com/questions/34775501/how-could-i-check-the-number-of-active-sqlalchemy-connections-in-a-pool-at-any-g
    #make sure at least minimum of 10 connections remain in the pool for other functions of the app to use 
    if db.engine.pool.checkedout() > (db.dbpool_size+db.dbmax_overflow)- 10:
        log.mal2_rest_log.warning("check_db_load_is_ok? False. Checkedout engine pool: %s. Rejecting incoming service request by returning 401"%db.engine.pool.checkedout())
        return False, "we're experiencing a high number requests. Please try again later."
    else:
        log.mal2_rest_log.info("check_db_load_is_ok? True. Checkedout engine pool: %s."%db.engine.pool.checkedout())
        return True, "glad to take on more"

def analyze_post(site:api.Site)->api.SiteAnalysisResult:
    #input
    url = extract_base_url(site._site_base_url)
    clientID = site._client_id
    reprocess = site._re_process
    log.mal2_rest_log.info("analyze_post for url %s, clientId %s reprocess %s",url,clientID,reprocess)
    
    #sanity check for all public controller methods on service load
    load_ok, feedback = check_db_load_ok()
    if load_ok == False:
        #return 401 which client can specifically target
        return feedback, 401
    
    #ret
    ret = api.SiteAnalysisResult()

    def handle_reprocess(url):

        def submit_prediction_to_waybackmachine(url):
            #call internet archive to add archived snapshot
            arch_time, arch_url = waybackmachine.get_entry_from_wayback_machine(url, retry=1)

            def get_day_dif_to_today(arch_time):
                if arch_time==None:
                    return -1
                else:
                    today =  dt.date.today()
                    archive_date = dt.datetime.strptime(arch_time,"%d.%m.%Y %H:%M")
                    diff = today - archive_date .date()
                    return diff.days

            if not arch_url:
                #shop does not yet exist - submit site for internet archive snapshot
                waybackmachine.submit_to_wayback_machine(url)
                arch_time, arch_url = waybackmachine.get_entry_from_wayback_machine(url, retry=3)
            elif get_day_dif_to_today(arch_time) > 180:
                #if archive is older than 180 days re-request a snapshot
                waybackmachine.submit_to_wayback_machine(url)
                arch_time, arch_url = waybackmachine.get_entry_from_wayback_machine(url, retry=3)
            return arch_time, arch_url

        def submit_prediction_to_mal2_db_for_inspection(url, *prediction_dbs):
            fake_score = 0
            prediction_count = 0
            for prediction_db in prediction_dbs:
                fake_score += prediction_db.prediction
                prediction_count += 1
                log.mal2_rest_log.info("adding prediction to aggregate score %s",prediction_db.__repr__)
            fake_score = fake_score / prediction_count   
            log.mal2_rest_log.info("aggregate model predicted risk-score of %s for %s ",url, fake_score)

            #FIME: only for plugin test period, change back to 0.6 afterwards
            if fake_score >= 0.01:
                #submt to fake-shop db
                db_submit_message = mal2_fakeshopdb.submit_result_for_inspection(url,fake_score)
                log.mal2_rest_log.info("submitted potential fake-shop: %s with risk-score: %s to central mal2 fake-shop db. status: %s",url,fake_score,db_submit_message)
            else:
                log.mal2_rest_log.info("skipping submission to mal2 fakeshop db. Risk-Score below threshold.")

            if fake_score >= 0.8:
                try:
                    #submit to waybackmachine
                    arch_time, arch_url = submit_prediction_to_waybackmachine(url)
                    log.mal2_rest_log.info("submitted potential fake-shop to waybackmachine: archive date: %s archive url: %s",arch_time, arch_url)
                except Exception as e:
                    log.mal2_rest_log.info("failed submitting fake-shop to waybackmachine: %s",e)
            else:
                log.mal2_rest_log.info("skipping submission to waybackmachine. Risk-Score below threshold.")

        def update_processing_db_status(url:str, status:db_model.EnumPredictionProcessingStatus):
            pred_status_db = db.get_predictionstatus_db_entry_by_url(url)
            if pred_status_db == None:
                pred_status_db = db_model.PredictionStatus(url=url)
            pred_status_db.status = status
            log.mal2_rest_log.info("setting db processing status: %s for site: %s",status,url)
            db.commit_db_etnries(pred_status_db)


        log.mal2_rest_log.info("handle_reporcess for %s",url)
        #raises 400 exception (forwareded to ui) if url is offline
        check_site_is_online(url)

        #raises 400 exception (forwarded to ui) if url either being processed right now (by a different request) or was previously processing but predicting failed 
        check_site_is_processing(url)

        #set status to prediction processing in db
        update_processing_db_status(url,db_model.EnumPredictionProcessingStatus.processing)

        log.mal2_rest_log.info("repredicting url %s",url)
        #call the mal2-model's verify to get fake-score prediction
        try:
            xg_fake_score, xg_htmlhash, xg_model_name, xg_model_version = mal2_verify.get_model_prediction(url,"xgboost",use_cache=False, keep_cache=True)
            rf_fake_score, rf_htmlhash, rf_model_name, rf_model_version = mal2_verify.get_model_prediction(url,"random_forest",use_cache=True, keep_cache=True)
            nn_fake_score, nn_htmlhash, nn_model_name, nn_model_version = mal2_verify.get_model_prediction(url,"neural_net",use_cache=True, keep_cache=False)
        except Exception as e:
            #set status to prediction processing failed in db
            update_processing_db_status(url,db_model.EnumPredictionProcessingStatus.failed)
            #forward exception
            raise e

        site_db = None
        xg_prediction_db = None
        rf_prediction_db = None
        nn_prediction_db = None

        if (xg_fake_score != None) and (rf_fake_score != None) and (nn_fake_score != None):
            #get or create the db entity site
            site_db = db.get_site_db_entry_by_url(url)
            if site_db == None:
                #no existing site - need to create
                site_db = db_model.Site(url=url)
            #create the db entity predictions
            xg_prediction_db = db_model.Prediction(site=site_db, html_hash = xg_htmlhash, prediction=float(xg_fake_score), algorithm=xg_model_name, model_version=xg_model_version)
            rf_prediction_db = db_model.Prediction(site=site_db, html_hash = rf_htmlhash, prediction=float(rf_fake_score), algorithm=rf_model_name, model_version=rf_model_version)
            nn_prediction_db = db_model.Prediction(site=site_db, html_hash = nn_htmlhash, prediction=float(nn_fake_score), algorithm=nn_model_name, model_version=nn_model_version)
            
            #set status to prediction processing completed in db
            update_processing_db_status(url,db_model.EnumPredictionProcessingStatus.completed)
            
            #submit results to db
            db.commit_db_etnries(site_db,xg_prediction_db,rf_prediction_db,nn_prediction_db)
            site_db = db.get_site_db_entry_by_url(url)

            #check if we need to report object to central db for manual inspection
            submit_prediction_to_mal2_db_for_inspection(url,xg_prediction_db,rf_prediction_db, nn_prediction_db)
        return site_db, xg_prediction_db, rf_prediction_db, nn_prediction_db
    

    def handle_noreprocess(url):
        log.mal2_rest_log.info("handle_noreprocess: checking for existing entry for url %s",url)
        site_db = db.get_site_db_entry_by_url(url)
        xg_prediction_db = None
        rf_prediction_db = None
        nn_prediction_db = None
        #check site known
        if site_db == None:
            # unknown site - re-process
            log.mal2_rest_log.info("unknown site - process url %s",url)
            site_db, xg_prediction_db, rf_prediction_db, nn_prediction_db = handle_reprocess(url)
        else:
            #check on an existing prediction
            xg_prediction_db = db.get_prediction_db_entry_by_site(site_db,"xgboost")
            rf_prediction_db = db.get_prediction_db_entry_by_site(site_db,"random_forest")
            nn_prediction_db = db.get_prediction_db_entry_by_site(site_db,"neural_net")
            if xg_prediction_db == None or rf_prediction_db==None or nn_prediction_db==None:
                #no prediction - re-process
                log.mal2_rest_log.info("no existing aggregated prediction possible - reprocess url %s",url)
                site_db, xg_prediction_db, rf_prediction_db, nn_prediction_db = handle_reprocess(url)
            else:
                log.mal2_rest_log.info("returning existing predictions %s and %s and %s for url %s",xg_prediction_db.__repr__,rf_prediction_db.__repr__, nn_prediction_db.__repr__, url)

        return site_db, xg_prediction_db, rf_prediction_db, nn_prediction_db
    
    def translate_model_score(model_score:float):
        #translates score to fake-shop db risk_types very low, low, below average, above average, high, very high, unknown
        #https://db-dev.malzwei.at/admin/mal2_db/websiteriskscore/
        #risk_score: rest-api allowed_values = ["very low", "low", "below average", "above average", "high", "very high", "unknown"]
        range_low = np.arange(0, 100, 0.01)
        score = model_score * 100
        if np.logical_and(score >= 0, score < 10):
            return "very low"
        elif np.logical_and(score >= 10, score < 25):
            return "low"
        elif np.logical_and(score >= 25, score < 50):
            return "below average"
        elif np.logical_and(score >= 50, score < 80):
            return "above average"
        elif np.logical_and(score >= 80, score < 90):
            return "high"
        elif np.logical_and(score >= 90, score <=100):
            return "very high"
        else:
            return "unknown"
    
    def check_site_is_online(url:str):
        """
        probes if a website returns status 200 otherwise raises exception
        Args:
            url (str): baseurl e.g. malzwei.at to probe
        Returns:
            None - raises Exception if status != 200
        """
        try:
            resp = requests.get("http://"+url, headers={'User-Agent': 'Mozilla/5.0'}, verify=False)
            resp.raise_for_status()
        except Exception as err:
            log.mal2_rest_log.info("don't call analyze, as site %s is down with err: %s"%(url,err))
            #exception forwarded to ui
            raise Exception("website is offline") 

    def check_site_is_processing(url:str):
        """
        gate-keeper function, checks the db processingstatus db table to either determine if a different request is currently processing/predicting on that 
        url or if predicting on that url has previously failed if so raises exception
        Args:
            url (str): baseurl e.g. malzwei.at to check on status
        Returns:
            None - raises Exception if processing should be skipped
        """
        #check prediction previously failed - raises immediately?
        check_site_has_failed_processing(url)

        #FIXME plugin fires 3-5 analyze requests within few milli-seconds, to avoid bypassing before db processing status was set define random sleep
        #introducing thread sleep for a random period between 0 and 10 seconds and re-check db before returning status which allows one thread to win race
        sleep(random.uniform(0, 12)) #output random.uniform is float
        log.mal2_rest_log.debug("gatekeeper after sleep for %s"%(url))

        #re-check failed
        check_site_has_failed_processing(url)
        #check currently processing?
        pred_status_db = db.get_predictionstatus_db_entry_by_url(url)

        if pred_status_db != None and (
            pred_status_db.status == db_model.EnumPredictionProcessingStatus.processing or
            pred_status_db.status == db_model.EnumPredictionProcessingStatus.completed):
            # if occurred within last day raise 'site is processing'
            d = dt.datetime.today() - dt.timedelta(days=1)
            if pred_status_db.timestamp > d:
                log.mal2_rest_log.info("skipping analyze, as getting prediction on site %s is being currently processed by different request"%(url))
                raise Exception("skipping analyze as prediction is currently beeing processed on that site.")


    def check_site_has_failed_processing(url:str):
        """
        checks the db processingstatus db table to determine if predicting on that url has previously failed if so raises exception
        Args:
            url (str): baseurl e.g. malzwei.at to check on status
        Returns:
            None - raises Exception if processing has previously failed and i.e. should be skipped
        """
        #check prediction previously failed?
        pred_status_db = db.get_predictionstatus_db_entry_by_url(url, db_model.EnumPredictionProcessingStatus.failed)
        if pred_status_db != None:
            # if occurred within last 7 days ago raise 'failed to get prediction' - else retry
            d = dt.datetime.today() - dt.timedelta(days=7)
            if pred_status_db.timestamp > d:
                log.mal2_rest_log.info("skipping analyze, as getting prediction on site %s has previously failed"%(url))
                raise Exception("skipping analyze as prediction previously failed on that site.")
        

    def get_SiteAnalysisResult()->api.SiteAnalysisResult:
        
        def get_bwgi_list_SiteAnalysisResult()->api.SiteAnalysisResult:
            """chekcs and fetches a SiteAnalysisResult for elements in white, black grey and ignore lists for this site or None if site in no list

            Returns:
                [SiteAnalysisResult] -- swagger model SiteAnalysisResult return object or None
            """
            #allowed processors values are ['whitelist', 'blacklist', 'greylist', 'ignorelist', 'mal2_ai']
            site_db = db.get_site_db_entry_by_url(url)
            if site_db:
                if site_db.status == db_model.EnumSiteStatus.ignore:
                    #respond with ignorelist
                    ignorelist_db = db.get_best_ignorelist_db_entry_by_url(url)
                    if not ignorelist_db:
                        log.mal2_rest_log.warn("build get_SiteAnalysisResult failed to get ignorelist entry for url: %s",url)
                        raise Exception("database error") 
                    log.mal2_rest_log.info("respond with ignorelist SiteAnalysisResult for %s and status: %s",url,site_db.status)
                    return api.SiteAnalysisResult(site_id=site_db.id,site_url=site_db.url,analyzed_date_time=ignorelist_db.timestamp,processor="ignorelist",risk_score=translate_model_score(-1))
                elif site_db.status == db_model.EnumSiteStatus.greylist:
                    #respond with greylist
                    greylist_db = db.get_best_greylist_db_entry_by_url(url)
                    if not greylist_db:
                        log.mal2_rest_log.warn("build get_SiteAnalysisResult failed to get greylist entry for url: %s",url)
                        raise Exception("database error") 
                    log.mal2_rest_log.info("respond with greylist SiteAnalysisResult for %s and status: %s",url,site_db.status)
                    return api.SiteAnalysisResult(site_id=site_db.id,site_url=site_db.url,analyzed_date_time=greylist_db.timestamp,processor="greylist",risk_score=translate_model_score(-1))
                elif site_db.status == db_model.EnumSiteStatus.blacklist:
                    #respond with blacklist
                    blacklist_db = db.get_best_blacklist_db_entry_by_url(url)
                    if not blacklist_db:
                        log.mal2_rest_log.warn("build get_SiteAnalysisResult failed to get blacklist entry for url: %s",url)
                        raise Exception("database error") 
                    log.mal2_rest_log.info("respond with blacklist SiteAnalysisResult for %s and status: %s",url,site_db.status)
                    return api.SiteAnalysisResult(site_id=site_db.id,site_url=site_db.url,analyzed_date_time=blacklist_db.timestamp,processor="blacklist",risk_score=translate_model_score(1))
                elif site_db.status == db_model.EnumSiteStatus.whitelist:
                    #respond with whitelist
                    whitelist_db = db.get_best_whitelist_db_entry_by_url(url)
                    if not whitelist_db:
                        log.mal2_rest_log.warn("build get_SiteAnalysisResult failed to get whitelist entry for url: %s",url)
                        raise Exception("database error") 
                    log.mal2_rest_log.info("respond with whitelist SiteAnalysisResult for %s and status: %s",url,site_db.status)
                    return api.SiteAnalysisResult(site_id=site_db.id,site_url=site_db.url,analyzed_date_time=whitelist_db.timestamp,processor="whitelist",risk_score=translate_model_score(0))
            return None

        bwi_list_result = get_bwgi_list_SiteAnalysisResult()

        if bwi_list_result:
            #return swagger_server blacklist, whitelist or ignorelist return object
            return bwi_list_result
        else:
            #forward request to mal2-model for analysis
            log.mal2_rest_log.info("respond with mal2_ai SiteAnalysisResult for %s",url)
            
            if reprocess==True:
                #obey reprocess flag
                site_db, xg_prediction_db, rf_prediction_db, nn_prediction_db = handle_reprocess(url)
            else:
                #reply with existing prediction from db (if available) or process unknown site
                site_db, xg_prediction_db, rf_prediction_db, nn_prediction_db = handle_noreprocess(url)
            
            #create and return swagger_server return object
            aggr_fake_score = (xg_prediction_db.prediction + rf_prediction_db.prediction + nn_prediction_db.prediction) / 3
            return api.SiteAnalysisResult(site_id=site_db.id,site_url=site_db.url,analyzed_date_time=xg_prediction_db.timestamp,processor="mal2_ai",risk_score=translate_model_score(aggr_fake_score))
        
    ret = get_SiteAnalysisResult()
    #remove db session (and auto-create new Session)
    log.mal2_rest_log.debug("removing db session %s",db.Session)
    db.Session.remove()
    return ret

def __validate_inputs(limit,offset):
    if offset:
        try:
            offset = int(offset)
        except:
            raise ValueError("offset not a valid integer")
        if offset < 0:
            raise ValueError("offset larger zero required")
    if limit:
        try:
            limit = int(limit)
        except:
            raise ValueError("limit not a valid integer")
        if limit < 1:
            raise ValueError("limit larger zero required")
    
def __init_limit_and_offset_params(limit,offset):
    __validate_inputs(limit,offset)
    if offset:
        query_offset = offset
    else:
        query_offset = 0
    if limit:
        query_limit = limit
    else:
        query_limit = 0
    return query_limit, query_offset

def __build_BlacklistEntry(blacklist_db:db_model.Blacklist)->api.BlackListEntry:
    ret = api.BlackListEntry(
        site_id=blacklist_db.site.id,
        site_base_url=blacklist_db.site.url,
        blacklist_name=blacklist_db.blacklist_source.name.value,
        blacklist_description=blacklist_db.blacklist_source.description,
        blacklist_logo= blacklist_db.blacklist_source.logo_url,
        blacklist_url = blacklist_db.blacklist_source.url,
        site_added_date=blacklist_db.timestamp,
        site_type=blacklist_db.type.value,
        site_screenshot=blacklist_db.screenshot_link,
        site_information_link=blacklist_db.information_link
    )
    return ret

def blacklist_get(limit=None, offset=None, all=None, clientID=None)->List[api.BlackListEntry]:
    log.mal2_rest_log.info("blacklist_get limit %s, offset %s, all %s, clientId %s",limit,offset,all,clientID)

    #sanity check for all public controller methods on service load
    load_ok, feedback = check_db_load_ok()
    if load_ok == False:
        #return 401 which client can specifically target
        return feedback, 401

    ret = []
    if (all == True) or (not offset and not limit):
        # return all blacklists (note most current one per site if multiple from different bl sources exist per site)
        #get all sites
        bl_entries_db = db.get_all_best_blacklist_db_entries()
    else:
        pagesize, page = __init_limit_and_offset_params(limit,offset)
        bl_entries_db = db.get_all_best_blacklist_db_entries(pagesize=pagesize,page=page)
    
    for blacklist_db in bl_entries_db:
        entry = __build_BlacklistEntry(blacklist_db)
        ret.append(entry)
    return ret

def blacklist_site_id_get(site_id, clientID=None)->api.BlackListEntry: 
    log.mal2_rest_log.info("blacklist_site_id_get site_id %s, clientId %s",site_id,clientID)

    #sanity check for all public controller methods on service load
    load_ok, feedback = check_db_load_ok()
    if load_ok == False:
        #return 401 which client can specifically target
        return feedback, 401

    try:
        site_id = int(site_id)
    except:
        raise ValueError("site_id not a valid integer")

    site_db = db.get_site_db_entry_by_siteID(site_id)
    blacklist_db = db.get_best_blacklist_db_entry_by_siteID(site_id)
    if not blacklist_db or not site_db:
        raise Exception("site is not blacklisted")
    
    ret = __build_BlacklistEntry(blacklist_db)
    return ret

def __build_GreylistEntry(greylist_db:db_model.Greylist)->api.GreyListEntry:
    ret = api.GreyListEntry(
        site_id=greylist_db.site.id,
        site_base_url=greylist_db.site.url,
        greylist_name=greylist_db.greylist_source.name.value,
        greylist_description=greylist_db.greylist_source.description,
        greylist_logo= greylist_db.greylist_source.logo_url,
        greylist_url = greylist_db.greylist_source.url,
        site_added_date=greylist_db.timestamp,
        site_type=greylist_db.type.value,
        site_screenshot=greylist_db.screenshot_link,
        site_information_link=greylist_db.information_link
    )
    return ret

def greylist_get(limit=None, offset=None, all=None, clientID=None)->List[api.GreyListEntry]:
    log.mal2_rest_log.info("greylist_get limit %s, offset %s, all %s, clientId %s",limit,offset,all,clientID)

    #sanity check for all public controller methods on service load
    load_ok, feedback = check_db_load_ok()
    if load_ok == False:
        #return 401 which client can specifically target
        return feedback, 401

    ret = []
    if (all == True) or (not offset and not limit):
        # return all greylists (note most current one per site if multiple from different bl sources exist per site)
        #get all sites
        gl_entries_db = db.get_all_best_greylist_db_entries()
    else:
        pagesize, page = __init_limit_and_offset_params(limit,offset)
        gl_entries_db = db.get_all_best_greylist_db_entries(pagesize=pagesize,page=page)
    
    for greylist_db in gl_entries_db:
        entry = __build_GreylistEntry(greylist_db)
        ret.append(entry)
    return ret

def greylist_site_id_get(site_id, clientID=None)->api.GreyListEntry: 
    log.mal2_rest_log.info("greylist_site_id_get site_id %s, clientId %s",site_id,clientID)

    #sanity check for all public controller methods on service load
    load_ok, feedback = check_db_load_ok()
    if load_ok == False:
        #return 401 which client can specifically target
        return feedback, 401

    try:
        site_id = int(site_id)
    except:
        raise ValueError("site_id not a valid integer")

    site_db = db.get_site_db_entry_by_siteID(site_id)
    greylist_db = db.get_best_greylist_db_entry_by_siteID(site_id)
    if not greylist_db or not site_db:
        raise Exception("site is not greylisted")
    
    ret = __build_GreylistEntry(greylist_db)
    return ret

def __build_WhitelistEntry(whitelist_db:db_model.Whitelist)->api.WhiteListEntry:
    ret = api.WhiteListEntry(
        site_id=whitelist_db.site.id,
        site_base_url=whitelist_db.site.url,
        whitelist_name=whitelist_db.whitelist_source.name.value,
        whitelist_description=whitelist_db.whitelist_source.description,
        whitelist_logo= whitelist_db.whitelist_source.logo_url,
        whitelist_url = whitelist_db.whitelist_source.url,
        site_added_date=whitelist_db.timestamp,
        site_information_link=whitelist_db.information_link,
        whitelist_type=whitelist_db.type.value,
        #add the company details that are exposed through the api
        company_name=whitelist_db.company.name,
        company_street=whitelist_db.company.street,
        company_zipcode=whitelist_db.company.zip_code,
        company_country=whitelist_db.company.country,
        company_city = whitelist_db.company.city,
        company_logo = whitelist_db.company.logo_url
    )
    return ret

def whitelist_get(limit=None, offset=None, all=None, clientID=None)->List[api.WhiteListEntry]:
    log.mal2_rest_log.info("whitelist_get limit %s, offset %s, all %s, clientId %s",limit,offset,all,clientID)

    #sanity check for all public controller methods on service load
    load_ok, feedback = check_db_load_ok()
    if load_ok == False:
        #return 401 which client can specifically target
        return feedback, 401

    ret = []
    if (all == True) or (not offset and not limit):
        # return all whitelists (note most current one per site if multiple from different bl sources exist per site)
        #get all sites
        wl_entries_db = db.get_all_best_whitelist_db_entries()
    else:
        pagesize, page = __init_limit_and_offset_params(limit,offset)
        wl_entries_db = db.get_all_best_whitelist_db_entries(pagesize=pagesize,page=page)
    
    for whitelist_db in wl_entries_db:
        entry = __build_WhitelistEntry(whitelist_db)
        ret.append(entry)
    return ret

def whitelist_site_id_get(site_id, clientID=None)->api.WhiteListEntry: 
    log.mal2_rest_log.info("whitelist_site_id_get site_id %s, clientId %s",site_id,clientID)

    #sanity check for all public controller methods on service load
    load_ok, feedback = check_db_load_ok()
    if load_ok == False:
        #return 401 which client can specifically target
        return feedback, 401

    try:
        site_id = int(site_id)
    except:
        raise ValueError("site_id not a valid integer")

    site_db = db.get_site_db_entry_by_siteID(site_id)
    whitelist_db = db.get_best_whitelist_db_entry_by_siteID(site_id)
    if not whitelist_db or not site_db:
        raise Exception("site is not whitelisted")
    
    ret = __build_WhitelistEntry(whitelist_db)
    return ret

def __build_IgnorelistEntry(ignorelist_db:db_model.Ignorelist)->api.IgnoreListEntry:
    ret = api.IgnoreListEntry(
        site_id=ignorelist_db.site.id,
        site_base_url=ignorelist_db.site.url,
        ignorelist_name=ignorelist_db.ignorelist_source.name.value,
        ignorelist_description=ignorelist_db.ignorelist_source.description,
        ignorelist_logo= ignorelist_db.ignorelist_source.logo_url,
        ignorelist_url = ignorelist_db.ignorelist_source.url,
        site_added_date=ignorelist_db.timestamp,
        site_type=ignorelist_db.category.value,
    )
    return ret

def ignorelist_get(limit=None, offset=None, all=None, clientID=None)->List[api.IgnoreListEntry]:
    log.mal2_rest_log.info("ignorelist_get limit %s, offset %s, all %s, clientId %s",limit,offset,all,clientID)

    #sanity check for all public controller methods on service load
    load_ok, feedback = check_db_load_ok()
    if load_ok == False:
        #return 401 which client can specifically target
        return feedback, 401

    ret = []
    if (all == True) or (not offset and not limit):
        # return all ignorelists sites 
        il_entries_db = db.get_all_best_ignorelist_db_entries()
    else:
        pagesize, page = __init_limit_and_offset_params(limit,offset)
        il_entries_db = db.get_all_best_ignorelist_db_entries(pagesize=pagesize,page=page)
    
    for ignorelist_db in il_entries_db:
        entry = __build_IgnorelistEntry(ignorelist_db)
        ret.append(entry)
    return ret

def ignorelist_site_id_get(site_id, clientID=None)->api.IgnoreListEntry: 
    log.mal2_rest_log.info("ignorelist_site_id_get site_id %s, clientId %s",site_id,clientID)

    #sanity check for all public controller methods on service load
    load_ok, feedback = check_db_load_ok()
    if load_ok == False: 
        #return 401 'unauthorized' which client can specifically target
        return feedback, 401

    try:
        site_id = int(site_id)
    except:
        raise ValueError("site_id not a valid integer")

    site_db = db.get_site_db_entry_by_siteID(site_id)
    ignorelist_db = db.get_best_ignorelist_db_entry_by_siteID(site_id)
    if not ignorelist_db or not site_db:
        raise Exception("site is not ignorelisted")
    
    ret = __build_IgnorelistEntry(ignorelist_db)
    return ret