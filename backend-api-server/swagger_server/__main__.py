#!/usr/bin/env python3
import threading
import atexit
import connexion
from flask_cors import CORS
#import logging
import os, shutil
import argparse
from datetime import datetime
from swagger_server import encoder
import swagger_server.mal2.db.handler.db_handler as db_handler
import swagger_server.mal2.db.handler.db_blacklist_handler as db_blacklist_handler
import swagger_server.mal2.db.handler.db_greylist_handler as db_greylist_handler
import swagger_server.mal2.db.handler.db_ignorelist_handler as db_ignorelist_handler
import swagger_server.mal2.db.handler.db_whitelist_handler as db_whitelist_handler
import swagger_server.mal2.crypto.crypto_handler as crypto_handler
import swagger_server.mal2.common.common_utils as utils
from swagger_server import logger_config as log

POOL_TIME = 3600 #Seconds
POOL_TIME2 = 43200 #Seconds
# variables that are accessible from anywhere
commonDataStruct = {}
# lock to control access to variable
dataLock = threading.Lock()
# thread handler
data_import_thread = threading.Thread()
cleanup_thread = threading.Thread()

def start_app(re_init_db=False, use_ssl=False):
    
    def import_data():
        """Imports whitelist, blacklist and ignorelist data if required
        """
        #re-import new ignorelist entries
        if db_ignorelist_handler.check_reimport_required() == True:
            db_ignorelist_handler.import_ignorelists()
        #re-import new greylist entries
        if db_greylist_handler.check_reimport_required() == True:
            db_greylist_handler.import_greylists()
        #re-import new blacklists entries
        if db_blacklist_handler.check_reimport_required() == True:
            db_blacklist_handler.import_blacklists()
        #re-import new whitelists entries
        if db_whitelist_handler.check_reimport_required() == True:
            db_whitelist_handler.import_whitelists()

    #second thread for handling db blacklist import every x hours
    def dataImportThread_interrupt():
        global data_import_thread
        data_import_thread.cancel()

    def dataImportThread_check_for_data():
        """rechecks every POOL_TIME if data import is required
        """
        global commonDataStruct
        global data_import_thread
        with dataLock:
            #FIXME Do your stuff with commonDataStruct here (currently no data lock)
            import_data()

        # Set the next thread to happen
        data_import_thread = threading.Timer(POOL_TIME, dataImportThread_check_for_data, ())
        data_import_thread.start()   

    def dataImportThread_start(re_init_db):
        # Do initialisation stuff here
        global data_import_thread
        #skip initial import of data if re-init db is false or data already exists
        if re_init_db == True or db_handler.check_db_data_exists()== False:
            log.mal2_rest_log.debug("re-import of data schedued to stark in 5 seconds")
            # Create your thread - trigger initial import 5 sec after launching thread
            data_import_thread = threading.Timer(5, dataImportThread_check_for_data, ())
        else:
            log.mal2_rest_log.debug("re-import of data schedued to stark in %s seconds",POOL_TIME)
            # Create your thread - data exists - check for re-import way later
            data_import_thread = threading.Timer(POOL_TIME, dataImportThread_check_for_data, ())
            
        data_import_thread.start()

    #third applicaton thread for handling cleanup of logs, crypto keys, etc. every x hours
    def cleanupThread_start(re_init_db):
        # Do initialisation stuff here
        global cleanup_thread
        #skip initial import of data if re-init db is false or data already exists
        if re_init_db == True:
            log.mal2_rest_log.debug("cleanup job scheduled to stark in 5 seconds")
            # Create your thread - db re-initialized - trigger initial cleanup 5 sec after launching thread
            cleanup_thread = threading.Timer(5, cleanupThread_check_for_data_to_dispose, ())
        else:
            log.mal2_rest_log.debug("cleanup job schedued to stark in %s seconds",POOL_TIME2)
            # Create your thread - existing application - check for cleanup way later
            cleanup_thread = threading.Timer(POOL_TIME2, cleanupThread_check_for_data_to_dispose, ())
            
        cleanup_thread.start()
    
    def cleanupThread_interrupt():
        global cleanup_thread
        cleanup_thread.cancel()

    def cleanupThread_check_for_data_to_dispose():
        """rechecks every POOL_TIME2 and executes data cleanup if required
        """
        global commonDataStruct
        global cleanup_thread
        with dataLock:
            #FIXME Do your stuff with commonDataStruct here (currently no data lock)
            #check for logs to dispose
            log.check_and_throw_away_logs()
            #persist prediction data
            db_handler.export_db_predictions_to_disc()

        # Set the next thread to happen
        cleanup_thread = threading.Timer(POOL_TIME2, cleanupThread_check_for_data_to_dispose, ())
        cleanup_thread.start()   

    #defining function to run on shutdown
    def close_and_cleanup():
        #persist prediction data
        db_handler.export_db_predictions_to_disc()

        try:
            #close db connection
            log.mal2_rest_log.info("dispose db engine")
            db_handler.Session.close()
            db_handler.engine.dispose()
        except Exception as e:
            log.mal2_rest_log.error("close_and_cleanup close db error: %s",str(e))
        try:
            #note mal2-model package creates data/verify_sites for scraped html dir - delete
            verify_output_dir = os.path.abspath(os.getcwd()+"/data/".replace("/",os.path.sep))
            log.mal2_rest_log.debug("cleanup of mal2_model package leftovers in verify_output_dir: %s", verify_output_dir)
            utils.nukedir_recursively(verify_output_dir)
        except Exception as e:
            log.mal2_rest_log.error("close_and_cleanup nuke verify_output_dir error: %s",str(e))
        try:    
            #shutdown data import thread
            log.mal2_rest_log.info("interrupt data import thread")
            dataImportThread_interrupt()
            log.mal2_rest_log.info("interrupt data cleanup thread")
            cleanupThread_interrupt()
        except Exception as e:
            log.mal2_rest_log.error("close_and_cleanup interrupting threads error: %s",str(e))

    #logging.basicConfig(filename='mal2-rest-log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    log.init()
    log.mal2_rest_log.info('Started MAL2 rest-api')

    app = connexion.App(__name__, specification_dir='./swagger/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'Fake-Shop Detector API'})
    # add CORS support to send Access-Control-Allow-Origin header
    CORS(app.app)

    #Register cleanup function when the Ctr+C command is received 
    atexit.register(close_and_cleanup)

    try:
        print("Hello MAL2 fakeshop-plugin REST API")
        #setup crypto
        crypto_handler.initKeys()
        #setup database
        db_handler.initDb(re_init_db)
        # Initiate data re-import check thread for blacklist/whitelist data
        dataImportThread_start(re_init_db)
        #Initiate data cleanup thread
        cleanupThread_start(re_init_db)

        if(use_ssl):
            app.run(port=8080, debug=False, ssl_context=(crypto_handler.sslkeys_loc+"cert.pem",crypto_handler.sslkeys_loc+"privkey.pem"), threaded=True)
        else:
            #debug=true will auto deploy code changes (note: will initialize the application twice)
            app.run(port=8080, debug=False, threaded=True)
    except Exception as e:
        log.mal2_rest_log.exception("run application error")
    finally:
        close_and_cleanup()

    log.mal2_rest_log.info('Finished MAL2 rest-api')


if __name__ == '__main__':
    Args = argparse.ArgumentParser(description="rest-api server for mal2-eCommerce Fake-Shop detection plugin")
    Args.add_argument("--re-init-db", default=False, action="store_true", dest='reinit_db', help="Set flag if you want to start fresh i.e. re-init the db schema + re-import csv data")
    Args.add_argument("--use-ssl", default=False, action="store_true", dest='use_ssl', help="Set flag if you want to enable self-signed ssl")
    args = Args.parse_args()

    #to start with fresh db call 'python -m swagger_server --re-init-db'
    start_app(args.reinit_db, args.use_ssl)