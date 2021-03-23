import connexion
import six

#swagger web modules
from swagger_server.models.black_list_entry import BlackListEntry  # noqa: E501
from swagger_server.models.grey_list_entry import GreyListEntry  # noqa: E501
from swagger_server.models.ignore_list_entry import IgnoreListEntry  # noqa: E501
from swagger_server.models.inline_response400 import InlineResponse400  # noqa: E501
from swagger_server.models.site import Site  # noqa: E501
from swagger_server.models.site_analysis_result import SiteAnalysisResult  # noqa: E501
from swagger_server.models.white_list_entry import WhiteListEntry  # noqa: E501
from swagger_server import util
from datetime import datetime 
#mal2 custom mmodules
import swagger_server.mal2.verify.verify_site as mal2_verify
import swagger_server.mal2.db.handler.db_handler as db
import swagger_server.mal2.db.model.db_model as db_model
from swagger_server import logger_config as log
import swagger_server.mal2.controller.mal2_default_controler as mal2_controller
from flask import Response


def analyze_post(body):  # noqa: E501
    """request Fake-Score analysis result of a given site

    returns the Fake-Score Analysis of a given site, either mal2_ai prediction or Whitelist/Blacklist entry # noqa: E501

    :param body: site and parameter configuration on which to run analysis on
    :type body: dict | bytes

    :rtype: SiteAnalysisResult
    """

    #init empty return object
    ret = SiteAnalysisResult()

    if connexion.request.is_json:
        #params passed in JSON structure
        try:
            body = Site.from_dict(connexion.request.get_json())
        except ValueError as e:
            log.mal2_rest_log.info("analyse_post invalid parameter request: "+str(e))
            res_body ='{"detail": "'+str(e)+'","status": 400, "title": "Bad Request","type": "about:blank"}'
            return Response(res_body,status=400,)
        finally:
            #remove db session (and auto-create new Session)
            log.mal2_rest_log.debug("removing db session %s",db.Session)
            db.Session.remove()

        #for re-analysis use expert_controller REST endpoint
        body.re_process=False

        log.mal2_rest_log.info("analyse_post for: site_base_url: "+body.site_base_url+" clientID: "+body.client_id+" re_process: "+str(body.re_process))
        #forward to mal2_controller
        try:
            ret = mal2_controller.analyze_post(body)
        except Exception as e:
            log.mal2_rest_log.exception("analyse_post exception: "+str(e))
            res_body ='{"detail": "'+str(e)+'","status": 400, "title": "analyze error","type": "about:blank"}'
            return Response(res_body,status=400,)
        finally:
            #remove db session (and auto-create new Session)
            log.mal2_rest_log.debug("removing db session %s",db.Session)
            db.Session.remove()
        
    log.mal2_rest_log.info("returning analyse_post results: %s",ret)
    return ret

def blacklist_get(limit=None, offset=None, all=None, client_id=None):  # noqa: E501
    """returns all blacklisted shops

    Returns a list of all blacklisted and confirmed fake-shops # noqa: E501

    :param limit: Limits the number of items returned per page. 
    :type limit: int
    :param offset: Specifies the page offset starting at page zero
    :type offset: int
    :param all: reuturns all known items in one request - if true limit and offset parameters are ignored
    :type all: bool
    :param client_id: client ID for debugging purposes on server
    :type client_id: str

    :rtype: List[BlackListEntry]
    """
    #init empty return object
    ret = []
    
    try:
        ret = mal2_controller.blacklist_get(limit,offset,all,client_id)
    except Exception as e:
        log.mal2_rest_log.exception("blacklist_get exception: "+str(e))
        res_body ='{"detail": "'+str(e)+'","status": 400, "title": "server error","type": "about:blank"}'
        return Response(res_body,status=400,)
    finally:
        #remove db session (and auto-create new Session)
        log.mal2_rest_log.debug("removing db session %s",db.Session)
        db.Session.remove()
    return ret


def blacklist_site_id_get(site_id, client_id=None):  # noqa: E501
    """returns information on a specific blacklisted site

    Returns information on a specific blacklist site # noqa: E501

    :param site_id: requested site_id as returned by /analyze
    :type site_id: str
    :param client_id: client ID for debugging purposes on server
    :type client_id: str

    :rtype: BlackListEntry
    """
    #init empty return object
    ret = BlackListEntry()
    try:
        ret = mal2_controller.blacklist_site_id_get(site_id, client_id)
    except Exception as e:
        log.mal2_rest_log.exception("blacklist_site_id_get exception: "+str(e))
        res_body ='{"detail": "'+str(e)+'","status": 400, "title": "server error","type": "about:blank"}'
        return Response(res_body,status=400,)
    finally:
        #remove db session (and auto-create new Session)
        log.mal2_rest_log.debug("removing db session %s",db.Session)
        db.Session.remove()
    return ret


def greylist_get(limit=None, offset=None, all=None, client_id=None):  # noqa: E501
    """returns all greylisted shops

    Returns a list of all greylisted fake-shops # noqa: E501

    :param limit: Limits the number of items returned per page. 
    :type limit: int
    :param offset: Specifies the page offset starting at page zero
    :type offset: int
    :param all: returns all known items in one request - if true limit and offset parameters are ignored
    :type all: bool
    :param client_id: client ID for debugging purposes on server
    :type client_id: str

    :rtype: List[GreyListEntry]
    """
    #init empty return object
    ret = []
    
    try:
        ret = mal2_controller.greylist_get(limit,offset,all,client_id)
    except Exception as e:
        log.mal2_rest_log.exception("greylist_get exception: "+str(e))
        res_body ='{"detail": "'+str(e)+'","status": 400, "title": "server error","type": "about:blank"}'
        return Response(res_body,status=400,)
    finally:
        #remove db session (and auto-create new Session)
        log.mal2_rest_log.debug("removing db session %s",db.Session)
        db.Session.remove()
    return ret


def greylist_site_id_get(site_id, client_id=None):  # noqa: E501
    """returns information on a specific greylisted site

    Returns information on a specific greylist site # noqa: E501

    :param site_id: requested site_id as returned by /analyze
    :type site_id: str
    :param client_id: client ID for debugging purposes on server
    :type client_id: str

    :rtype: GreyListEntry
    """
    #init empty return object
    ret = GreyListEntry()
    try:
        ret = mal2_controller.greylist_site_id_get(site_id, client_id)
    except Exception as e:
        log.mal2_rest_log.exception("greylist_site_id_get exception: "+str(e))
        res_body ='{"detail": "'+str(e)+'","status": 400, "title": "server error","type": "about:blank"}'
        return Response(res_body,status=400,)
    finally:
        #remove db session (and auto-create new Session)
        log.mal2_rest_log.debug("removing db session %s",db.Session)
        db.Session.remove()
    return ret


def ignorelist_get(limit=None, offset=None, all=None, client_id=None):  # noqa: E501
    """returns all ignorelisted shops

    Returns a list of all websites on the ignorelist on which the MAL2 Plugin won&#x27;t operated upon as they are no online shops such as news outlets as orf.at or falter.at # noqa: E501

    :param limit: Limits the number of items returned per page. 
    :type limit: int
    :param offset: Specifies the page offset starting at page zero
    :type offset: int
    :param all: reuturns all known items in one request - if true limit and offset parameters are ignored
    :type all: bool
    :param client_id: client ID for debugging purposes on server
    :type client_id: str

    :rtype: List[IgnoreListEntry]
    """
    #init empty return object
    ret = []
    
    try:
        ret = mal2_controller.ignorelist_get(limit,offset,all,client_id)
    except Exception as e:
        log.mal2_rest_log.exception("ignorelist_get exception: "+str(e))
        res_body ='{"detail": "'+str(e)+'","status": 400, "title": "server error","type": "about:blank"}'
        return Response(res_body,status=400,)
    finally:
        #remove db session (and auto-create new Session)
        log.mal2_rest_log.debug("removing db session %s",db.Session)
        db.Session.remove()
    return ret


def ignorelist_site_id_get(site_id, client_id=None):  # noqa: E501
    """returns information on a specific ignorelisted site

    Returns information on a specific website on which the MAL2 plugin won&#x27;t operated upon as it is not a online shop, e.g. such as news sites as orf.at, falter.at, etc. # noqa: E501

    :param site_id: requested site_id as returned by /analyze
    :type site_id: str
    :param client_id: client ID for debugging purposes on server
    :type client_id: str

    :rtype: IgnoreListEntry
    """
    #init empty return object
    ret = IgnoreListEntry()
    try:
        ret = mal2_controller.ignorelist_site_id_get(site_id, client_id)
    except Exception as e:
        log.mal2_rest_log.exception("ignorelist_site_id_get exception: "+str(e))
        res_body ='{"detail": "'+str(e)+'","status": 400, "title": "server error","type": "about:blank"}'
        return Response(res_body,status=400,)
    finally:
        #remove db session (and auto-create new Session)
        log.mal2_rest_log.debug("removing db session %s",db.Session)
        db.Session.remove()
    return ret


def whitelist_get(limit=None, offset=None, all=None, client_id=None):  # noqa: E501
    """returns all whitelisted shops

    Returns a list of all whitelisted shops # noqa: E501

    :param limit: Limits the number of items returned per page. 
    :type limit: int
    :param offset: Specifies the page offset starting at page zero
    :type offset: int
    :param all: reuturns all known items in one request - if true limit and offset parameters are ignored
    :type all: bool
    :param client_id: client ID for debugging purposes on server
    :type client_id: str

    :rtype: List[WhiteListEntry]
    """
    #init empty return object
    ret = []
    
    try:
        ret = mal2_controller.whitelist_get(limit,offset,all,client_id)
    except Exception as e:
        log.mal2_rest_log.exception("whitelist_get exception: "+str(e))
        res_body ='{"detail": "'+str(e)+'","status": 400, "title": "server error","type": "about:blank"}'
        return Response(res_body,status=400,)
    finally:
        #remove db session (and auto-create new Session)
        log.mal2_rest_log.debug("removing db session %s",db.Session)
        db.Session.remove()
    return ret


def whitelist_site_id_get(site_id, client_id=None):  # noqa: E501
    """returns information on a specific whitelisted site

    returns information on a specific whitelisted site # noqa: E501

    :param site_id: requested site_id as returned by /analyze
    :type site_id: str
    :param client_id: client ID for debugging purposes on server
    :type client_id: str

    :rtype: WhiteListEntry
    """
    #init empty return object
    ret = WhiteListEntry()
    try:
        ret = mal2_controller.whitelist_site_id_get(site_id, client_id)
    except Exception as e:
        log.mal2_rest_log.exception("whitelist_site_id_get exception: "+str(e))
        res_body ='{"detail": "'+str(e)+'","status": 400, "title": "server error","type": "about:blank"}'
        return Response(res_body,status=400,)
    finally:
        #remove db session (and auto-create new Session)
        log.mal2_rest_log.debug("removing db session %s",db.Session)
        db.Session.remove()
    return ret
