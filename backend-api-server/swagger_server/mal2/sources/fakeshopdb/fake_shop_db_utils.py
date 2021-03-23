import swagger_server.mal2.db.model.db_model as db_model
from swagger_server import logger_config as log
import swagger_server.mal2.sources.sources_utils as sources_utils
import requests
import datetime as dt
from w3lib.url import url_query_cleaner
from url_normalize import url_normalize

#list of sites to skip from fake-shop db entries
# e.g. preventing https://instagram.com to get added as fake-shop due to https://instagram.com/yeezystoregermany entry
skip_baseurls = ["instagram.com", "google.com", "google.at", "facebook.com"]

def translate_site_status(website_type:int, website_category) -> db_model.EnumSiteStatus:
        """translates the fake-Shop type received from the mal2 db to either site status whitelist, blacklist or unknown
        """
        if website_type == 1 or website_type == 4:
            if website_category == 2:
                return db_model.EnumSiteStatus.whitelist
            else:
                return db_model.EnumSiteStatus.ignore
        elif website_type == 2 or website_type == 3 or website_type >= 6:
            return db_model.EnumSiteStatus.blacklist
        else:
            return db_model.EnumSiteStatus.unknown

def translate_blacklist_type(website_type:int) -> db_model.EnumBlacklistType:
    """translates the website_type (int or 'null') and website_category received from the mal2 db to the types 
    defined within this application

    Returns:
        db_model.EnumBlacklistType
    """
    #fakeshopdb: website_type: as of https://db.malzwei.at/api/v1/website/type/ 
    # 1= no verification required (i.e. well known site)
    # 2= Fake Shop 3= Markenfälscher 
    # 4= checked and not fake (i.e. manually checked and confirmed not fake)
    # 5= unsure (i.e. shops watchlist needs to further monitor, no definitive answer possible yet)
    # 6= fraudulent real estate agency
    # 7= fraudulent vacation booking platform
    # 8= fraudulent craftsman services (Handwerksbetriebe)
    # 9= fraudulent carrier (Spedition)
    # 10= fraudulent survey platforms
    # null= "zu überprüfen"

    if website_type == 2:
        return db_model.EnumBlacklistType.fraudulent_online_shop
    elif website_type == 3:
        return db_model.EnumBlacklistType.fraudulent_brand_counterfeiter
    elif website_type == 6:
        return db_model.EnumBlacklistType.fraudulent_real_estate_agency
    elif website_type == 7:
        return db_model.EnumBlacklistType.fraudulent_travel_agency_or_booking_platform
    elif website_type == 8:
        return db_model.EnumBlacklistType.fraudulent_craft_service
    elif website_type == 9:
        return db_model.EnumBlacklistType.fraudulent_freight_forwarder
    elif website_type == 10:
        return db_model.EnumBlacklistType.fraudulent_survey_platform
    else:
        return db_model.EnumBlacklistType.other


def translate_ignorelist_category(website_category:int) -> db_model.EnumIgnoreListCategory:
    """translates the website category (int) received from the mal2 db to the shop_categories defined within this application

    Returns:
        db_model.EnumIgnoreListCategory
    """
    #fakeshopdb: website_category:
    # 1= Unbekannt
    # 2= Online Shop
    # 3= Sonstiges
    if website_category == 2:
        return db_model.EnumIgnoreListCategory.ecommerce
    else:
        return db_model.EnumIgnoreListCategory.unknown


def get_website_entry_list(api_url,api_token,results,fetch_screenshots=False, limit_imported_items:int=-1, curr_page=1):
    """queries the given mal2 fakeshopdb entpoint (api_url) and extracts all 'website' elements 

    Arguments:
        api_url {Str} -- 'website' endpoint e.g. api/v1/website/fake_shop/?ordering=-created_at
        api_token {Str} -- token string for querying the fakeshopdb
        results {List[Dict]} -- List to append results. If None, new list is created

    Returns:
        List[Dict] -- List of Dict{ws_id, fs_id, url, created_at, website_type}
    """

    log.mal2_fakeshop_db_log.info("get_website_entry_list for %s",api_url)
    if results == None:
        results = []
    headers = {'content-type': 'application/json', 'Authorization':'Token {}'.format(api_token) }
    resp =requests.get(api_url,headers=headers,timeout=10)
    
    #parse responds
    if resp.status_code == 200:
        #are there more results? then there's a next url
        resp_dict= resp.json()
        next_page_url = resp_dict['next']
        #print(resp_dict)
        #there should be a results entry in the response json
        if resp_dict['results']:
            #iterate over the fake-shop db results and filter out wildcard matchings e.g. orf.at in .ff-wallendorf.at   
            for res_entry in resp_dict['results']:
                row = {}
                #website id
                row['ws_id']= res_entry['id']
                #fake shop entry (with manual evaluation data) db_id
                row['fs_id']= res_entry['db_id']
                base_url = sources_utils.extract_base_url(res_entry['url'])
                row['url']= base_url
                row['created_at']=dt.datetime.fromisoformat(res_entry['created_at'])
                #ws_type: 1=no verification required, 2=Fake Shop, 3=Markenfälscher, 4= verified as no-fake
                row['website_type']=res_entry['website_type']
                row['company_type']=res_entry['website_category']
                
                if(fetch_screenshots):
                    screenshot_link = __getScreenshotLink(res_entry['id'])
                    if screenshot_link:
                        row['screenshot_link'] = screenshot_link

                #check if not in skip-list
                if not (base_url in skip_baseurls):
                    results.append(row)
                else:
                    log.mal2_fakeshop_db_log.debug("skipping entry for %s", res_entry['url'])
        else:
            log.mal2_fakeshop_db_log.warn("unknown site to fake-shop database: %s",resp_dict)
            
        #now check if continue the recursion
        if next_page_url:
            if limit_imported_items > -1 and len(results)*curr_page >= limit_imported_items:
                log.mal2_fakeshop_db_log.debug("reached max item limit to import from fake-shop db.")
                pass
            else:
                results = get_website_entry_list(next_page_url,api_token,results,fetch_screenshots,limit_imported_items,curr_page+1)
        
    elif resp.status_code == 403:
        log.mal2_fakeshop_db_log.warn("invalid credentials code: %s response: %s",resp.status_code,resp.text)
    else:
        log.mal2_fakeshop_db_log.warn("error status code: %s response: %s",resp.status_code,resp.text)
    
    return results


def __getScreenshotLink(website_id):
    image_base_url = "https://db.malzwei.at/media/websites/screenshots/{}.png"
    screenshot_url = image_base_url.format(website_id)
    headers = {'content-type': 'application/json'}
    
    resp =requests.get(screenshot_url,headers=headers,timeout=10)
    
    if resp.status_code == 200:
        log.mal2_fakeshop_db_log.info("returning screenshot link: %s for website_id: %s,",screenshot_url,website_id)
        return screenshot_url
    else:
        log.mal2_fakeshop_db_log.debug("no screenshot found for website_id: %s, with: %s at: %s",website_id, resp.status_code,screenshot_url)
        return None
