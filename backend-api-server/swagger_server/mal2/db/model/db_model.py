import sqlalchemy as sql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint
from datetime import datetime
import enum

Base = declarative_base()

#Enums used within the db tables
class EnumSiteStatus(enum.Enum):
    """[summary]
    Possible Site Status that's manually confirmed e.g. type of unknown, legit (whitelist), fake-shop, brand-counterfeiter, etc (Blacklist)
    """
    #all sites if we don't know their status - inlcuding the ones we created predictions for 
    unknown = "unknown"
    # whitelisted site
    whitelist = "whitelist"
    # ignored site e.g. orf.at
    ignore = "ignorelist"
    # blacklisted site
    blacklist = "blacklist"
    # greylisted site
    greylist = "greylist"

class EnumBlacklistType(enum.Enum):
    fraudulent_online_shop = "fraudulent_online_shop"
    fraudulent_brand_counterfeiter = "fraudulent_brand_counterfeiter"
    fraudulent_streaming_platform = "fraudulent_streaming_platform"
    fraudulent_real_estate_agency = "fraudulent_real_estate_agency"
    fraudulent_travel_agency_or_booking_platform = "fraudulent_travel_agency_or_booking_platform"
    fraudulent_craft_service = "fraudulent_craft_service"
    fraudulent_freight_forwarder = "fraudulent_freight_forwarder"
    fraudulent_survey_platform= "fraudulent_survey_platform"
    other = "other"

class EnumGreylistType(enum.Enum):
    shop_dropshipping = "shop_dropshipping"
    shop_not_located_in_the_eu = "shop_not_located_in_the_eu"
    other = "other"

class EnumWhitelistType(enum.Enum):
    """[summary]
    Currently supported Whitelist types
    """
    trustmark = "trustmark"
    secure_listing = "secure_listing"
    unknown = "unknown"

class EnumIgnoreListCategory(enum.Enum):
    """[summary]
    Currently supported IgnoreList kategory names
    """
    ecommerce = "ecommerce"
    media_or_entertainment = "media_or_entertainment"
    blog = "blog"
    business = "business"
    crowdfunding = "crowdfunding"
    educational = "educational"
    nonprofit = "nonprofit"
    personal = "personal"
    portfolio = "portfolio"
    portal = "portal"
    social_media = "social_media"
    search_engine = "search_engine"
    internet_forum = "internet_forum"
    webbased_application = "webbased_application"
    unknown = "unknown"

class EnumBlacklistSources(enum.Enum):
    """[summary]
    Currently supported BlacklistSources names
    """
    mal2_fake_shop_db = "Fakeshop-Detector Datenbank"
    watchlist_internet_listing = "Watchlist Internet"

class EnumGreylistSources(enum.Enum):
    """[summary]
    Currently supported GreylistSources names
    """
    watchlist_internet_listing = "Watchlist Internet"

class EnumWhitelistSources(enum.Enum):
    """[summary]
    Currently supported WhitelistSources names
    """
    ecommerce_guetezeichen_at = "Österreichisches E-Commerce Gütezeichen"
    schweizer_guetezeichen_ch = "Zertifizierte Onlineshops der Schweiz"
    geizhals_onlineshop_listing = "der Geizhals-Händlerliste"
    largest_dach_ecommerce = "der Liste umsatzstärkster Onlineshops der DACH Region"
    mal2_fake_shop_db = "der Fakeshop-Detector Liste, die manuell überprüft wurde"
    trustedshops_certified = "Trusted Shops Gütezeichen"
    trustedshops_listing = "der Trusted Shops Händlerliste"
    kaufhausoesterreich_listing = "der Österreichischen Händlerliste, die manuell überprüft wurde"
    ehisiegel_certified = "Gütesiegel EHI"
    handelsverband_listing = "der Kaufsregional Händlerliste"
    versandapotheken_listing_at = "Versandapotheke aus Österreich "
    versandapotheken_listing_de = "Versandapotheke aus Deutschland"
    falter_onlineshop_listing = "der Falter-Onlineshop-Fibel"
    nunukaller_onlineshop_listing = "der Nunu Kaller-Liste"
    buchhandel_listing_at = "der Händlerliste des Österreichischen Buchhandels"

class EnumIgnorelistSources(enum.Enum):
    """[summary]
    Currently supported IgnorelistSources names
    """
    mal2_fake_shop_db = "Fakeshop.at Datenbank"
    most_visited_domains = "Meistbesuchte Domains der DACH Region"

class EnumPredictionProcessingStatus(enum.Enum):
    """[summary]
    status codes for model based prediction e.g. ongoing, completed or failed
    """
    processing = "processing"
    completed = "completed"
    failed = "failed"

#Definition of db tables
class Prediction(Base):
    """database table prediction stores the mal2_models prediction
    """
    __tablename__ = "prediction"
    id = sql.Column(sql.BigInteger , primary_key=True)

    site_id = sql.Column(sql.Integer, sql.ForeignKey('site.id'), nullable=False)
    site = relationship("Site",lazy="joined")
    html_hash = sql.Column(sql.String(256))
    prediction = sql.Column(sql.Float)
    algorithm = sql.Column(sql.String(32))
    model_version = sql.Column(sql.String(32))
    timestamp = sql.Column(
        sql.DateTime, default=datetime.now, onupdate=datetime.now
    )
    def __repr__(self):
        return "<Prediction(id='%s', site='%s', html_hash='%s', prediction='%s', algorithm='%s', model_version='%s', timestamp='%s')>" % (self.id, self.site, self.html_hash, self.prediction, self.algorithm, self.model_version, self.timestamp)

class PredictionStatus(Base):
    """ status of predicting upon a site
    """
    __tablename__ = "predictionstatus"
    id = sql.Column(sql.BigInteger , primary_key=True)
    url = sql.Column(sql.String(256), nullable=False)
    status = sql.Column(sql.Enum(EnumPredictionProcessingStatus), nullable=False)
    UniqueConstraint(url)
    timestamp = sql.Column(
        sql.DateTime, default=datetime.now, onupdate=datetime.now
    )
    def __repr__(self):
        return "<PredictionStatus(id='%s', url='%s', status='%s', timestamp='%s')>" % (self.id, self.url, self.status, self.timestamp)

class Site(Base):
    """ website information master table
    """
    __tablename__ = "site"
    id = sql.Column(sql.BigInteger , primary_key=True)
    url = sql.Column(sql.String(256), nullable=False)
    UniqueConstraint(url)
    status = sql.Column(sql.Enum(EnumSiteStatus), nullable=False, default=EnumSiteStatus.unknown)
    def __repr__(self):
        return "<Site(id='%s', url='%s', status='%s')>" % (self.id, self.url, self.status)

class Blacklist(Base):
    """ blacklist information master table
    """
    __tablename__ = "blacklist"
    id = sql.Column(sql.BigInteger , primary_key=True)

    site_id = sql.Column(sql.Integer, sql.ForeignKey('site.id'), nullable=False)
    site = relationship("Site",lazy="joined")
    blacklist_source_id = sql.Column(sql.Integer, sql.ForeignKey('blacklist_source.id'), nullable=False)
    blacklist_source = relationship("BlacklistSource",lazy="joined")
    UniqueConstraint(site_id, blacklist_source_id)
    type = sql.Column(sql.Enum(EnumBlacklistType), nullable=False, default=EnumBlacklistType.other)
    timestamp = sql.Column(
        sql.DateTime, default=datetime.now
    )
    information_link = sql.Column(sql.String(256))
    screenshot_link = sql.Column(sql.String(256))
    def __repr__(self):
        return "<Blacklist(id='%s', site='%s', blacklist_source='%s', type='%s', timestamp='%s', information_link='%s', screenshot_link='%s')>" % (self.id, self.site, self.blacklist_source, self.type, self.timestamp, self.information_link, self.screenshot_link)

class BlacklistSource(Base):
    """ blacklistsource source/origin information master table
    """
    __tablename__ = "blacklist_source"
    id = sql.Column(sql.BigInteger , primary_key=True)
    name = sql.Column(sql.Enum(EnumBlacklistSources), nullable=False)
    description = sql.Column(sql.String(512))
    url = sql.Column(sql.String(256))
    logo_url = sql.Column(sql.String(256))
    UniqueConstraint(name)
    def __repr__(self):
        return "<BlacklisSource(id='%s', name='%s', description='%s', url='%s', logo_url='%s')>" % (self.id, self.name, self.description, self.url, self.logo_url)

class Greylist(Base):
    """ greylist information master table
    """
    __tablename__ = "greylist"
    id = sql.Column(sql.BigInteger , primary_key=True)

    site_id = sql.Column(sql.Integer, sql.ForeignKey('site.id'), nullable=False)
    site = relationship("Site",lazy="joined")
    greylist_source_id = sql.Column(sql.Integer, sql.ForeignKey('greylist_source.id'), nullable=False)
    greylist_source = relationship("GreylistSource",lazy="joined")
    UniqueConstraint(site_id, greylist_source_id)
    type = sql.Column(sql.Enum(EnumGreylistType), nullable=False, default=EnumGreylistType.other)
    timestamp = sql.Column(
        sql.DateTime, default=datetime.now
    )
    information_link = sql.Column(sql.String(256))
    screenshot_link = sql.Column(sql.String(256))
    def __repr__(self):
        return "<Greylist(id='%s', site='%s', greylist_source='%s', type='%s', timestamp='%s', information_link='%s', screenshot_link='%s')>" % (self.id, self.site, self.greylist_source, self.type, self.timestamp, self.information_link, self.screenshot_link)

class GreylistSource(Base):
    """ greylistsource source/origin information master table
    """
    __tablename__ = "greylist_source"
    id = sql.Column(sql.BigInteger , primary_key=True)
    name = sql.Column(sql.Enum(EnumGreylistSources), nullable=False)
    description = sql.Column(sql.String(512))
    url = sql.Column(sql.String(256))
    logo_url = sql.Column(sql.String(256))
    UniqueConstraint(name)
    def __repr__(self):
        return "<GreylisSource(id='%s', name='%s', description='%s', url='%s', logo_url='%s')>" % (self.id, self.name, self.description, self.url, self.logo_url)

class Whitelist(Base):
    """ whitelist information master table
    """
    __tablename__ = "whitelist"
    id = sql.Column(sql.BigInteger , primary_key=True)

    site_id = sql.Column(sql.Integer, sql.ForeignKey('site.id'), nullable=False)
    site = relationship("Site",lazy="joined")
    whitelist_source_id = sql.Column(sql.Integer, sql.ForeignKey('whitelist_source.id'), nullable=False)
    whitelist_source = relationship("WhitelistSource",lazy="joined")
    UniqueConstraint(site_id, whitelist_source_id)
    type = sql.Column(sql.Enum(EnumWhitelistType), nullable=False, default=EnumWhitelistType.unknown)
    timestamp = sql.Column(
        sql.DateTime, default=datetime.now
    )
    information_link = sql.Column(sql.String(256))
    company_id = sql.Column(sql.Integer, sql.ForeignKey('company.id'), nullable=False)
    company = relationship("Company",lazy="joined")
    def __repr__(self):
        return "<Whitelist(id='%s', site='%s', whitelist_source='%s', type='%s', timestamp='%s', information_link='%s', company='%s')>" % (self.id, self.site, self.whitelist_source, self.type, self.timestamp, self.information_link, self.company)

class Company(Base):
    """ company details table
    """
    __tablename__ = "company"
    id = sql.Column(sql.BigInteger , primary_key=True)
    name = sql.Column(sql.String(256), nullable=False)
    street = sql.Column(sql.String(256))
    zip_code = sql.Column(sql.String(10))
    city = sql.Column(sql.String(256))
    country = sql.Column(sql.String(128))
    logo_url = sql.Column(sql.String(256))
    UniqueConstraint(name)
    def __repr__(self):
        return "<Company(id='%s', name='%s', street='%s', zip_code='%s', city='%s', country='%s', logo_url='%s')>" % (self.id, self.name, self.street, self.zip_code, self.city, self.country, self.logo_url)

class WhitelistSource(Base):
    """ whitelistsource source/origin information master table
    """
    __tablename__ = "whitelist_source"
    id = sql.Column(sql.BigInteger , primary_key=True)
    name = sql.Column(sql.Enum(EnumWhitelistSources), nullable=False)
    description = sql.Column(sql.String(512))
    url = sql.Column(sql.String(256))
    logo_url = sql.Column(sql.String(256))
    UniqueConstraint(name)
    def __repr__(self):
        return "<WhitelistSource(id='%s', name='%s', description='%s', url='%s', logo_url='%s')>" % (self.id, self.name, self.description, self.url, self.logo_url)


class Ignorelist(Base):
    """ ignored domains information master table
    """
    __tablename__ = "ignorelist"
    id = sql.Column(sql.BigInteger , primary_key=True)

    site_id = sql.Column(sql.Integer, sql.ForeignKey('site.id'), nullable=False)
    site = relationship("Site",lazy="joined")
    ignorelist_source_id = sql.Column(sql.Integer, sql.ForeignKey('ignorelist_source.id'), nullable=False)
    ignorelist_source = relationship("IgnorelistSource",lazy="joined")
    category = sql.Column(sql.Enum(EnumIgnoreListCategory), nullable=False, default=EnumIgnoreListCategory.unknown)
    UniqueConstraint(site_id, ignorelist_source_id)
    timestamp = sql.Column(
        sql.DateTime, default=datetime.now
    )
    def __repr__(self):
        return "<Ignorelist(id='%s', site='%s', ignorelist_source='%s', category='%s', timestamp='%s')>" % (self.id, self.site, self.ignorelist_source, self.category, self.timestamp)

class IgnorelistSource(Base):
    """ ignorelist sources/origin information master table
    """
    __tablename__ = "ignorelist_source"
    id = sql.Column(sql.BigInteger , primary_key=True)
    name = sql.Column(sql.Enum(EnumIgnorelistSources), nullable=False)
    description = sql.Column(sql.String(512))
    url = sql.Column(sql.String(256))
    logo_url = sql.Column(sql.String(256))
    UniqueConstraint(name)
    def __repr__(self):
        return "<IgnorelistSource(id='%s', name='%s', description='%s', url='%s', logo_url='%s')>" % (self.id, self.name, self.description, self.url, self.logo_url)