import datetime as dt
import time
import requests
import json
import time
from swagger_server import logger_config as log


def submit_to_wayback_machine(url):
    """submit a site to the internet wayback archive

    Arguments:
        url {Str} -- url to submit to internet arvhive for archiving snapshot
    """
    request_url = "https://web.archive.org/save/"+url
    headers = {'content-type': 'application/json'}
    
    log.mal2_rest_log.info("submitting %s to wayback-machine %s",url, request_url)
    resp =requests.get(request_url,headers=headers,timeout=10)
    
    if resp.status_code == 200:
        log.mal2_rest_log.info("waybackmachine - successfully submitted site %s to the internet archive",url)
    else:
        log.mal2_rest_log.warn("waybackmachine - error - satus code: %s message: %s",resp.status_code,resp.text)

def get_entry_from_wayback_machine(url,retry=3):
    """queries the internet wayback arhive on the latest snapshot

    Arguments:
        url {Str} -- url to request archived snapshot for e.g. google.at

    Keyword Arguments:
        retry {int} -- number of retries (default: {3})

    Returns:
        archive_date {Str} -- archive creation date - formatted for output %d.%m.%Y %H:%M
        archive_url {Str} -- link to waybackmachine

    """
    ret_arch_time = None
    ret_arch_url = None
    request_url = "https://archive.org/wayback/available?url="+url
    headers = {'content-type': 'application/json'}
    log.mal2_rest_log.info("waybackmachine - getting internet archive for %s from wayback-machine %s",url, request_url)
    #Note: API is only able to deliver latest (closest) snapshot
    
    #try three times - just in case we previously asked to create archive
    counter = 0
    while ret_arch_url == None and counter < retry:
        #send request
        resp =requests.get(request_url,headers=headers,timeout=10)
        #check on status code
        if resp.status_code == 200:
            resp_dict= resp.json()
            #print(resp_dict)
            if resp_dict['archived_snapshots']:
                timestamp = resp_dict['archived_snapshots']['closest']['timestamp']
                ret_arch_time = dt.datetime.strptime(timestamp,'%Y%m%d%H%M%S')
                ret_arch_time = dt.datetime.strftime(ret_arch_time,"%d.%m.%Y %H:%M")
                ret_arch_url = resp_dict['archived_snapshots']['closest']['url']
                log.mal2_rest_log.info("waybackmachine - received webarchive entry. archived: %s url: %s",ret_arch_time,ret_arch_url)
                return ret_arch_time, ret_arch_url
            else:
                log.mal2_rest_log.info("waybackmachine - no archive available at wayback-machine")
        else:
            log.mal2_rest_log.warn("waybackmachine - error - satus code: %s message: %s",resp.status_code,resp.text)
        counter += 1
        #sleep for 3 seconds
        time.sleep(3)
    return ret_arch_time, ret_arch_url