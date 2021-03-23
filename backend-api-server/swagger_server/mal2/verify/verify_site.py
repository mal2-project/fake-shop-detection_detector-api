import os, shutil
import verify as mal2_model_verify
import pkg_resources
from swagger_server import logger_config as log
import swagger_server.mal2.common.common_utils as utils
import checksumdir

#Note: mal2-model
# checkout https://mal2git.x-t.at/root/mal2/tree/master/eCommerce
# - install package via pip install .
# - uninstall package via pip uninstall mal2-fakeshop-models -y

def get_model_prediction(site:str,model="xgboost",keep_cache=False,use_cache=False):
    """verifies a given site url against the mal2-model component

    Arguments:
        site {Str} -- url without protocol prefix e.g. google.at

    Returns:
        prediction {Float}, hash {Str}, model_name {Str}, model_version {Str} -- Returns the models prediction [0..1], a hash of the downloaded html artefacts, model_name, model_version
    """

    supported_models = ["xgboost", "random_forest", "neural_net"]
    # validate selected model input
    if model not in supported_models:
        raise ValueError("non-supported model selected")

    #load the resources from the package 
    MODEL = model
    MODEL_PATH = pkg_resources.resource_filename('verify', 'files/'+MODEL+'.model')
    DICT_PATH = pkg_resources.resource_filename('verify', 'files/vectorizers.dict')
    VERSION = pkg_resources.get_distribution("mal2-fakeshop-models").version
    prediction = None
    dirhash = None

    #that's created by the mal2-model (downloaded html artefacts via scrapy)
    verify_output_dir = os.path.abspath(os.getcwd()+"/data/verify_sites/"+site+"/".replace("/",os.path.sep))

    if use_cache == False:
        utils.nukedir_recursively(verify_output_dir)
    
    #call mal2-model verify 
    try:
        #call the mal2_model
        score, verified, explanation = mal2_model_verify.main(MODEL_PATH,DICT_PATH,site,check_db=False, use_cache=use_cache, do_feature_importance=False, do_scrape_images=False)
        if score != None:
            prediction = score[0]
            log.mal2_model_log.info("mal2-model verify result site: %s model: %s risk-score: %s verified: %s explanation: %s",site, model, prediction,verified,explanation)
        
            #store the hash of html artefacts
            dirhash = checksumdir.dirhash(verify_output_dir)
            log.mal2_model_log.info("hash of html scrapy download %s",dirhash)
        else:
            log.mal2_model_log.info("issues getting prediction from model %s for %s",model, site)
            #exception forwarded to ui
            raise Exception("failed to get prediction") 
    except Exception as err:
        log.mal2_model_log.exception("error calling verify_site for %s with "+str(err),site)
        #exception forwarded to ui
        raise Exception("failed to get prediction") 

    finally:
        if keep_cache == False:
            utils.nukedir_recursively(verify_output_dir)

    return prediction, dirhash, MODEL, VERSION