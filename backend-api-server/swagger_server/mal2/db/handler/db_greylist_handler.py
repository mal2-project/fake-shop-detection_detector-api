import swagger_server.mal2.db.model.db_model as db_model
import swagger_server.mal2.sources.fakeshopdb.fake_shop_db as fakeshopdb
import swagger_server.mal2.sources.fakeshopdb.fake_shop_db_utils as fakeshopdb_utils
import swagger_server.mal2.sources.watchlistinternet.watchlist_internet as watchlistinternet
import swagger_server.mal2.sources.waybackmachine.internet_archive as waybackmachine
import swagger_server.mal2.db.handler.db_handler as db_handler
from swagger_server import logger_config as log
from datetime import datetime

last_import = None   

def check_reimport_required()->bool:
    """checks if a given timespan has passed since last import

    Returns:
        bool -- re-import required True or False
    """
    
    def hours_since_last_import():
        """determines hours since previous import

        Returns:
            [type] -- hours since previous import or -1 if 
        """
        if not last_import:
            #no import executed
            return -1
        else:
            now =  datetime.now()
            diff = now - last_import
            return diff.total_seconds()/60/60

    if not last_import:
        #no import executed
        return True
    #re-import of greylist data every 24 hours
    elif hours_since_last_import() > 24:
        return True
    else:
        return False


def import_greylists():
    """imports all greylists - ignores the ones already existing in the local db
    """
    #set it to now - just to avoid thread issues
    global last_import 
    last_import = datetime.now()
    log.mal2_rest_log.info("import_greylists")
    #import watchlist-internet website csv greylists
    import_watchlist_internet_greylists(limit_imported_items=10)
    

def import_watchlist_internet_greylists(limit_imported_items:int=-1):
    """imports watchlist internet greylists from watchlist internet csv sources
    """
    try:
        log.mal2_rest_log.info("import watchlist internet csv greylists")
        #query watchlist website csv endpoints
        df_gl_greylist = watchlistinternet.get_all_greylist_entries()
        #create greylist source if not exists
        db_gl_source_entry = db_handler.get_greylistsource_db_entry_by_name(db_model.EnumGreylistSources.watchlist_internet_listing)
        if not db_gl_source_entry:
            db_gl_source_entry = db_model.GreylistSource(
                name=db_model.EnumGreylistSources.watchlist_internet_listing,
                description= "Informationsplattform zu Internetbetrug aus Österreich, laufend aktualisiert",
                url= "https://www.watchlist-internet.at/alle-themen/",
                logo_url= "https://www.watchlist-internet.at/fileadmin/files/Logos/Logo_Watchlist_Internet_300RGB.png"
                )
            #commit greylist source to db
            db_handler.commit_db_entry(db_gl_source_entry)
            log.mal2_rest_log.info("created greylist_source %s",db_gl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_greylists for %s",db_model.EnumGreylistSources.watchlist_internet_listing.value)
        
        __import_greylist_data(
            db_gl_source_entry,
            db_model.EnumGreylistSources.watchlist_internet_listing,
            df_gl_greylist,
            limit_imported_items= limit_imported_items)
    except Exception as e:
        log.mal2_rest_log.exception("failed import greylist %s",e)


def __import_greylist_data(db_gl_source_entry:db_model.GreylistSource, source:db_model.EnumGreylistSources, dataframe, limit_imported_items:int=-1):
    """common importer for greylist entries via pandas dataframe that contain ['url'] and 
    optional [website_type], ['created_at]
    """

    def check_df_data_exists(entry,key):
        ret = True
        try:
            if entry[key] == None or len(str(entry[key])) <=0:
                ret = False
        except:
            #in that case the column did not exist
            return False
        return ret

  
    log.mal2_rest_log.info("start greylist import for %s",source.value)
    imported_count = 0
    processed_count = 0
    #import ignorelist entries into local db
    for index, entry in dataframe.iterrows():
        
        #limit number of imports
        if  limit_imported_items > 0 and processed_count >= limit_imported_items:
                break
        try:
            processed_count += 1
            #mandatory items
            if not check_df_data_exists(entry,'url'):
                raise Exception("url does not exist in imported pandas dataframe")

            db_gl_entry =  db_handler.get_greylist_db_entry_by_url_and_name(entry['url'],source)
            #check if existing entry
            if not db_gl_entry:
                #check if site exists
                db_site = db_handler.get_site_db_entry_by_url(entry['url'])
                if not db_site:
                    #create site or update site
                    db_site = db_model.Site(url=entry['url'], status=db_model.EnumSiteStatus.greylist)
                else:
                    db_site.status = db_model.EnumSiteStatus.greylist

                log.mal2_rest_log.info("import_greylists adding new greylist entry to db")

                #FIXME need to include information_link in dataframe
                db_gl_entry = db_model.Greylist(
                    site=db_site,
                    greylist_source=db_gl_source_entry,
                    information_link= "https://www.watchlist-internet.at/search/?tx_kesearch_pi1[sword]={}".format(entry['url']),
                )
                if check_df_data_exists(entry,'created_at'):
                    db_gl_entry.timestamp = entry['created_at']

                if check_df_data_exists(entry,'screenshot_link'):
                    db_gl_entry.screenshot_link = entry['screenshot_link']
                else:
                    #arch_date, arch_link = waybackmachine.get_entry_from_wayback_machine(entry['url'],retry=1)
                    #screenshot_link= arch_link,
                    screenshot_link= ""

                if check_df_data_exists(entry,'website_type'):
                    #expecting EnumgreylistType object from data import
                    if isinstance(entry['website_type'], db_model.EnumGreylistType):
                        db_gl_entry.type = entry['website_type']
                    else:
                        db_gl_entry.type = db_model.EnumGreylistType.other

                #commit ignorelist entry to db
                db_handler.commit_db_etnries(db_site, db_gl_entry)
                imported_count += 1
            else:
                log.mal2_rest_log.debug("import_greylist skipping known entry %s",db_gl_entry.__repr__)
        except:
            log.mal2_rest_log.exception("import_greylist failed - unsupported pandas import data format for %s",entry.to_string)

    global last_import 
    last_import= datetime.now()
    log.mal2_rest_log.info("Completed import_greylist items %s of %s for %s",imported_count,processed_count, source)