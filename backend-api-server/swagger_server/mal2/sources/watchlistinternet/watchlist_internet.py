from swagger_server import logger_config as log
import swagger_server.mal2.db.model.db_model as db_model
import swagger_server.mal2.sources.sources_utils as sources_utils
import requests
import datetime as dt
import pandas as pd

WATCHLIST_FAKE_SHOP_CSV =  "https://www.watchlist-internet.at/index.php?id=120&no_cache=1"
WATCHLIST_FRAUD_STREAMING_CSV =  "https://www.watchlist-internet.at/index.php?id=121&no_cache=1"
WATCHLIST_FRAUD_REALESTATE_CSV = "https://www.watchlist-internet.at/index.php?id=122&no_cache=1"

#list of sites to skip from fake-shop db entries
# e.g. preventing https://instagram.com to get added as fake-shop due to https://instagram.com/yeezystoregermany entry
skip_baseurls = ["instagram.com", "google.com", "google.at", "facebook.com"]


def get_all_blacklist_entries():
    """queries the watchlist-internet csv endpoints of fake_shops (=Markenfälscher + Fake-Shop), fraudulent streaming sites 
    and fraudulent real estate lists and returns a pandas dataframe with [url, created_at, website_type]
    """
    ret = []

    log.mal2_fakeshop_db_log.info("checking watchlist-internet website for blacklist entries")
    #fetch all fake_shops (even though its fake-shops + counterfeit_goods)
    fake_shops = __get_csv_bl_entry_list(WATCHLIST_FAKE_SHOP_CSV,db_model.EnumBlacklistType.fraudulent_online_shop)
    log.mal2_rest_log.info("downloaded fake_shops. count: %s, from: %s",len(fake_shops),WATCHLIST_FAKE_SHOP_CSV)

    #fetch all fraudulent streaming sites from csv listing
    fraud_streaming = __get_csv_bl_entry_list(WATCHLIST_FRAUD_STREAMING_CSV,db_model.EnumBlacklistType.fraudulent_streaming_platform)
    log.mal2_rest_log.info("downloaded fraudulent streaming sites. count: %s, from: %s",len(fraud_streaming),WATCHLIST_FRAUD_STREAMING_CSV)

    #fetch all fraudulent streaming sites from csv listing
    fraud_realestate = __get_csv_bl_entry_list(WATCHLIST_FRAUD_REALESTATE_CSV,db_model.EnumBlacklistType.fraudulent_real_estate_agency)
    log.mal2_rest_log.info("downloaded fraudulent realestate sites. count: %s, from: %s",len(fraud_realestate),WATCHLIST_FRAUD_REALESTATE_CSV)
        
    ret = fake_shops + fraud_streaming + fraud_realestate
    
    if len(ret) < 1:
        df = pd.DataFrame(columns={'url','website_type','created_at'})
    else:    
        df = pd.DataFrame(ret) 
    
    return df


def __get_csv_bl_entry_list(api_url, bl_type:db_model.EnumBlacklistType):
    """queries the watchlist-internet csv entpoints (api_url) and extracts all listed elements 
    example format of a line: "007drones.de";26.02.2018;"Fake-Shop"

    Arguments:
        api_url {Str} -- 'watchlist internet csv endpoint e.g. https://www.watchlist-internet.at/index.php?id=120&no_cache=1
        type {db_model.EnumBlacklistType} -- List to append results. If None, new list is created
        results {List} -- List[Dict] to append results. If None, new list is created

    Returns:
        List[Dict] -- List of Dict{url:str, created_at:datetime}
    """
    def __checkcsv_is_bltype_to_import(csv_bltype_entry_name):
        """checks the bltype from the csv and returns if it shall be imported or not
        e.g. we're not importing bltypes "Dropshipping" and "Sitz außerhalb EU"
        old watchlist csv style don't provide the bltype within the csv, these are not filtered
        Returns: boolean
        """
        if csv_bltype_entry_name==None:
            return True #old csv style, bltype not present in csv
        elif csv_bltype_entry_name=="Fake-Shop":
            return True
        elif csv_bltype_entry_name=="Markenfälscher":
            return True
        else:
            return False #e.g. "Dropshipping"
    
    def __get_bltype_from_csv(csv_bltype_entry_name):
        """extract blacklist type provided within watchlist csv file and maps it to db supported EnumBlacklistType
        If none provided in csv stick with the one provided when alling the parent function
        Returns:
            db_model.EnumBlacklistType: blacklist type 
        """
        if csv_bltype_entry_name=="Fake-Shop":
            return db_model.EnumBlacklistType.fraudulent_online_shop
        elif csv_bltype_entry_name=="Markenfälscher":
            return db_model.EnumBlacklistType.fraudulent_brand_counterfeiter
        else:
            #if not provided in csv return the default provided by the calling function
            return bl_type

    results = []
    #log.mal2_fakeshop_db_log.info("get_website_entry_list for %s",api_url)
    resp =requests.get(api_url,timeout=10)
    
    #parse responds
    if resp.status_code == 200:
        data = resp.text
        count = 0
        if data:
            lines = data.splitlines()
            for line in lines:
                line_elems = line.split(';')
                line_ok = True
                #ignore malformed lines
                if len(line_elems)==2:
                    #csv from watchlist does not provide blacklist type (e.g. immobilien, streaming, etc.)
                    rurl = line_elems[0]
                    rdate = line_elems[1]
                    rbltype = None
                elif len(line_elems)==3:
                    #csv from watchlist provide blacklist type (e.g. fake-shop, markenfälscher)
                    rurl = line_elems[0]
                    rdate = line_elems[1]
                    rbltype = line_elems[2]
                    rbltype = rbltype[1:-1] #strip trailing " and ending "chars
                else:
                    log.mal2_rest_log.warn("skipping malformed csv entry: %s",line)
                    line_ok = False

                line_to_import = True
                if not __checkcsv_is_bltype_to_import(rbltype):
                    log.mal2_rest_log.debug("ignoring unsupported blacklist type csv entry: %s, %s", rbltype, line)
                    line_to_import = False

                if line_ok and line_to_import:
                    rurl = rurl[1:-1]
                    row = {}
                    row['created_at'] = dt.datetime.strptime(rdate,'%d.%m.%Y')
                    base_url = sources_utils.extract_base_url(rurl)
                    row['url'] = base_url
                    row['website_type'] = __get_bltype_from_csv(rbltype)

                    #check if not in skip-list
                    if not (base_url in skip_baseurls):
                        results.append(row)
                        count +=1
                    else:
                        log.mal2_fakeshop_db_log.debug("skipping entry for %s", rurl)
        else:
            log.mal2_fakeshop_db_log.error("no data received for watchlist internet csv api url: %s",api_url)
    else:
        log.mal2_rest_log.error("error status code: %s response: %s",resp.status_code,resp.text)
    
    return results


def get_all_greylist_entries():
    """queries the watchlist-internet csv endpoints for grey list entries (=Dropshipping + Non-EU Shops)
    returns a pandas dataframe with [url, created_at, website_type]
    """
    ret = []

    log.mal2_fakeshop_db_log.info("checking watchlist-internet website for greylist entries")
    #fetch all grey listed shops 
    ret  = __get_csv_gl_entry_list(WATCHLIST_FAKE_SHOP_CSV)
    log.mal2_rest_log.info("downloaded greylisted shops. count: %s, from: %s",len(ret),WATCHLIST_FAKE_SHOP_CSV)

    if len(ret) < 1:
        df = pd.DataFrame(columns={'url','website_type','created_at'})
    else:    
        df = pd.DataFrame(ret) 
    
    return df


def __get_csv_gl_entry_list(api_url):
    """queries the watchlist-internet csv entpoints (api_url) and extracts all listed elements 
    example format of a line: "007drones.de";26.02.2018;"Droppshipping"

    Arguments:
        api_url {Str} -- 'watchlist internet csv endpoint e.g. https://www.watchlist-internet.at/index.php?id=120&no_cache=1
        results {List} -- List[Dict] to append results. If None, new list is created

    Returns:
        List[Dict] -- List of Dict{url:str, created_at:datetime}
    """
    def __checkcsv_is_gltype_to_import(csv_gltype_entry_name):
        """checks the gltype from the csv and returns if it shall be imported or not
        e.g. we're not importing gltypes "Fake-Shop" and "Markenfälscher"
        Returns: boolean
        """
        if csv_gltype_entry_name=="Sitz außerhalb EU":
            return True
        elif csv_gltype_entry_name=="Dropshipping":
            return True
        else:
            return False #e.g. "Markenfälscher"
    
    def __get_gltype_from_csv(csv_gltype_entry_name):
        """extract greylist type provided within watchlist csv file and maps it to db supported EnumGreylistType
        If none provided in csv stick other is returned
        Returns:
            db_model.EnumGreylistType: greylist type 
        """
        if csv_gltype_entry_name=="Sitz außerhalb EU":
            return db_model.EnumGreylistType.shop_not_located_in_the_eu
        elif csv_gltype_entry_name=="Dropshipping":
            return db_model.EnumGreylistType.shop_dropshipping
        else:
            #if not provided in csv return the default
            return db_model.EnumGreylistType.other

    results = []
    #log.mal2_fakeshop_db_log.info("get_website_entry_list for %s",api_url)
    resp =requests.get(api_url,timeout=10)
    
    #parse responds
    if resp.status_code == 200:
        data = resp.text
        count = 0
        if data:
            lines = data.splitlines()
            for line in lines:
                line_elems = line.split(';')
                line_ok = True
                #ignore malformed lines
                if len(line_elems)==3:
                    #csv from watchlist provide greylist type (e.g. Dropshipping)
                    rurl = line_elems[0]
                    rdate = line_elems[1]
                    rgltype = line_elems[2]
                    rgltype = rgltype[1:-1] #strip trailing " and ending "chars
                else:
                    log.mal2_rest_log.warn("skipping malformed csv entry: %s",line)
                    line_ok = False

                line_to_import = True
                if not __checkcsv_is_gltype_to_import(rgltype):
                    log.mal2_rest_log.debug("ignoring unsupported greylist type csv entry: %s, %s", rgltype, line)
                    line_to_import = False

                if line_ok and line_to_import:
                    rurl = rurl[1:-1]
                    row = {}
                    row['created_at'] = dt.datetime.strptime(rdate,'%d.%m.%Y')
                    base_url = sources_utils.extract_base_url(rurl)
                    row['url'] = base_url
                    row['website_type'] = __get_gltype_from_csv(rgltype)

                    #check if not in skip-list
                    if not (base_url in skip_baseurls):
                        results.append(row)
                        count +=1
                    else:
                        log.mal2_fakeshop_db_log.debug("skipping entry for %s", rurl)
        else:
            log.mal2_fakeshop_db_log.error("no data received for watchlist internet csv api url: %s",api_url)
    else:
        log.mal2_rest_log.error("error status code: %s response: %s",resp.status_code,resp.text)
    
    return results