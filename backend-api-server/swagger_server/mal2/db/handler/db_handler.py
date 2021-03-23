import sqlalchemy as sql
import sqlalchemy.orm as sql_orm
import swagger_server.mal2.db.model.db_model as db_model
from swagger_server import logger_config as log
from typing import List
import os
import pandas as pd
from datetime import datetime

dbpool_size = 20 
dbmax_overflow = 10
engine = sql.create_engine('postgresql://mal2user:mal2pass@127.0.0.1:54320/mal2restdb',pool_size=dbpool_size, max_overflow=dbmax_overflow)
connection = engine.connect()
metadata = sql.MetaData()
Session = sql_orm.scoped_session(sql_orm.sessionmaker(bind=engine))
Base = db_model.Base

#def create_table(connection):
#    emp = sql.Table('emp', metadata,
#              sql.Column('Id', sql.Integer()),
#              sql.Column('name', sql.String(255), nullable=False),
#              sql.Column('salary', sql.Float(), default=100.0),
#              sql.Column('active', sql.Boolean(), default=True)
#              )
#    #create the table
#    metadata.create_all(engine) 

def initDb(re_init=False):
    """initializes the database - and checks if re-creation of db is required when Site table is missing

    Keyword Arguments:
        re_init {bool} -- force re-init of database structure and csv data import to db (default: {False})
    """
    def check_db_exists():
        try:
            pred_table = sql.Table("site", metadata, autoload=True, autoload_with=engine)
            return True
        except Exception as err:
            return False
            
    def do_re_init():
        log.mal2_rest_log.info("re-init db - drop and create all tables")
        #drop and create all db tables
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        #import saved predictions from disc
        import_db_predictions_from_disc(limit_imported_items=10)

    #re-init when flag is passed
    if re_init:
        do_re_init()
        return

    if check_db_exists()==False:
        log.mal2_rest_log.info("site table does not exist - call re-init")
        do_re_init()
    else:
        log.mal2_rest_log.debug("no re-init - continue working with existing db structure and data")
        
def check_db_data_exists():
    try:
        blacklist_entries_db = get_all_best_blacklist_db_entries()
        if len(blacklist_entries_db)>0:
            return True
        return False
    except Exception as err:
        return False

def commit_db_etnries(*db_model_elems):
    """commits multiple db_model objects within a commit to db 

    Arguments:
        db_model_elems -- sequence of sqlalchemy db model types defined in db_model.py
    """
    for db_model_elem in db_model_elems:
        log.mal2_rest_log.info("db adding: %s with %s for Session commit", type(db_model_elem).__name__, db_model_elem.__repr__)
        Session.add(db_model_elem)
    
    try:
        Session.commit()
        log.mal2_rest_log.info("db successfully committed added entries")
    except Exception as e:
        log.mal2_rest_log.warn("db failed on committing added entries due to: %s",e)
        Session.rollback()
        #exception forwarded to ui
        raise Exception("server error occurred") 

def commit_db_entry(db_model_elem):
    """commits a single db_model object to db 

    Arguments:
        db_model_elem -- sqlalchemy db model type defined in db_model.py

    Returns:
        db_model_elem -- refreshed version of the ingested db_type object
    """
    try: 
        Session.add(db_model_elem)
        Session.commit()
        #refresh object e.g. with auto generated id
        Session.refresh(db_model_elem)
        log.mal2_rest_log.info("db successfully committed entry int table: %s with %s ", type(db_model_elem).__name__, db_model_elem.__repr__)
    except Exception as e:
        log.mal2_rest_log.warn("db failed on committing entry int table: %s with %s err: %s", type(db_model_elem).__name__, db_model_elem.__repr__,e)
        Session.rollback()
        #exception forwarded to ui
        raise Exception("server error occurred") 
    return db_model_elem


def get_site_db_entry_all() -> List[db_model.Site]:
    """Fetches a list of all entries of the db table site

    Returns:
        List[db_model.Site] -- List of all db_model.Site entries or empty list
    """
    return Session.query(db_model.Site).all()

def get_site_db_entry_by_url(url:str) -> db_model.Site:
    """Fetches a  site from the db table site exact matching the url

    Arguments:
        url {str} -- query url, note: starting without http://

    Returns:
        db_model.Site -- db_model.Site object or None
    """
    return Session.query(db_model.Site).filter_by(url=url).first()

def get_site_db_entry_by_siteID(siteID:int) -> db_model.Site:
    """Fetches a  site from the db table site exact matching the siteID

    Arguments:
        siteID {int} -- query for db_site_id

    Returns:
        db_model.Site -- db_model.Site object or None
    """
    return Session.query(db_model.Site).filter_by(id=siteID).first()

def get_prediction_db_entry_by_site(site:db_model.Site, model_name:None) -> db_model.Prediction:
    """Fetches the most recent prediction from the db table predictions matching the given site

    Arguments:
        site {db_model.Site} -- query with existing db_model.Site
        model_name {db_model.Prediction.algorithm} -- query with existing algorithm

    Returns:
        db_model.Prediction -- db_model.Prediction object or None
    """
    return __get_prediction_db_entry_by_site_query(site,model_name).first()

def get_prediction_db_entry_by_site_all(site:db_model.Site, model_name=None) -> List[db_model.Prediction]:
    """Fetches all existing predictions from the db table predictions matching the given site

    Arguments:
        site {db_model.Site} -- query with existing db_model.Site
        model_name {db_model.Prediction.algorithm} -- query with existing algorithm

    Returns:
        List[db_model.Prediction] -- db_model.Prediction list or empty list
    """
    return __get_prediction_db_entry_by_site_query(site,model_name).all()
    
def __get_prediction_db_entry_by_site_query(site:db_model.Site, model_name=None) -> sql_orm.Query:
    query = Session.query(db_model.Prediction).filter_by(site=site)
    if model_name:
        query = query.filter_by(algorithm=model_name)
    query = query.order_by(db_model.Prediction.timestamp.desc())
    return query


def get_predictionstatus_db_entry_by_url(url:str, status:db_model.EnumPredictionProcessingStatus=None) -> db_model.PredictionStatus:
    """Fetches the most recent prediction status from the db table predictionstatus matching the given url (not db site!) and optional a specific status

    Arguments:
        url {str} -- query for site url (not site db object!)
        status {db_model.EnumPredictionProcessingStatus} -- optional query param to restrict to a specific status

    Returns:
        db_model.PredictionStatus -- db_model.PredictionStatus object or None
    """
    return __get_predictionstatus_db_entry_by_url_query(url,status).first()    

def __get_predictionstatus_db_entry_by_url_query(url:str, status:db_model.EnumPredictionProcessingStatus=None) -> sql_orm.Query:
    query = Session.query(db_model.PredictionStatus).filter_by(url=url)
    if status:
        query = query.filter_by(status=status)
    #order by most most recent/latest first    
    query = query.order_by(db_model.PredictionStatus.timestamp.desc())
    return query


def get_blacklistsource_db_entry_by_name(name:db_model.EnumBlacklistSources) -> db_model.BlacklistSource:
    """Fetches the BlacklistSource from the db table blacklist_source matching the name identifier. None if not exists.

    Arguments:
        name {db_model.EnumBlacklistSources} -- query by BlacklistSource name

    Returns:
        db_model.BlacklistSource -- db_model.BlacklistSource object or None
    """
    return Session.query(db_model.BlacklistSource).filter_by(name=name).first()

def get_blacklist_db_entry_by_url_and_source(url:str, bl_source:db_model.BlacklistSource) -> db_model.Blacklist:
    """Fetches the most important Blacklist entry from the db table blacklist matching the url and BlacklistSource. None if not exists.
    best/highest ranked: is with lowest blacklist_source_id ID as most important source get created first, then by newest blacklist timestamp and 
    (as some timestamp don't provide time element) finally blacklist id

    Arguments:
        url {Str} -- query url, note: starting without http://
        bl_source {db_model.BlacklistSource} -- query with existing db_model.BlacklistSource

    Returns:
        db_model.Blacklist -- db_model.Blacklist object or None
    """
    site = get_site_db_entry_by_url(url)
    if not site:
        return None    
    return Session.query(db_model.Blacklist).filter_by(site=site, blacklist_source=bl_source).order_by(
        db_model.Blacklist.blacklist_source_id.asc(),db_model.Blacklist.timestamp.desc(), db_model.Blacklist.id.desc()
        ).first()

def get_blacklist_db_entry_by_url_and_name(url:str,bl_source_name:db_model.EnumBlacklistSources) -> db_model.Blacklist:
    """Fetches the most important Blacklist entry from the db table blacklist matching the url and blacklist_source's name. None if not exists.
    best/highest ranked: is with lowest blacklist_source_id ID as most important source get created first, then by newest blacklist timestamp and 
    (as some timestamp don't provide time element) finally blacklist id

    Arguments:
        url {Str} -- query url, note: starting without http://
        bl_source {db_model.BlacklistSource} -- query with existing db_model.BlacklistSource

    Returns:
        db_model.Blacklist -- db_model.Blacklist object or None
    """
    bl_source = get_blacklistsource_db_entry_by_name(bl_source_name)
    if not bl_source:
        return None
    return get_blacklist_db_entry_by_url_and_source(url, bl_source)

def get_best_blacklist_db_entry_by_url(url:str) -> db_model.Blacklist:
    """Fetches the most important Blacklist entry from the db table blacklist matching the url independent of blacklist_sources origin. None if not exists.
    best/highest ranked: is with lowest blacklist_source_id ID as most important source get created first, then by newest blacklist timestamp and 
    (as some timestamp don't provide time element) finally blacklist id

    Arguments:
        url {str} -- query url, note: starting without http://

    Returns:
        db_model.Blacklist -- db_model.Blacklist object or None
    """
    site = get_site_db_entry_by_url(url)
    if not site:
        return None    
    return Session.query(db_model.Blacklist).filter_by(site=site).order_by(
        db_model.Blacklist.blacklist_source_id.asc(),db_model.Blacklist.timestamp.desc(), db_model.Blacklist.id.desc()
        ).first()

def get_best_blacklist_db_entry_by_siteID(siteID:int) -> db_model.Blacklist:
    """Fetches the most important Blacklist entry from the db table blacklist matching the url independent of blacklist_sources origin. None if not exists.
    best/highest ranked: is with lowest blacklist_source_id ID as most important source get created first, then by newest blacklist timestamp and 
    (as some timestamp don't provide time element) finally blacklist id

    Arguments:
        siteID {int} -- query with database site_id

    Returns:
        db_model.Blacklist -- db_model.Blacklist object or None
    """
    #check siteID 
    site = get_site_db_entry_by_siteID(siteID)
    if not site:
        return None    
    return Session.query(db_model.Blacklist).filter_by(site=site).order_by(
        db_model.Blacklist.blacklist_source_id.asc(),db_model.Blacklist.timestamp.desc(), db_model.Blacklist.id.desc()
        ).first()

def get_all_best_blacklist_db_entries(pagesize=None, page=None) -> List[db_model.Blacklist]:
    """Fetches all (most important one if more than one per site) Blacklist entries from the db table blacklist independent of blacklist_sources origin.
    best/highest ranked: is with lowest blacklist_source_id ID as most important source get created first, then by newest blacklist timestamp and 
    (as some timestamp don't provide time element) finally blacklist id

    Returns:
        List[db_model.Blacklist] -- List of db_model.Blacklist object or empty list
    """
    query = Session.query(db_model.Blacklist).order_by(
        db_model.Blacklist.site_id,db_model.Blacklist.blacklist_source_id.asc(),db_model.Blacklist.timestamp.desc(), db_model.Blacklist.id.desc()
        ).distinct(db_model.Blacklist.site_id)
    #limit return elements and follow offset
    if pagesize:
        query = query.limit(pagesize)
    if page:
        query = query.offset(page*pagesize)

    return query.all()


def get_greylistsource_db_entry_by_name(name:db_model.EnumGreylistSources) -> db_model.GreylistSource:
    """Fetches the GreylistSource from the db table greylist_source matching the name identifier. None if not exists.

    Arguments:
        name {db_model.EnumGreylistSources} -- query by GreylistSource name

    Returns:
        db_model.GeylistSource -- db_model.GreylistSource object or None
    """
    return Session.query(db_model.GreylistSource).filter_by(name=name).first()

def get_greylist_db_entry_by_url_and_source(url:str, gl_source:db_model.GreylistSource) -> db_model.Greylist:
    """Fetches the most important Greylist entry from the db table greylist matching the url and GreylistSource. None if not exists.
    best/highest ranked: is with lowest greylist_source_id ID as most important source get created first, then by newest greylist timestamp and 
    (as some timestamp don't provide time element) finally greylist id

    Arguments:
        url {Str} -- query url, note: starting without http://
        bl_source {db_model.GreylistSource} -- query with existing db_model.GreylistSource

    Returns:
        db_model.Greylist -- db_model.Greylist object or None
    """
    site = get_site_db_entry_by_url(url)
    if not site:
        return None    
    return Session.query(db_model.Greylist).filter_by(site=site, greylist_source=gl_source).order_by(
        db_model.Greylist.greylist_source_id.asc(),db_model.Greylist.timestamp.desc(), db_model.Greylist.id.desc()
        ).first()

def get_greylist_db_entry_by_url_and_name(url:str,gl_source_name:db_model.EnumGreylistSources) -> db_model.Greylist:
    """Fetches the most important Greylist entry from the db table greylist matching the url and greylist_source's name. None if not exists.
    best/highest ranked: is with lowest greylist_source_id ID as most important source get created first, then by newest greylist timestamp and 
    (as some timestamp don't provide time element) finally greylist id

    Arguments:
        url {Str} -- query url, note: starting without http://
        bl_source {db_model.GreylistSource} -- query with existing db_model.GreylistSource

    Returns:
        db_model.Greylist -- db_model.Greylist object or None
    """
    gl_source = get_greylistsource_db_entry_by_name(gl_source_name)
    if not gl_source:
        return None
    return get_greylist_db_entry_by_url_and_source(url, gl_source)

def get_best_greylist_db_entry_by_url(url:str) -> db_model.Greylist:
    """Fetches the most important Greylist entry from the db table greylist matching the url independent of greylist_sources origin. None if not exists.
    best/highest ranked: is with lowest greylist_source_id ID as most important source get created first, then by newest greylist timestamp and 
    (as some timestamp don't provide time element) finally greylist id

    Arguments:
        url {str} -- query url, note: starting without http://

    Returns:
        db_model.Greylist -- db_model.Greylist object or None
    """
    site = get_site_db_entry_by_url(url)
    if not site:
        return None    
    return Session.query(db_model.Greylist).filter_by(site=site).order_by(
        db_model.Greylist.greylist_source_id.asc(),db_model.Greylist.timestamp.desc(), db_model.Greylist.id.desc()
        ).first()

def get_best_greylist_db_entry_by_siteID(siteID:int) -> db_model.Greylist:
    """Fetches the most important Greylist entry from the db table greylist matching the url independent of greylist_sources origin. None if not exists.
    best/highest ranked: is with lowest greylist_source_id ID as most important source get created first, then by newest greylist timestamp and 
    (as some timestamp don't provide time element) finally greylist id

    Arguments:
        siteID {int} -- query with database site_id

    Returns:
        db_model.Greylist -- db_model.Greylist object or None
    """
    #check siteID 
    site = get_site_db_entry_by_siteID(siteID)
    if not site:
        return None    
    return Session.query(db_model.Greylist).filter_by(site=site).order_by(
        db_model.Greylist.greylist_source_id.asc(),db_model.Greylist.timestamp.desc(), db_model.Greylist.id.desc()
        ).first()

def get_all_best_greylist_db_entries(pagesize=None, page=None) -> List[db_model.Greylist]:
    """Fetches all (most important one if more than one per site) Greylist entries from the db table greylist independent of greylist_sources origin.
    best/highest ranked: is with lowest greylist_source_id ID as most important source get created first, then by newest greylist timestamp and 
    (as some timestamp don't provide time element) finally greylist id

    Returns:
        List[db_model.Greylist] -- List of db_model.Greylist object or empty list
    """
    query = Session.query(db_model.Greylist).order_by(
        db_model.Greylist.site_id,db_model.Greylist.greylist_source_id.asc(),db_model.Greylist.timestamp.desc(), db_model.Greylist.id.desc()
        ).distinct(db_model.Greylist.site_id)
    #limit return elements and follow offset
    if pagesize:
        query = query.limit(pagesize)
    if page:
        query = query.offset(page*pagesize)

    return query.all()

def get_whitelistsource_db_entry_by_name(name:db_model.EnumWhitelistSources) -> db_model.WhitelistSource:
    """Fetches the WhitelistSource from the db table whitelist_source matching the name identifier. None if not exists.

    Arguments:
        name {db_model.EnumWhitelistSources} -- query by WhitelistSource name

    Returns:
        db_model.WhitelistSource -- db_model.WhitelistSource object or None
    """
    return Session.query(db_model.WhitelistSource).filter_by(name=name).first()

def get_whitelist_db_entry_by_url_and_source(url:str, wl_source:db_model.WhitelistSource) -> db_model.Whitelist:
    """Fetches the most important Whitelist entry from the db table whitelist matching the url and WhitelistSource. None if not exists.
    Order is: trustmark above secure listig (type asc), then ordered by whitelist_source_id asc (as most important sources have 
    lower IDs as they get created/imported first) followed by whitelist timestamp (newest first) and whitelist id

    Arguments:
        url {Str} -- query url, note: starting without http://
        bl_source {db_model.WhitelistSource} -- query with existing db_model.WhitelistSource

    Returns:
        db_model.Whitelist -- db_model.Whitelist object or None
    """
    site = get_site_db_entry_by_url(url)
    if not site:
        return None    
    return Session.query(db_model.Whitelist).filter_by(site=site, whitelist_source=wl_source).order_by(
        db_model.Whitelist.type.asc(),db_model.Whitelist.whitelist_source_id.asc(),db_model.Whitelist.timestamp.desc(), db_model.Whitelist.id.desc()
        ).first()

def get_whitelist_db_entry_by_url_and_name(url:str,wl_source_name:db_model.EnumWhitelistSources) -> db_model.Whitelist:
    """Fetches the most important Whitelist entry from the db table whitelist matching the url and whitelist_source's name. None if not exists.
    Order is: trustmark above secure listig (type asc), then ordered by whitelist_source_id asc (as most important sources have 
    lower IDs as they get created/imported first) followed by whitelist timestamp (newest first) and whitelist id

    Arguments:
        url {Str} -- query url, note: starting without http://
        bl_source {db_model.WhitelistSource} -- query with existing db_model.WhitelistSource

    Returns:
        db_model.Whitelist -- db_model.Whitelist object or None
    """
    wl_source = get_whitelistsource_db_entry_by_name(wl_source_name)
    if not wl_source:
        return None
    return get_whitelist_db_entry_by_url_and_source(url, wl_source)

def get_best_whitelist_db_entry_by_siteID(siteID:int) -> db_model.Whitelist:
    """Fetches the most important Whitelist entry from the db table whitelist matching the url independent of whitelist_sources origin. None if not exists.
    best/highest ranked: Order is: trustmark above secure listig (type asc), then ordered by whitelist_source_id asc (as most important sources have 
    lower IDs as they get created/imported first) followed by whitelist timestamp (newest first) and whitelist id

    Arguments:
        siteID {int} -- query with database site_id

    Returns:
        db_model.Whitelist -- db_model.Whitelist object or None
    """
    #check siteID 
    site = get_site_db_entry_by_siteID(siteID)
    if not site:
        return None    
    return Session.query(db_model.Whitelist).filter_by(site=site).order_by(
        db_model.Whitelist.type.asc(),db_model.Whitelist.whitelist_source_id.asc(),db_model.Whitelist.timestamp.desc(), db_model.Whitelist.id.desc()
        ).first()

def get_best_whitelist_db_entry_by_url(url:str) -> db_model.Whitelist:
    """Fetches the most important Whitelist entry from the db table whitelist matching the url independent of whitelist_sources origin. None if not exists.
    best/highest ranked: Order is: trustmark above secure listig (type asc), then ordered by whitelist_source_id asc (as most important sources have 
    lower IDs as they get created/imported first) followed by whitelist timestamp (newest first) and whitelist id

    Arguments:
        url {str} -- query url, note: starting without http://

    Returns:
        db_model.Whitelist -- db_model.Whitelist object or None
    """
    site = get_site_db_entry_by_url(url)
    if not site:
        return None    
    return Session.query(db_model.Whitelist).filter_by(site=site).order_by(
         db_model.Whitelist.type.asc(),db_model.Whitelist.whitelist_source_id.asc(),db_model.Whitelist.timestamp.desc(), db_model.Whitelist.id.desc()
        ).first()

def get_all_best_whitelist_db_entries(pagesize=None, page=None) -> List[db_model.Whitelist]:
    """Fetches all (most important one if more than one per site) Whitelist entries from the db table whitelist independent of whitelist_sources origin.
    Order is: trustmark above secure listig (type asc), then ordered by whitelist_source_id asc (as most important sources have 
    lower IDs as they get created/imported first) followed by whitelist timestamp (newest first) and whitelist id

    Returns:
        List[db_model.Whitelist] -- List of db_model.Whitelist object or empty list
    """
    query = Session.query(db_model.Whitelist).order_by(
        db_model.Whitelist.site_id, db_model.Whitelist.type.asc(),db_model.Whitelist.whitelist_source_id.asc(),db_model.Whitelist.timestamp.desc(), db_model.Whitelist.id.desc()
        ).distinct(db_model.Whitelist.site_id)
    #limit return elements and follow offset
    if pagesize:
        query = query.limit(pagesize)
    if page:
        query = query.offset(page*pagesize)

    return query.all()

def get_company_db_entry_by_name(company_name:str) -> db_model.Company:
    """Fetches a Company entry from the db table matching the companys name. None if not exists.

    Arguments:
        name {str} -- query with existing company name

    Returns:
        db_model.Company -- db_model.Company object or None
    """
    return Session.query(db_model.Company).filter_by(name=company_name).first()

def get_ignorelistsource_db_entry_by_name(name:db_model.EnumIgnorelistSources) -> db_model.IgnorelistSource:
    """Fetches the IgnorelistSource from the db table ignorelist_source matching the name identifier. None if not exists.

    Arguments:
        name {db_model.EnumIgnorelistSources} -- query by IgnorelistSource name

    Returns:
        db_model.IgnorelistSource -- db_model.IgnorelistSource object or None
    """
    return Session.query(db_model.IgnorelistSource).filter_by(name=name).first()

def get_ignorelist_db_entry_by_url_and_source(url:str, il_source:db_model.IgnorelistSource) -> db_model.Ignorelist:
    """Fetches the most important Ignorelist entry from the db table ignorelist matching the url and IgnorelistSource. None if not exists.
    Order is: ignorelist_source_id asc (as most important sources have lower IDs as they get created/imported first) followed 
    by ignorelist timestamp (newest first) and ignorelist id

    Arguments:
        url {Str} -- query url, note: starting without http://
        il_source {db_model.IgnorelistSource} -- query with existing db_model.IgnorelistSource

    Returns:
        db_model.Ignorelist -- db_model.Ignorelist object or None
    """
    site = get_site_db_entry_by_url(url)
    if not site:
        return None    
    return Session.query(db_model.Ignorelist).filter_by(site=site, ignorelist_source=il_source).order_by(
        db_model.Ignorelist.ignorelist_source_id.asc(),db_model.Ignorelist.timestamp.desc(), db_model.Ignorelist.id.desc()
        ).first()

def get_ignorelist_db_entry_by_url_and_name(url:str,il_source_name:db_model.EnumIgnorelistSources) -> db_model.Ignorelist:
    """Fetches the most important Ignorelist entry from the db table ignorelist matching the url and ignorelist_source's name. None if not exists.
    Order is: ignorelist_source_id asc (as most important sources have lower IDs as they get created/imported first) followed 
    by ignorelist timestamp (newest first) and ignorelist id

    Arguments:
        url {Str} -- query url, note: starting without http://
        il_source {db_model.IgnorelistSource} -- query with existing db_model.IgnorelistSource

    Returns:
        db_model.Ignorelist -- db_model.Ignorelist object or None
    """
    il_source = get_ignorelistsource_db_entry_by_name(il_source_name)
    if not il_source:
        return None
    return get_ignorelist_db_entry_by_url_and_source(url, il_source)

def get_best_ignorelist_db_entry_by_url(url:str) -> db_model.Ignorelist:
    """Fetches the most important Ignorelist entry from the db table ignorelist matching the url independent of ignorelist_sources origin. None if not exists.
    Order is: ignorelist_source_id asc (as most important sources have lower IDs as they get created/imported first) followed 
    by ignorelist timestamp (newest first) and ignorelist id

    Arguments:
        url {str} -- query url, note: starting without http://

    Returns:
        db_model.Ignorelist -- db_model.Ignorelist object or None
    """
    site = get_site_db_entry_by_url(url)
    if not site:
        return None    
    return Session.query(db_model.Ignorelist).filter_by(site=site).order_by(
        db_model.Ignorelist.ignorelist_source_id.asc(),db_model.Ignorelist.timestamp.desc(), db_model.Ignorelist.id.desc()
        ).first()

def get_best_ignorelist_db_entry_by_siteID(siteID:int) -> db_model.Ignorelist:
    """Fetches the most important Ignorelist entry from the db table ignorelist matching the url, independent of ignorelist_sources origin. None if not exists.
    Order is: ignorelist_source_id asc (as most important sources have lower IDs as they get created/imported first) followed 
    by ignorelist timestamp (newest first) and ignorelist id

    Arguments:
        siteID {int} -- query with database site_id

    Returns:
        db_model.Ignorelist -- db_model.Ignorelist object or None
    """
    #check siteID 
    site = get_site_db_entry_by_siteID(siteID)
    if not site:
        return None    
    return Session.query(db_model.Ignorelist).filter_by(site=site).order_by(
        db_model.Ignorelist.ignorelist_source_id.asc(),db_model.Ignorelist.timestamp.desc(), db_model.Ignorelist.id.desc()
        ).first()

def get_all_best_ignorelist_db_entries(pagesize=None, page=None) -> List[db_model.Ignorelist]:
    """Fetches all (most important if more than one per site) Ignorelist entries from the db table ignorelist independent of ignorelist_sources origin.
    Order is: ignorelist_source_id asc (as most important sources have lower IDs as they get created/imported first) followed 
    by ignorelist timestamp (newest first) and ignorelist id

    Returns:
        List[db_model.Ignorelist] -- List of db_model.Ignorelist object or empty list
    """
    query = Session.query(db_model.Ignorelist).order_by(
        db_model.Ignorelist.site_id, db_model.Ignorelist.ignorelist_source_id.asc(),db_model.Ignorelist.timestamp.desc(), db_model.Ignorelist.id.desc()
        ).distinct(db_model.Ignorelist.site_id)
    #limit return elements and follow offset
    if pagesize:
        query = query.limit(pagesize)
    if page:
        query = query.offset(page*pagesize)

    return query.all()


prediction_input_dir = os.path.abspath(os.getcwd()+"/swagger_server/resources/predictions/".replace("/",os.path.sep))
prediction_export_file = prediction_input_dir+os.path.sep+"predictions_exported.csv"
prediction_import_file = prediction_input_dir+os.path.sep+"predictions_to_import.csv"
def export_db_predictions_to_disc():
    """fetches all predictions in db and exports them to csv via pandas df
    """
    log.mal2_rest_log.info("export_db_predictions_to_disc")
    try:
        #fetch all predictions from db
        lPredictions =  Session.query(db_model.Prediction).order_by(db_model.Prediction.model_version.asc(), db_model.Prediction.timestamp.asc(), db_model.Prediction.id.asc()).all()
        log.mal2_rest_log.info("exporting %s predictions to %s",len(lPredictions), prediction_export_file)
        #create dataframe columns
        df_export = pd.DataFrame(columns=['url','status','html_hash','prediction','algorithm','model_version','timestamp'])
        
        for i,p in enumerate(lPredictions):
            #add prediction data to dataframe
            df_export.loc[i] = [p.site.url, p.site.status.value, p.html_hash, p.prediction, p.algorithm, p.model_version, p.timestamp]
        
        os.makedirs(prediction_input_dir, exist_ok=True)
        #sort
        df_export.sort_values(by=['model_version', 'url', 'html_hash', 'timestamp'], inplace=True)
        #persist
        df_export.to_csv(prediction_export_file,encoding='utf-8', index=False, sep=';')
    except Exception as e:
        log.mal2_rest_log.error('failed to export_db_predictions_to_disc %s',str(e))


def import_db_predictions_from_disc(limit_imported_items:int=-1):
    """imports stored predictions from csv file to db
    """
    log.mal2_rest_log.info("import_db_predictions_from_disc")
    try:
        if os.path.exists(prediction_import_file):
            log.mal2_rest_log.info("found existing predictions csv file to import from %s",prediction_import_file)
            #read to pandas df
            df_import = pd.read_csv(prediction_import_file, sep=';') 
            log.mal2_rest_log.info("found %s entries in csv to potentially import",df_import['url'].count())
            df_import = df_import.sort_values(by=['url'], ascending=True)
            processed_count = 0
            for row in df_import.itertuples():
                if  limit_imported_items > 0 and processed_count >= limit_imported_items:
                    log.mal2_rest_log.info("maximum number of predictions to import from disc reached")
                    break

                #get or create the db entity site
                site_db = get_site_db_entry_by_url(row.url)
                if site_db == None:
                    #no existing site - need to create one
                    site_db = db_model.Site(url=row.url)
                    commit_db_etnries(site_db)

                lPredictions_db = get_prediction_db_entry_by_site_all(site_db,row.algorithm)
                #make sure we don't already have the exact same prediction imported
                found = False
                for p_db in lPredictions_db:
                    #check the fields 'hash','prediction','algorithm','model_version','timestamp
                    if(str(p_db.html_hash) == str(row.html_hash) and 
                    str(p_db.prediction) == str(row.prediction) and 
                    str(p_db.algorithm) == str(row.algorithm) and
                    str(p_db.model_version) == str(row.model_version) and 
                    str(p_db.timestamp) == str(row.timestamp)):

                        log.mal2_rest_log.debug("skipping import of prediction, already exists %s",str(row))
                        found=True
                
                if found==False:
                    log.mal2_rest_log.info("import of prediction %s",str(row))
                    #create the db entity prediction
                    prediction_db = db_model.Prediction(site=site_db, html_hash = row.html_hash, prediction=float(row.prediction), algorithm=row.algorithm, model_version=row.model_version, timestamp = datetime.strptime(row.timestamp, "%Y-%m-%d %H:%M:%S.%f"))
                    #submit to db
                    commit_db_etnries(prediction_db)
                    processed_count += 1
            log.mal2_rest_log.info("completed import of existing predictions from disc %s",str(processed_count))
        else:
            log.mal2_rest_log.info("no existing predictions found to import - skip import")
    except Exception as e:
        log.mal2_rest_log.error('failed to import_db_predictions_from_disc %s',str(e))