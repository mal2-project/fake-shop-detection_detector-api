import swagger_server.mal2.db.model.db_model as db_model
import swagger_server.mal2.sources.fakeshopdb.fake_shop_db as fakeshopdb
import swagger_server.mal2.sources.api_sources.ecommerce_guetezeichen as guetezeichen_at
import swagger_server.mal2.sources.api_sources.schweizer_guetesiegel as guetezeichen_ch
import swagger_server.mal2.sources.api_sources.buchhandel_at_securelisting as buchhandel_at
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
    #re-import of blacklist data every 24 hours
    elif hours_since_last_import() > 24:
        return True
    else:
        return False


def import_whitelists():
    """imports all whitelists - ignores the ones already existing in the local db
    """
    #set it to now - just to avoid thread issues
    global last_import 
    last_import = datetime.now()
    log.mal2_rest_log.info("import_whitelists")

    #note: limits removed through sed in docker build
    #trustmark before secure listings (fifo)
    import_ecommerce_guetezeichen_whitelist(limit_imported_items=10)
    import_versandapotheken_at_listing_whitelist(limit_imported_items=10)
    import_versandapotheken_de_listing_whitelist(limit_imported_items=10)
    import_schweizer_guetezeichen_whitelist(limit_imported_items=10)
    import_ehi_trustmark_whitelist(limit_imported_items=10)
    import_trustedshops_certified_whitelist(limit_imported_items=10)
    
    #secure listing whitelists
    import_buchhandel_at_listing_whitelist(limit_imported_items=10)
    import_trustedshops_listing_whitelist(limit_imported_items=10)
    import_handelsverband_listing_whitelist(limit_imported_items=10)
    import_largest_dach_ecommerce_whitelist(limit_imported_items=10)
    import_geizhals_whitelist(limit_imported_items=10)
    import_falter_listing_whitelist(limit_imported_items=10)
    import_nunukaller_csv_ignorelist(limit_imported_items=10)
    import_kaufhausoesterreich_listing_whitelist(limit_imported_items=10)
    import_mal2_fake_shop_db_whitelist(limit_imported_items=10)


def import_ecommerce_guetezeichen_whitelist(limit_imported_items:int=-1):
    """imports ecommerce guetezeichen whitelist
    """
    try:
        log.mal2_rest_log.info("import ecommerce_guetezeichen_whitelist")
        #query watchlist website csv endpoints
        df_gz_whitelist = guetezeichen_at.get_all_whitelist_entries()

        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.ecommerce_guetezeichen_at)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.ecommerce_guetezeichen_at,
                description= "Täglich aktualisiert",
                url= "https://www.guetezeichen.at",
                logo_url= "https://www.guetezeichen.at/fileadmin/daten/downloads/Logo/logo_ecg-72dpi.png"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_whitelists for %s",db_model.EnumWhitelistSources.ecommerce_guetezeichen_at.value)
        #import whitelist entries into local db

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.ecommerce_guetezeichen_at,
            db_model.EnumWhitelistType.trustmark,
            df_gz_whitelist,
            limit_imported_items = limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def import_schweizer_guetezeichen_whitelist(limit_imported_items:int=-1):
    """imports schweizer guetezeichen whitelist
    """
    try:
        log.mal2_rest_log.info("import schweizer_guetezeichen_whitelist")
        #query watchlist website csv endpoints
        df_gz_whitelist = guetezeichen_ch.get_all_whitelist_entries()

        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.schweizer_guetezeichen_ch)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.schweizer_guetezeichen_ch,
                description= "Täglich aktualisiert",
                url= "https://www.zertifizierte-shops.ch",
                logo_url= "https://www.zertifizierte-shops.ch/img/logo-de.png"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_whitelists for %s",db_model.EnumWhitelistSources.schweizer_guetezeichen_ch.value)
        #import whitelist entries into local db

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.schweizer_guetezeichen_ch,
            db_model.EnumWhitelistType.trustmark,
            df_gz_whitelist,
            limit_imported_items = limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def import_geizhals_whitelist(limit_imported_items:int=-1):
    """imports geizhals whitelist
    """
    try:
        log.mal2_rest_log.info("import geizhals_whitelist")
        #query watchlist website csv endpoints
        df_gh_whitelist = localcsvsrc.get_geizhals_whitelist_entries()

        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.geizhals_onlineshop_listing)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.geizhals_onlineshop_listing,
                description= "Stand: Mai 2020",
                url= "https://www.geizhals.at",
                logo_url= "http://gzhls.at/b/svgs/geizhals_logo_without_margin.svg"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_whitelists for %s",db_model.EnumWhitelistSources.geizhals_onlineshop_listing.value)
        #import whitelist entries into local db

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.geizhals_onlineshop_listing,
            db_model.EnumWhitelistType.secure_listing,
            df_gh_whitelist,
            limit_imported_items = limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def import_largest_dach_ecommerce_whitelist(limit_imported_items:int=-1):
    """imports largest ecommerce shops in DACH region 2018 whitelist
    """
    try:
        log.mal2_rest_log.info("import largest_dach_ecommerce_whitelist")
        #import local entries from excel sheet
        df_dach_whitelist = localcsvsrc.get_largest_ecommerce_domains_whitelist_entries()

        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.largest_dach_ecommerce)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.largest_dach_ecommerce,
                description= "Stand: 2018",
                url= "https://www.ehi.org/de/top-50-umsatzstaerkste-onlineshops-in-oesterreich"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_whitelists for %s",db_model.EnumWhitelistSources.largest_dach_ecommerce.value)
        #import whitelist entries into local db

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.largest_dach_ecommerce,
            db_model.EnumWhitelistType.secure_listing,
            df_dach_whitelist,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def import_mal2_fake_shop_db_whitelist(limit_imported_items:int=-1):
    """imports mal2 fakeshop db whitelist entries
    """
    try:
        log.mal2_rest_log.info("import_mal2_fake_shop_db_whitelist")
        #query mal2 fake-shop db for online-shop whitelistings
        df_fsdb_whitelist = fakeshopdb.get_all_whitelist_entries(limit_imported_items)

        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.mal2_fake_shop_db)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.mal2_fake_shop_db,
                description= "Laufend aktualisiert",
                url= "https://www.fakeshop.at",
                logo_url= "https://www.fakeshop.at/typo3conf/ext/theme/Resources/Public/images/logo.svg"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_whitelists for %s",db_model.EnumWhitelistSources.mal2_fake_shop_db.value)
        #import whitelist entries into local db

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.mal2_fake_shop_db,
            db_model.EnumWhitelistType.secure_listing,
            df_fsdb_whitelist,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def import_trustedshops_certified_whitelist(limit_imported_items:int=-1):
    """imports trustedshops_de certified shops whitelist entries
    """
    try:
        log.mal2_rest_log.info("import_trustedshops_certified_whitelist")
        #get trustedshops_de certified only shops from csv file for whitelistings
        df_trustedshops_certified_whitelist = localcsvsrc.get_trustedshops_whitelist_entries(valid_trustmark_only=True)

        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.trustedshops_certified)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.trustedshops_certified,
                description= "Stand: Dezember 2020",
                url= "https://www.trustedshops.de",
                logo_url= "https://static.trustedshops.com/img/brand/e-trustedshops_black.svg"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_whitelists for %s",db_model.EnumWhitelistSources.trustedshops_certified.value)
        #import whitelist entries into local db

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.trustedshops_certified,
            db_model.EnumWhitelistType.trustmark,
            df_trustedshops_certified_whitelist,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def import_trustedshops_listing_whitelist(limit_imported_items:int=-1):
    """imports trustedshops_de no trustmark but secure listed shops whitelist entries
    """
    try:
        log.mal2_rest_log.info("import_trustedshops_listing_whitelist")
        #get trustedshops_de no currently valid but once had a trustmark shops from csv file for whitelistings
        df_trustedshops_listing_whitelist = localcsvsrc.get_trustedshops_whitelist_entries(secure_listing_only=True)

        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.trustedshops_listing)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.trustedshops_listing,
                description= "Verzeichnis ehemaliger Gütesiegelträger, Stand: Dezember 2020",
                url= "https://www.trustedshops.de",
                logo_url= "https://static.trustedshops.com/img/brand/e-trustedshops_black.svg"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_whitelists for %s",db_model.EnumWhitelistSources.trustedshops_listing.value)
        #import whitelist entries into local db

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.trustedshops_listing,
            db_model.EnumWhitelistType.secure_listing,
            df_trustedshops_listing_whitelist,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def import_kaufhausoesterreich_listing_whitelist(limit_imported_items:int=-1):
    """imports kaufhaus oesterreich secure listed shops whitelist entries
    """
    try:
        log.mal2_rest_log.info("import_kaufhausoesterreich_listing_whitelist")
        #get kaufhaus-oesterreich listed shops from csv file for whitelistings
        df_kaufhausoesterreich_listing_whitelist = localcsvsrc.get_kaufhausoesterreich_whitelist_entries()

        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.kaufhausoesterreich_listing)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.kaufhausoesterreich_listing,
                description= "Stand: Dezember 2020",
                url= "https://www.fakeshop.at",
                logo_url= "https://www.fakeshop.at/typo3conf/ext/theme/Resources/Public/images/logo.svg"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_whitelists for %s",db_model.EnumWhitelistSources.kaufhausoesterreich_listing.value)
        #import whitelist entries into local db

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.kaufhausoesterreich_listing,
            db_model.EnumWhitelistType.secure_listing,
            df_kaufhausoesterreich_listing_whitelist,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def import_ehi_trustmark_whitelist(limit_imported_items:int=-1):
    """imports ehi-siegel.de trustmark shops whitelist entries
    """
    try:
        log.mal2_rest_log.info("import_ehi_trustmark_whitelist")
        #get ehi trustmark certified shops from csv file for whitelistings
        df_ehi_trustmark_whitelist = localcsvsrc.get_ehi_trustmark_whitelist_entries()

        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.ehisiegel_certified)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.ehisiegel_certified,
                description= "Stand: Dezember 2020",
                url= "https://ehi-siegel.de",
                logo_url= "https://ehi-siegel.de/fileadmin/ehi/templates/assets/img/ehi-logo.png"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_whitelists for %s",db_model.EnumWhitelistSources.ehisiegel_certified.value)
        #import whitelist entries into local db

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.ehisiegel_certified,
            db_model.EnumWhitelistType.trustmark,
            df_ehi_trustmark_whitelist,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def import_handelsverband_listing_whitelist(limit_imported_items:int=-1):
    """imports handelsverband retail.at secure listed shops whitelist entries
    """
    try:
        log.mal2_rest_log.info("import_handelsverband_listing_whitelist")
        #get handelsverband retail.at listed shops from csv file for whitelistings
        df_handelsverband_listing_whitelist = localcsvsrc.get_handelsverband_whitelist_entries()

        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.handelsverband_listing)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.handelsverband_listing,
                description= "Verzeichnis regionaler Onlineshops des Handelsverbands Österreich, Stand: Dezember 2020",
                url= "https://www.kaufsregional.at",
                logo_url= "https://i2.wp.com/retail.at/wp-content/uploads/2019/06/retail_mag_logo.png"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_whitelists for %s",db_model.EnumWhitelistSources.handelsverband_listing.value)
        #import whitelist entries into local db

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.handelsverband_listing,
            db_model.EnumWhitelistType.secure_listing,
            df_handelsverband_listing_whitelist,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)

def import_versandapotheken_at_listing_whitelist(limit_imported_items:int=-1):
    """imports versandapotheken-at from versandhandelsregister as whitelist entries with trustmark
    """
    try:
        log.mal2_rest_log.info("import_versandapotheken_at_listing_whitelist")
        #get handelsverband retail.at listed shops from csv file for whitelistings
        df_versandapotheken_at_listing_whitelist = localcsvsrc.get_versandapotheken_at_whitelist_entries()

        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.versandapotheken_listing_at)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.versandapotheken_listing_at,
                description= "Stand: Februar 2021",
                url= "https://versandapotheken.basg.gv.at/versandapotheken",
                logo_url= "https://www.basg.gv.at/fileadmin/redakteure/A/Fotos_der_Website/Logo-Austria.jpg"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_whitelists for %s",db_model.EnumWhitelistSources.handelsverband_listing.value)
        #import whitelist entries into local db

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.versandapotheken_listing_at,
            db_model.EnumWhitelistType.trustmark,
            df_versandapotheken_at_listing_whitelist,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def import_versandapotheken_de_listing_whitelist(limit_imported_items:int=-1):
    """imports versandapotheken-de from versandhandelsregister as whitelist entries with trustmark
    """
    try:
        log.mal2_rest_log.info("import_versandapotheken_de_listing_whitelist")
        #get handelsverband retail.at listed shops from csv file for whitelistings
        df_versandapotheken_de_listing_whitelist = localcsvsrc.get_versandapotheken_de_whitelist_entries()

        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.versandapotheken_listing_de)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.versandapotheken_listing_de,
                description= "Stand: Februar 2021",
                url= "https://www.basg.gv.at/konsumentinnen/arzneimittel-im-internet/versandapotheken",
                logo_url= "https://www.dimdi.de/static/.content/images/logo-versandhandel.png_419066846.png"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)
        
        log.mal2_rest_log.info("start import_whitelists for %s",db_model.EnumWhitelistSources.handelsverband_listing.value)
        #import whitelist entries into local db

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.versandapotheken_listing_de,
            db_model.EnumWhitelistType.trustmark,
            df_versandapotheken_de_listing_whitelist,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)

def import_falter_listing_whitelist(limit_imported_items:int=-1):
    """imports falter listing of austrian small online shops as whitelist from csv
    """
    try:
        log.mal2_rest_log.info("import_falter_listing_whitelist")
        #fetch the data from csv
        falter_whitelist_df = localcsvsrc.get_falter_csv_whitelist_entries()
        #create whitelist source if not exists
        db_wl_source_entry = db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.falter_onlineshop_listing)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.falter_onlineshop_listing,
                description= "Liste regionaler und österreichischer Onlineshops, Stand: April 2020",
                url= "https://www.falter.at/onlineshop-fibel",
                logo_url= "https://de.m.wikipedia.org/wiki/Datei:FalterLogo.svg"
                )
            #commit whitelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.falter_onlineshop_listing,
            db_model.EnumWhitelistType.secure_listing,
            falter_whitelist_df,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def import_nunukaller_csv_ignorelist(limit_imported_items:int=-1):
    """imports nunukaller listing of austrian small online shops as whitelist from csv
    """
    try:
        log.mal2_rest_log.info("import_nunukaller_csv_ignorelist")
        #fetch the data from csv
        nunukaller_whitelist_df = localcsvsrc.get_nunukaller_csv_whitelist_entries()
        #create whitelist source if not exists
        db_wl_source_entry =db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.nunukaller_onlineshop_listing)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.nunukaller_onlineshop_listing,
                description= "Liste regionaler und österreichischer Onlineshops, Stand: April 2020.",
                url= "https://www.nunukaller.com/",
                #logo_url= "https://de.m.wikipedia.org/wiki/Datei:FalterLogo.svg"
                )
            #commit ignorelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.nunukaller_onlineshop_listing,
            db_model.EnumWhitelistType.secure_listing,
            nunukaller_whitelist_df,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def import_buchhandel_at_listing_whitelist(limit_imported_items:int=-1):
    """imports Hauptverband des österreichischen Buchhandels merchants as whitelist (secure listing) from api-endpoint
    """
    try:
        log.mal2_rest_log.info("import_buchhandel_at_listing_whitelist")
        #fetch the data from csv
        buchhandel_at_whitelist_df = buchhandel_at.get_all_whitelist_entries()
        #create whitelist source if not exists
        db_wl_source_entry =db_handler.get_whitelistsource_db_entry_by_name(db_model.EnumWhitelistSources.buchhandel_listing_at)
        if not db_wl_source_entry:
            db_wl_source_entry = db_model.WhitelistSource(
                name=db_model.EnumWhitelistSources.buchhandel_listing_at,
                description= "Täglich aktualisiert",
                url= "https://www.buchhandel.at",
                logo_url= "https://buchhandel.at/logo-fuer-saferinternet/hvb-logo.gif "
                )
            #commit ignorelist source to db
            db_handler.commit_db_entry(db_wl_source_entry)
            log.mal2_rest_log.info("created whitelist_source %s",db_wl_source_entry.__repr__)

        #common code for handling the db import
        __import_whitelist_data(
            db_wl_source_entry,
            db_model.EnumWhitelistSources.buchhandel_listing_at,
            db_model.EnumWhitelistType.secure_listing,
            buchhandel_at_whitelist_df,
            limit_imported_items= limit_imported_items)

    except Exception as e:
        log.mal2_rest_log.exception("failed import whitelist %s",e)


def __import_whitelist_data(db_wl_source_entry:db_model.WhitelistSource, source:db_model.EnumWhitelistSources, wl_type:db_model.EnumWhitelistType,dataframe, limit_imported_items:int=-1):
    """common importer for whitelist entries via pandas dataframe that contain ['url'] and ['company_name]
    """

    def check_df_data_exists(entry,key):
        ret = True
        try:
            if entry[key] == None or len(str(entry[key])) <=0 or str(entry[key])=='NaN':
                ret = False
        except:
            #in that case the column did not exist
            return False
        return ret

  
    log.mal2_rest_log.info("start import_whitelists for %s",source.value)
    imported_count = 0
    processed_count = 0
    #import whitelist entries into local db
    for index, entry in dataframe.iterrows():
        
        #limit number of imports
        if  limit_imported_items > 0 and processed_count >= limit_imported_items:
                break
        try:
            processed_count += 1
            #mandatory items
            if not check_df_data_exists(entry,'url'):
                raise Exception("url does not exist in imported pandas dataframe")
            if not check_df_data_exists(entry,'company_name'):
                raise Exception("name does not exist in imported pandas dataframe")

            db_wl_entry =  db_handler.get_whitelist_db_entry_by_url_and_name(entry['url'],source)
            #check if existing entry
            if not db_wl_entry:
                #check if site exists
                db_site = db_handler.get_site_db_entry_by_url(entry['url'])
                if not db_site:
                    #create site or update site
                    db_site = db_model.Site(url=entry['url'], status=db_model.EnumSiteStatus.whitelist)
                else:
                    db_site.status = db_model.EnumSiteStatus.whitelist
                
                log.mal2_rest_log.info("import_whitelists adding new whitelist entry to db")

                #fetch existing company entry from db or create new one
                db_company = db_handler.get_company_db_entry_by_name(entry['company_name'])
                if not db_company:
                    db_company = db_model.Company(
                        name = entry['company_name'],
                    )
                #update record with details
                if check_df_data_exists(entry,'company_street'):
                    db_company.street = entry['company_street']
                if check_df_data_exists(entry,'company_zip_code'):
                    db_company.zip_code = entry['company_zip_code']
                if check_df_data_exists(entry,'company_city'):
                    db_company.city =  entry['company_city']
                if check_df_data_exists(entry,'company_country'):
                    db_company.country = entry['company_country']
                if check_df_data_exists(entry,'company_logo_url'):
                    db_company.logo_url =  entry['company_logo_url']

                #build the whitelist db entry
                db_wl_entry = db_model.Whitelist(
                    site=db_site,
                    whitelist_source=db_wl_source_entry,
                    type=wl_type,
                    company=db_company
                )
                if check_df_data_exists(entry,'created_at'):
                    db_wl_entry.timestamp = entry['created_at']

                if check_df_data_exists(entry,'certificate_url'):
                    db_wl_entry.information_link =  entry['certificate_url']

                #commit whitelist entry to db
                db_handler.commit_db_etnries(db_site, db_company, db_wl_entry)
                imported_count += 1
            else:
                log.mal2_rest_log.debug("import_whitelists skipping known entry %s",db_wl_entry.__repr__)
        except:
            log.mal2_rest_log.exception("import_whitelists failed - unsupported pandas import data format for %s",entry.to_string)

    global last_import 
    last_import= datetime.now()
    log.mal2_rest_log.info("Completed import_whitelists items %s of %s for %s",imported_count,processed_count, source)

