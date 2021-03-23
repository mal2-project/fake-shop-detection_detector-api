import requests
import datetime as dt
import io as io
import pandas as pd
from swagger_server import logger_config as log
import swagger_server.mal2.sources.sources_utils as sources_utils
import traceback

def get_all_whitelist_entries():
    log.mal2_fakeshop_db_log.info("checking Schweizer Gütezeichen api (json data) for whitelist entries")
    api_json_endpoint = "https://www.zertifizierte-shops.ch/api/export"
    return __get_guetezeichen_json_entry_list(api_json_endpoint)

def __get_guetezeichen_json_entry_list(api_url):
    """queries the Schweizer Gütezeichens json entpoint (api_url) and extracts all listed elements 
    as pandas dataframe following the mandatory data import columns ['url', 'company_name'] optional params such as ['company_street', 'company_city', 
    'company_zip_code', 'company_country', 'company_logo', 'created_at'] are currently not available from API. 
    url are converted to netloc format
    create_at is datetime format

    Arguments:
        api_url {Str} -- 'schweizer guetezeichen json endpoint https://www.zertifizierte-shops.ch/api/export

    Returns:
        Dataframe -- pandas dataframe or none
    """
    log.mal2_fakeshop_db_log.info("__get_guetezeichen_json_entry_list for %s",api_url)
    resp =requests.get(api_url,timeout=10)

    #parse responds
    if resp.status_code == 200:
        api_data = resp.json()
        if (api_data.keys() != 1) and (not 'data' in api_data.keys()):
            log.mal2_fakeshop_db_log.error("api endpoint data structure changed!")
            return None
        
        df = pd.DataFrame.from_dict(pd.json_normalize(api_data['data']), orient='columns')
        #print(df.head())
        if not 'url' in df.columns.tolist() or not 'certificate' in df.columns.tolist():
            log.mal2_fakeshop_db_log.error("api endpoint data structure changed!")
            return None

        if df.size>0:
            try:
                df.insert(0, 'created_at', pd.to_datetime('now').replace(microsecond=0))
                #apply base_url extraction for all records in the dataframe
                df['siteurl'] = df['url'].apply(sources_utils.extract_base_url)
                #required param name not in data, use domain-name and remove .ch ending
                df['company_name']=df['url'].apply(lambda x: x.rsplit(".",1)[0])
                # rename the existing DataFrame column (rather than creating a copy) 
                df = df.drop('url', 1)
                df = df.rename(columns={'certificate':'certificate_url', 'siteurl':'url'})
                #replace nan data with None values
                df = df.where(pd.notnull(df), None)
                log.mal2_fakeshop_db_log.info("number of entries from schweizer guetezeichen received: %s",df.size)
                return df
            except Exception as e:
                log.mal2_fakeshop_db_log.error("failure in dataframe: %s",e)
                traceback.print_exc()
                return None
        else:
            log.mal2_fakeshop_db_log.error("no data received: %s",resp.text)
    else:
        log.mal2_fakeshop_db_log.error("error status code: %s response: %s",resp.status_code,resp.text)
    
    return None