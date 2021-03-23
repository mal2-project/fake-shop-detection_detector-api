from swagger_server import logger_config as log
import swagger_server.mal2.sources.sources_utils as sources_utils
import swagger_server.mal2.db.model.db_model as db_model
import pandas as pd
import os
import datetime as dt

resources_input_dir = os.path.abspath(os.getcwd()+"/swagger_server/resources/data/".replace("/",os.path.sep))
falter_filename = "2020_04_01_falter-online-shops.csv"
nunukaller_filename= "2020_04_07_nunukaller-online-shops.csv"
geizhals_filename= "2020_05_26_geizhals-online-shops_eu.csv"
handelsverband_filename= "2020_11_29_handelsverband-online-shops.csv"
ehisiegel_filename = "2020_12_06_ehi-certified-shops.csv"
kaufhaus_at_filename = "2020_12_06_kaufhaus_oesterreich-online-shops.csv"
trustedshops_de_filename = "2020_12_06_trustedshops_de-certified-shops.csv"
versandapotheken_at_filename = "2021_02_03_versandapotheken_register_at.csv"
versandapotheken_de_filename = "2021_02_03_versandapotheken_register_de.csv"


def get_falter_csv_whitelist_entries():   
    """gets the local csv entries scraped from falter database of Austrian small onlineshops to import it as whitelist
    the dataset has undergone QA by ÖIAT.

    Returns:
        dataframe -- pandas dataframe ['url'],['created_at'] or None
    """
    log.mal2_rest_log.info("checking local falter csv datasets for whitelist entries")
    df = __get_csv_entries_base_data(falter_filename)
    #required field for whitelist, not included in csv - use first chars of description
    df['company_name'] = df['description'].apply(lambda x: x if len(x)<=255 else x[0:255])
    df['company_zip_code'] = df['address'].apply(lambda x: x.split(" ")[0])
    df['company_city'] = df['address'].apply(lambda x: x.split(" ",1)[1])
    df = df.where(pd.notnull(df), None)
    return df

def get_nunukaller_csv_whitelist_entries():   
    """gets the local csv entries scraped from nunukaller database of Austrian small onlineshops to import it as whitelist
    the dataset has undergone QA by ÖIAT.

    Returns:
        dataframe -- pandas dataframe ['url'],['created_at'] or None
    """
    log.mal2_rest_log.info("checking local nunukaller csv datasets for whitelist entries")
    df = __get_csv_entries_base_data(nunukaller_filename)
    #required field for whitelist, not included in csv - use first chars of description
    df['company_name'] = df['description'].apply(lambda x: x if len(x)<=255 else x[0:255])
    df = df.where(pd.notnull(df), None)
    return df

def get_geizhals_whitelist_entries():
    """gets the local csv entries for legit shop entries that have been scraped from geizhals.at
    """
    log.mal2_rest_log.info("checking local geizhals csv datasets for whitelist entries")
    return __get_csv_entries_base_data(geizhals_filename)

def get_most_visited_domains_ignorelist_entries():
    """gets the local excel entries on most visited domains DACH region + world for 2018 and partially 2016
    for source see excel sheet or the dataframe['origin_link]
    """
    log.mal2_rest_log.info("checking local excel file on most visited domains datasets for ignorelist entries")
    most_visited_domains = resources_input_dir+os.path.sep+"2020_05_22_most_visited_domains.xlsx"
    return __get_excel_whitelist_domains_entries(most_visited_domains)

def get_largest_ecommerce_domains_whitelist_entries():
    """gets the local excel entries on most largest ecommerce shops of the DACH region for 2018
    for source see excel sheet or the dataframe['origin_link]
    """
    log.mal2_rest_log.info("checking local excel file on largest ecommerce domains datasets for whitelist entries")
    mlargest_ecommerce_domains = resources_input_dir+os.path.sep+"2020_05_22_umsatzstaerkste_online_shops.xlsx"
    return __get_excel_whitelist_domains_entries(mlargest_ecommerce_domains)

def get_trustedshops_whitelist_entries(valid_trustmark_only=False, secure_listing_only=False):
    """gets the local csv entries for legit shop entries that have been scraped from trustedshops.de
    valid_trustmark_only=True only returns sites with existing valid trustmark
    secure_listing_only=True only returns sites with formerly existing but no longer valid trustmark
    default returns all trustedshops csv entries as pandas dataframe
    """
    log.mal2_rest_log.info("checking local trustedshops csv datasets for whitelist entries. valid_trustmark_only: %s, secure_listing_only: %s", valid_trustmark_only,secure_listing_only)
    df = __get_csv_entries_base_data(trustedshops_de_filename)
    if valid_trustmark_only == True:
        df = df[df['trustmark_status']=='VALID']
    elif secure_listing_only == True:
        df = df[df['trustmark_status']!='VALID']

    #required field for whitelist, not handled by csv import
    df['company_name'] = df['name'].apply(lambda x: x.split('.')[0])
    #replace nan data with None values
    df = df.where(pd.notnull(df), None)
    #rename fields as required by whitelist importer
    df.rename(columns={'logo':'company_logo_url'}, inplace=True)
    log.mal2_rest_log.info("number of entries received: %s from: %s",df.size, trustedshops_de_filename)

    return df

def get_kaufhausoesterreich_whitelist_entries():
    """gets the local csv entries for legit shop entries that have been scraped from kaufhaus-oesterreich.at
    and returns all csv entries as pandas dataframe
    """
    log.mal2_rest_log.info("checking local kaufhausoesterreich csv datasets for whitelist entries.")
    df = __get_csv_entries_base_data(kaufhaus_at_filename)

    #required field for whitelist, not handled by csv import
    df['company_name'] = df['url'].apply(lambda x: ' '.join(x.split('.')[:-1]))
    #replace nan data with None values
    df = df.where(pd.notnull(df), None)
    log.mal2_rest_log.info("number of entries received: %s from: %s",df.size, kaufhaus_at_filename)

    return df

def get_ehi_trustmark_whitelist_entries():
    """gets the local csv entries for legit shop entries with trustmark that have been scraped from ehi-siegel.de
    and returns all csv entries as pandas dataframe
    """
    log.mal2_rest_log.info("checking local ehi_trustmark csv datasets for whitelist entries.")
    df = __get_csv_entries_base_data(ehisiegel_filename)

    #required field for whitelist, not handled by csv import
    df['company_name'] = df['name'].apply(lambda x: x.split('.')[0])
    #replace nan data with None values
    df = df.where(pd.notnull(df), None)
    #rename fields as required by whitelist importer
    df.rename(columns={'certificateurl':'certificate_url'}, inplace=True)
    log.mal2_rest_log.info("number of entries received: %s from: %s",df.size, ehisiegel_filename)

    return df

def get_handelsverband_whitelist_entries():
    """gets the local csv entries for legit shop entries that have been scraped from retail.at
    and returns all csv entries as pandas dataframe
    """
    log.mal2_rest_log.info("checking local handelsverband csv datasets for whitelist entries.")
    df = __get_csv_entries_base_data(handelsverband_filename)

    #required field for whitelist, not handled by csv import
    df['company_name'] = df['url'].apply(lambda x: ' '.join(x.split('.')[:-1]))
    #replace nan data with None values
    df = df.where(pd.notnull(df), None)
    log.mal2_rest_log.info("number of entries received: %s from: %s",df.size, handelsverband_filename)

    return df

def get_versandapotheken_at_whitelist_entries():
    """gets the local csv entries for legit shop entries that have been scraped from https://versandapotheken.basg.gv.at/versandapotheken
    and returns all csv entries as pandas dataframe
    """
    log.mal2_rest_log.info("checking local versandapotheken-at csv datasets for whitelist entries.")
    df = __get_csv_entries_base_data(versandapotheken_at_filename)
    #does already provide all required fields for whitelist within the csv
    #replace nan data with None values
    df = df.where(pd.notnull(df), None)
    #print(df.head())
    log.mal2_rest_log.info("number of entries received: %s from: %s",df.size, versandapotheken_at_filename)
    return df

def get_versandapotheken_de_whitelist_entries():
    """gets the local csv entries for legit shop entries that have been scraped from https://www.dimdi.de/dynamic/de/arzneimittel/versandhandel/
    and returns all csv entries as pandas dataframe
    """
    log.mal2_rest_log.info("checking local versandapotheken-de csv datasets for whitelist entries.")
    df = __get_csv_entries_base_data(versandapotheken_de_filename)
    #does already provide all required fields for whitelist within the csv
    #replace nan data with None values
    df = df.where(pd.notnull(df), None)
    #print(df.head())
    log.mal2_rest_log.info("number of entries received: %s from: %s",df.size, versandapotheken_de_filename)
    return df

def __get_csv_entries_base_data(filename):   
    """operates on siteurl column of csv, renames it to url and adds a created_at datetime column

    Returns:
        dataframe -- pandas dataframe ['url'],['created_at'] or None
    """
    CSV_PATH = resources_input_dir+os.path.sep+filename
    if os.path.exists(CSV_PATH):
        #now cleanup the resulting csv - remove duplicates
        data = pd.read_csv(CSV_PATH, sep=';') 
        # Preview the first 5 lines of the loaded data 
        # data.head()

        if not ('siteurl' in data.columns):
            return None

        # dropping ALL duplicte values 
        data.drop_duplicates(subset ="siteurl", 
                            keep = 'first', inplace = True) 

        data = data.sort_values(by=['siteurl'], ascending=True)
        # rename the existing DataFrame column (rather than creating a copy) 
        data.rename(columns={'siteurl': 'url'}, inplace=True)
        #apply base_url_extraction to all entries
        data['url'] = data['url'].apply(sources_utils.extract_base_url)
        #get the date from the filename
        date = filename[:10]
        rdate = dt.datetime.strptime(date,'%Y_%m_%d')
        data['created_at'] = rdate
        log.mal2_fakeshop_db_log.info("number of entries received: %s from: %s",data.size, CSV_PATH)
        return data
    else:
        log.mal2_fakeshop_db_log.error("no data found for csv_ignorelist at: %s",CSV_PATH)
        return None

def __get_excel_whitelist_domains_entries(whitelist_data_excel_file):
    """reads the excel on most visited domains or largest ecommerce reatilers DACH region that follow both the same data strucure
    and returns the data (all entries of all tabs) within a pandas dataframe
    
    Returns:
        dataframe -- pandas dataframe ['url'],['company_name',['company_type],['origin_link] or None
    """
    if os.path.exists(whitelist_data_excel_file):
        #add all sheets (except mapping one)
        sheets = pd.ExcelFile(whitelist_data_excel_file).sheet_names
        df = pd.DataFrame()
        for sheet in sheets:
            if sheet != 'Mapping':
                #print(sheet)
                df = df.append(pd.read_excel(whitelist_data_excel_file, sheet),sort=True)
        #print(df.columns)
        #df = pd.read_excel(most_visited_domains, sheetname='Austria2016')
        df = df[['Domain','Eigentümer', 'mal2-mapping','source']].copy()
        #replace nan data with None values
        df = df.where(pd.notnull(df), None)

        df.rename(columns={'Domain': 'url', 'Eigentümer': 'company_name', 'mal2-mapping':'company_type', 'source':'origin_link'}, inplace=True)
        df.drop_duplicates(subset ="url",keep = 'first', inplace = True) 
        df = df.sort_values(by=['url'], ascending=True)
        log.mal2_rest_log.info("number of entries received: %s from: %s",df.size, whitelist_data_excel_file)
        return df
    else:
        log.mal2_rest_log.error("no data found for most_visited_domains_excel_whitelist at: %s",whitelist_data_excel_file)
        return None