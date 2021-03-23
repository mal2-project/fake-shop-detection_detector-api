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
    #re-import of blacklist data every 24 hours
    elif hours_since_last_import() > 24:
        return True
    else:
        return False


def import_blacklists():
    """imports all blacklists - ignores the ones already existing in the local db
    """
    #set it to now - just to avoid thread issues
    global last_import 
    last_import = datetime.now()
    log.mal2_rest_log.info("import_blacklists")
    #import watchlist-internet website csv blacklists
    import_watchlist_internet_blacklists(limit_imported_items=10)
    #import mal2 fakeshop-db blacklists
    import_mal2_fake_shop_db_blacklists(limit_imported_items=10) 
    

def import_watchlist_internet_blacklists(limit_imported_items:int=-1):
    """imports watchlist internet blacklist from watchlist internet csv sources
    """
    try:
        log.mal2_rest_log.info("import watchlist internet csv blacklists")
        #query watchlist website csv endpoints
        df_bl_blacklist = watchlistinternet.get_all_blacklist_entries()
        #create blacklist source if not exists
        db_bl_source_entry = db_handler.get_blacklistsource_db_entry_by_name(db_model.EnumBlacklistSources.watchlist_internet_listing)
        if not db_bl_source_entry:
            db_bl_source_entry = db_model.BlacklistSource(
                name=db_model.EnumBlacklistSources.watchlist_internet_listing,
                description= "Informationsplattform zu Internetbetrug und anderen Online-Fallen aus Österreich, laufend aktualisiert",
                url= "https://www.watchlist-internet.at/alle-themen/",
                logo_url= "https://www.watchlist-internet.at/fileadmin/files/Logos/Logo_Watchlist_Internet_300RGB.png"
                )
            #commit blacklist source to db
            db_handler.commit_db_entry(db_bl_source_entry)
            log.mal2_rest_log.info("created blacklist_source %s",db_bl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_blacklists for %s",db_model.EnumBlacklistSources.watchlist_internet_listing.value)
        
        __import_blacklist_data(
            db_bl_source_entry,
            db_model.EnumBlacklistSources.watchlist_internet_listing,
            df_bl_blacklist,
            limit_imported_items= limit_imported_items)
    except Exception as e:
        log.mal2_rest_log.exception("failed import blacklist %s",e)


def import_mal2_fake_shop_db_blacklists(limit_imported_items:int=-1):
    """imports watchlist internet blacklist from fake-shop db
    """
    try:
        log.mal2_rest_log.info("import mal2_fake_shop_db_blacklists")
        #query mal2 fake-shop db for fake-shops listings
        df_fsdb_blacklist = fakeshopdb.get_all_blacklist_entries(limit_imported_items)
        #create blacklist source if not exists
        db_bl_source_entry = db_handler.get_blacklistsource_db_entry_by_name(db_model.EnumBlacklistSources.mal2_fake_shop_db)
        if not db_bl_source_entry:
            db_bl_source_entry = db_model.BlacklistSource(
                name=db_model.EnumBlacklistSources.mal2_fake_shop_db,
                description= "Kuratiert durch die Watchlist Internet, laufend aktualisiert",
                url= "https://www.fakeshop.at",
                logo_url= "https://www.fakeshop.at/typo3conf/ext/theme/Resources/Public/images/logo.svg"
                )
            #commit blacklist source to db
            db_handler.commit_db_entry(db_bl_source_entry)
            log.mal2_rest_log.info("created blacklist_source %s",db_bl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_blacklists for %s",db_model.EnumBlacklistSources.mal2_fake_shop_db.value)

        __import_blacklist_data(
            db_bl_source_entry,
            db_model.EnumBlacklistSources.mal2_fake_shop_db,
            df_fsdb_blacklist,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import blacklist %s",e)


def __import_blacklist_data(db_bl_source_entry:db_model.BlacklistSource, source:db_model.EnumBlacklistSources, dataframe, limit_imported_items:int=-1):
    """common importer for blacklist entries via pandas dataframe that contain ['url'] and 
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

  
    log.mal2_rest_log.info("start blacklist import for %s",source.value)
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

            db_bl_entry =  db_handler.get_blacklist_db_entry_by_url_and_name(entry['url'],source)
            #check if existing entry
            if not db_bl_entry:
                #check if site exists
                db_site = db_handler.get_site_db_entry_by_url(entry['url'])
                if not db_site:
                    #create site or update site
                    db_site = db_model.Site(url=entry['url'], status=db_model.EnumSiteStatus.blacklist)
                else:
                    db_site.status = db_model.EnumSiteStatus.blacklist

                log.mal2_rest_log.info("import_blacklists adding new blacklist entry to db")

                #FIXME need to include information_link in dataframe
                db_bl_entry = db_model.Blacklist(
                    site=db_site,
                    blacklist_source=db_bl_source_entry,
                    information_link= "https://www.watchlist-internet.at/search/?tx_kesearch_pi1[sword]={}".format(entry['url']),
                )
                if check_df_data_exists(entry,'created_at'):
                    db_bl_entry.timestamp = entry['created_at']

                if check_df_data_exists(entry,'screenshot_link'):
                    db_bl_entry.screenshot_link = entry['screenshot_link']
                else:
                    #arch_date, arch_link = waybackmachine.get_entry_from_wayback_machine(entry['url'],retry=1)
                    #screenshot_link= arch_link,
                    screenshot_link= ""

                if check_df_data_exists(entry,'website_type'):
                    #expecting EnumblacklistType object from data import
                    if isinstance(entry['website_type'], db_model.EnumBlacklistType):
                        db_bl_entry.type = entry['website_type']
                    else:
                        db_bl_entry.type = db_model.EnumBlacklistType.other

                #commit ignorelist entry to db
                db_handler.commit_db_etnries(db_site, db_bl_entry)
                imported_count += 1
            else:
                log.mal2_rest_log.debug("import_blacklist skipping known entry %s",db_bl_entry.__repr__)
        except:
            log.mal2_rest_log.exception("import_blacklist failed - unsupported pandas import data format for %s",entry.to_string)

    global last_import 
    last_import= datetime.now()
    log.mal2_rest_log.info("Completed import_blacklist items %s of %s for %s",imported_count,processed_count, source)