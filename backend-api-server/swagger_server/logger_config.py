import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import os
from datetime import datetime, date, timedelta
import fnmatch

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s - %(funcName)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger_dir = os.getcwd()+os.path.sep+"logs"+os.path.sep


def setup_logger(name, level=logging.INFO):
    """To setup more than one logger with different output files"""
    #handler = logging.FileHandler(logger_dir+'{:%Y-%m-%d}_{}.log'.format(datetime.now(),name), 'a')   
    handler = TimedRotatingFileHandler(logger_dir+'{}.log'.format(name),when='midnight',interval=1)
    handler.suffix = "%Y-%m-%d" # or anything else that strftime will allow    
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

def get_root_logger():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    #on console output
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.ERROR)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)
    #persist as log file
    #file_handler = logging.FileHandler(logger_dir+'{:%Y-%m-%d}_mal2-all-log.log'.format(datetime.now()), 'a') 
    file_handler = TimedRotatingFileHandler(logger_dir+'mal2-all-log.log',when='midnight',interval=1)       
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

def init():
    if not os.path.exists(logger_dir):
        #create log output dir
        print("creating log output dir: {}".format(logger_dir))
        os.mkdir(logger_dir)

    get_root_logger()
    setup_logger('mal2-model-log', level=logging.INFO)
    setup_logger('mal2-rest-log', level=logging.INFO)
    setup_logger('mal2-fakeshopdb-log', level=logging.INFO) #logger for fake-shop db and all other datasources


def check_and_throw_away_logs():
    def get_key_name(timestamp:date)->str:
        """[returns '%Y-%m-%d' from date which is used as key_name for that day
        Args:
            timestamp (date): [any given date]
        """
        return timestamp.strftime('%Y-%m-%d')

    print("checking logfile cleanup jobs. current date: {}".format(get_key_name(datetime.now() - timedelta(days=0))))
    #check for log files dating back 14-365 days from now 
    for i in range(14, 365):
        #log files: keys contain a pattern as e.g. 2020-09-26
        key_name = get_key_name(datetime.now() - timedelta(days=i))
        #search for keys and delete
        for filename in os.listdir(logger_dir):
            if fnmatch.fnmatch(filename, "*"+key_name):
                os.remove(logger_dir+filename)
                print("logfile cleanup job deleted file: {}".format(logger_dir+filename))


#all available loggers
mal2_model_log = logging.getLogger('mal2-model-log')
mal2_rest_log = logging.getLogger('mal2-rest-log')
mal2_fakeshop_db_log = logging.getLogger('mal2-fakeshopdb-log')