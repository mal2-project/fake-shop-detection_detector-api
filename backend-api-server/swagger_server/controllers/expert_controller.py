import connexion
import six

#swagger web modules
from swagger_server.models.inline_response400 import InlineResponse400  # noqa: E501
from swagger_server.models.site import Site  # noqa: E501
from swagger_server.models.site_analysis_result import SiteAnalysisResult  # noqa: E501
from swagger_server import util
from datetime import datetime 
#mal2 custom mmodules
import swagger_server.mal2.verify.verify_site as mal2_verify
import swagger_server.mal2.db.handler.db_handler as db
import swagger_server.mal2.db.model.db_model as db_model
from swagger_server import logger_config as log
import swagger_server.mal2.controller.mal2_default_controler as mal2_controller
from flask import Response


def reanalyze_post(site):  # noqa: E501
    """request Fake-Score re-analysis of a given site

    returns the Fake-Score Re-Analysis through the mal2_ai if the site is not a Whitelist/Blacklist entry # noqa: E501

    :param site: site and parameter configuration on which to run analysis on
    :type site: dict | bytes

    :rtype: SiteAnalysisResult
    """

    #init empty return object
    ret = SiteAnalysisResult()

    if connexion.request.is_json:
        #params passed in JSON structure
        try:
            site = Site.from_dict(connexion.request.get_json())  # noqa: E501
        except ValueError as e:
            log.mal2_rest_log.info("analyse_post invalid parameter request: "+str(e))
            res_body ='{"detail": "'+str(e)+'","status": 400, "title": "Bad Request","type": "about:blank"}'
            return Response(res_body,status=400,)
        finally:
            #remove db session (and auto-create new Session)
            log.mal2_rest_log.debug("removing db session %s",db.Session)
            db.Session.remove()

        log.mal2_rest_log.info("analyse_post for: site_base_url: "+site.site_base_url+" clientID: "+site.client_id+" re_process: "+str(site.re_process))
        #forward to mal2_controller
        try:
            ret = mal2_controller.analyze_post(site)
        except Exception as e:
            log.mal2_rest_log.exception("analyse_post exception: "+str(e))
            res_body ='{"detail": "'+str(e)+'","status": 400, "title": "server error","type": "about:blank"}'
            return Response(res_body,status=400,)
        finally:
            #remove db session (and auto-create new Session)
            log.mal2_rest_log.debug("removing db session %s",db.Session)
            db.Session.remove()
        
    log.mal2_rest_log.info("returning reanalyse_post results: %s",ret)
    return ret
