import requests
import datetime as dt
import io as io
import pandas as pd
from swagger_server import logger_config as log
import swagger_server.mal2.sources.sources_utils as sources_utils
import traceback

def get_all_whitelist_entries():
    log.mal2_fakeshop_db_log.info("checking Österreichischer Buchhandel API (json data) for whitelist entries")
    api_json_endpoint = "https://buchhandel.at/wp-json/wp/v2/buchhandlung?page=1&per_page=50"
    return __get_securelisting_json_entry_list(api_json_endpoint)

def __get_securelisting_json_entry_list(api_url):
    """queries the Hauptverband des österreichischen Buchhandels json entpoint (api_url) and extracts all listed elements 
    as pandas dataframe following the mandatory data import columns ['url', 'company_name'] optional params such as ['company_street', 'company_city', 
    'company_zip_code', 'company_country', 'company_logo', 'created_at'] are provided where available from API. 
    url are converted to netloc format
    create_at is datetime format

    Arguments:
        api_url {Str} -- 'schweizer guetezeichen json endpoint https://buchhandel.at/wp-json/wp/v2/buchhandlung?page=1&per_page=50

    Returns:
        Dataframe -- pandas dataframe or none
    """

    def __extrac_next_link(resp):
        try:
            next_link = resp.headers['Link']
            if('rel="prev"' in next_link and 'rel="next"' in next_link):
                next_link = next_link.split(',')[1]
            elif('rel="prev"' in next_link and not 'rel="next"' in next_link):
                return None
            
            l_start = next_link.find('<')+1
            l_end = next_link.find('>', l_start)
            return next_link[l_start:l_end]
        except:
            return None

    def __replace_chars(s):
        replace_chars = {"&amp;":"&", "&#038;":"&", "&#8211;":"-"}
        for token in replace_chars.keys():
            s = replace_chars[token].join(s.split(token))
        return s

    def __extract_name(siteurl):
        if "." in siteurl:
            siteurl = siteurl.rsplit(".",1)[0]
        return siteurl


    log.mal2_fakeshop_db_log.info("__get_securelisting_json_entry_list for %s",api_url)
    try:
        resp =requests.get(api_url,timeout=10)

        #parse responds
        if resp.status_code == 200:
            #uses pagination rest-api
            total_pages = resp.headers['X-WP-TotalPages']
            results = []
            api_data = resp.json()
            results = results + api_data

            for i in range(1, int(total_pages)):
                url_next = __extrac_next_link(resp)
                resp =requests.get(url_next,timeout=10)
                if resp.status_code != 200:
                    raise Exception("Error fetching data for: %s"%url_next)
                url_next = __extrac_next_link(resp)
                api_data = resp.json()
                results = results + api_data
            
            log.mal2_fakeshop_db_log.info("overall number of entries received from api: %s",len(results))

            #parsing of data
            data = []
            for r in results: 
                item = {}
                if r['status'] == "publish" and r['type'] == "buchhandlung":
                    
                    item['company_street'] = r['acf']['buchhandlung_strasse'] #strasse mit hausnummer
                    item['company_zip_code'] = r['acf']['buchhandlung_plz']
                    item['company_city'] = r['acf']['buchhandlung_ort']
                    if r['acf']['buchhandlung_google_maps'] != False:
                        item['company_country'] =  r['acf']['buchhandlung_google_maps']['country']
                    else:
                        item['company_country'] = None
                    item['name'] = __replace_chars(r['title']['rendered'])#company name
                    item['url'] = r['acf']['buchhandlung_website_url']
                    item['category'] = r['type']
                    data.append(item)
                else:
                    log.mal2_fakeshop_db_log.info("skipping item %s %s",r['status'],r['type'])
            
            df = pd.DataFrame.from_dict(data)

            if not 'url' in df.columns.tolist() or not 'name' in df.columns.tolist():
                raise Exception("api endpoint data structure changed!")

            if df.size>0:
                try:
                    df.insert(0, 'created_at', pd.to_datetime('now').replace(microsecond=0))
                    #apply base_url extraction for all records in the dataframe
                    df['siteurl'] = df['url'].apply(sources_utils.extract_base_url)
                    #make sure we always have a company name - use one provided by api or of non extract from url
                    df['company_name']= df.apply(lambda x: x['name'] if len(x['name']) >1 else __extract_name(x['siteurl']), axis=1)
                    df = df.sort_values(by=['siteurl'], ascending=True)
                    #drop entries that don't have a url or malformed urls such as http://http://buchhandlung.familie-trenker.at
                    df = df[(df['siteurl'].notna()) & (df['siteurl'].str.len()>3) & (df['siteurl'] != "http") & (df['siteurl'] != "https")]
                    # drop all duplicte values 
                    df.drop_duplicates(subset ="siteurl", keep = 'first', inplace = True) 
                    # rename the existing DataFrame column (rather than creating a copy) 
                    df = df.drop('url', 1)
                    df = df.drop('name', 1)
                    df = df.drop('category', 1)
                    df = df.rename(columns={'siteurl':'url'})
                    #replace nan data with None values
                    df = df.where(pd.notnull(df), None)
                    log.mal2_fakeshop_db_log.info("number of entries from Österreichischer Buchhandel received: %s",df.size)
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
    except Exception as e:
        log.mal2_fakeshop_db_log.error("failure in reaching buchhandel_at API endpoint: %s",e)
        traceback.print_exc()
        return None