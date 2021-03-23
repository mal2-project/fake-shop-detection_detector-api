import swagger_server.mal2.db.model.db_model as db_model
import swagger_server.mal2.sources.fakeshopdb.fake_shop_db as fakeshopdb
import swagger_server.mal2.sources.fakeshopdb.fake_shop_db_utils as fakeshopdb_utils
import swagger_server.mal2.sources.localdata.local_csv_sources as localcsvsrc
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
    #re-import of ignored domains every 6 hours
    elif hours_since_last_import() > 6:
        return True
    else:
        return False


def import_ignorelists():
    """imports all ignored domains - ignores the ones already existing in the local db
    """
    #set it to now - just to avoid thread issues
    global last_import 
    last_import = datetime.now()
    log.mal2_rest_log.info("import_ignorelists")
    #import most visited websites DACH (from local excel)
    import_most_visited_domains_ignorelist(limit_imported_items=10)
    #import watchlist-internet fake-shop (from no_verification_required)
    import_mal2_fake_shop_db_ignorelist(limit_imported_items=10) 
    

def import_mal2_fake_shop_db_ignorelist(limit_imported_items:int=-1):
    """imports watchlist internet ignorelist from fake-shop db
    """
    try:
        log.mal2_rest_log.info("import_mal2_fake_shop_db_ignorelist")
        #query mal2 fake-shop db for fake-shops listings
        df_fsdb_ignorelist = fakeshopdb.get_all_ignored_entries(limit_imported_items)
        #create ignorelist source if not exists
        db_il_source_entry = db_handler.get_ignorelistsource_db_entry_by_name(db_model.EnumIgnorelistSources.mal2_fake_shop_db)
        if not db_il_source_entry:
            db_il_source_entry = db_model.IgnorelistSource(
                name=db_model.EnumIgnorelistSources.mal2_fake_shop_db,
                description= "Laufend aktualisiert",
                url= "https://www.fakeshop.at",
                logo_url= "https://www.fakeshop.at/typo3conf/ext/theme/Resources/Public/images/logo.svg"
                )
            #commit ignorelist source to db
            db_handler.commit_db_entry(db_il_source_entry)
            log.mal2_rest_log.info("created ignorelist_source %s",db_il_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_ignorelists for %s",db_model.EnumIgnorelistSources.mal2_fake_shop_db.value)
        
        #common code for handling the db import
        __import_ignorelist_data(
            db_il_source_entry,
            db_model.EnumIgnorelistSources.mal2_fake_shop_db,
            df_fsdb_ignorelist,
            limit_imported_items = limit_imported_items
            )
    except Exception as e:
        log.mal2_rest_log.exception("failed import ignorelist %s",e)


def import_most_visited_domains_ignorelist(limit_imported_items:int=-1):
    """imports most_visited_domains ignorelist
    """
    try:
        log.mal2_rest_log.info("import most_visited_domains_ignorelist")
        #import local entries from excel sheet
        df_mvd_ignorelist = localcsvsrc.get_most_visited_domains_ignorelist_entries()

        #create ignorelist source if not exists
        db_il_source_entry = db_handler.get_ignorelistsource_db_entry_by_name(db_model.EnumIgnorelistSources.most_visited_domains)
        if not db_il_source_entry:
            db_il_source_entry = db_model.IgnorelistSource(
                name=db_model.EnumIgnorelistSources.most_visited_domains,
                description= "Stand: 2018",
                url= "https://de.wikipedia.org/wiki/Liste_der_meistaufgerufenen_Websites",
                )
            #commit ignorelist source to db
            db_handler.commit_db_entry(db_il_source_entry)
            log.mal2_rest_log.info("created ignorelist_source %s",db_il_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_ignorelists for %s",db_model.EnumIgnorelistSources.most_visited_domains.value)
        #import ignorelist entries into local db

        #common code for handling the db import
        __import_ignorelist_data(
            db_il_source_entry,
            db_model.EnumIgnorelistSources.most_visited_domains,
            df_mvd_ignorelist,
            limit_imported_items = limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def __import_ignorelist_data(db_il_source_entry:db_model.IgnorelistSource, source:db_model.EnumIgnorelistSources, dataframe, limit_imported_items:int=-1):
    """common importer for ingorelist entries via pandas dataframe that contain ['url'] and 
    optional [company_type], ['created_at]
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

  
    log.mal2_rest_log.info("start import_ignorelists for %s",source.value)
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

            db_il_entry =  db_handler.get_ignorelist_db_entry_by_url_and_name(entry['url'],source)
            #check if existing entry
            if not db_il_entry:
                #check if site exists
                db_site = db_handler.get_site_db_entry_by_url(entry['url'])
                if not db_site:
                    #create site or update site
                    db_site = db_model.Site(url=entry['url'], status=db_model.EnumSiteStatus.ignore)
                else:
                    db_site.status = db_model.EnumSiteStatus.ignore

                log.mal2_rest_log.info("import_ignorelist adding new ignorelist entry to db")

                db_il_entry = db_model.Ignorelist(
                    site=db_site,
                    ignorelist_source=db_il_source_entry,
                    category=db_model.EnumIgnoreListCategory.unknown
                )

                if check_df_data_exists(entry,'created_at'):
                    db_il_entry.timestamp = entry['created_at']
                
                if check_df_data_exists(entry,'company_type'):
                    #check if value in allowed mal2 categories
                    if entry['company_type'] in db_model.EnumIgnoreListCategory.__members__:
                        db_il_entry.category = entry['company_type']
                    else:
                        db_il_entry.category = db_model.EnumIgnoreListCategory.unknown

                #commit ignorelist entry to db
                db_handler.commit_db_etnries(db_site, db_il_entry)
                imported_count += 1
            else:
                log.mal2_rest_log.debug("import_ignorelist skipping known entry %s",db_il_entry.__repr__)
        except:
            log.mal2_rest_log.exception("import_ignorelist failed - unsupported pandas import data format for %s",entry.to_string)

    global last_import 
    last_import= datetime.now()
    log.mal2_rest_log.info("Completed import_ignorelist items %s of %s for %s",imported_count,processed_count, source)