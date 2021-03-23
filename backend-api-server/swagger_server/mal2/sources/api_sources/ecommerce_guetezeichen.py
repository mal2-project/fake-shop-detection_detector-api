import requests
import datetime as dt
import io as io
import pandas as pd
from swagger_server import logger_config as log
import swagger_server.mal2.sources.sources_utils as sources_utils

def get_all_whitelist_entries():
    log.mal2_fakeshop_db_log.info("checking ecommerce guetezeichen api (csv data) for whitelist entries")
    api_csv_endpoint = "https://www.guetezeichen.at/export/"
    return __get_guetezeichen_csv_entry_list(api_csv_endpoint)

def __get_guetezeichen_csv_entry_list(api_url):
    """queries the Österreichische ecommerce Gütezeichens csv entpoint (api_url) and extracts all listed elements 
    as pandas dataframe following the supported data import columns ['url', 'company_name', 'company_street', 'company_city', 
    'company_zip_code', 'company_country', 'company_logo', 'created_at']. 
    url are converted to netloc format
    create_at is datetime format

    Arguments:
        api_url {Str} -- 'guetezeichen csv endpoint https://www.guetezeichen.at/export/

    Returns:
        Dataframe -- pandas dataframe or none
    """
    log.mal2_fakeshop_db_log.info("__get_guetezeichen_csv_entry_list for %s",api_url)
    resp =requests.get(api_url,timeout=10)
    
    #parse responds
    if resp.status_code == 200:
        data = resp.text
        CSVData = io.StringIO(data)
        df = pd.read_csv(CSVData, sep=";")
        if CSVData and df.size>0:
            try:
                # rename the existing DataFrame column (rather than creating a copy) 
                df.rename(
                    columns={'Certificate Date (dd.mm.yyyy)': 'created_at','Shoplink':'url','Company name':'company_name',
                        'Company street':'company_street','Company zipcode':'company_zip_code','Company City':'company_city',
                        'Logofilename':'company_logo_url','Company Country':'company_country'}, 
                    inplace=True
                    )
                #print column names
                #print(list(df.columns.values))
                df["created_at"] = pd.to_datetime(df["created_at"], format="%d.%m.%Y", errors='coerce')
                #e.g. https://www.guetezeichen.at/zertifikate/shopzertifikat/wwwabatonat/
                df['certificate_url'] = df['url'].str.replace('.','')
                #edge case for example for .../wwwa1net/shop
                df['certificate_url'] = "https://www.guetezeichen.at/zertifikate/shopzertifikat/www"+df['certificate_url'].str.replace('/','')
                #apply base_url extraction for all records in the dataframe
                df['url'] = df['url'].apply(sources_utils.extract_base_url)
                log.mal2_fakeshop_db_log.info("number of entries from ecommerce guetezeichen received: %s",df.size)
                return df
            except Exception as e:
                log.mal2_fakeshop_db_log.error("failure in dataframe: %s",e)
                return None
        else:
            log.mal2_fakeshop_db_log.error("no data received: %s",resp.text)
    else:
        log.mal2_fakeshop_db_log.error("error status code: %s response: %s",resp.status_code,resp.text)
    
    return None