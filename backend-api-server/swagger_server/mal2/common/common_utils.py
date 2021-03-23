import os, shutil
from swagger_server import logger_config as log

def deletedir_recursive(dir):
    """Delete directory and files recursively but keep the onesthat are still in use

    Arguments:
        dir {Str} -- folder path
    """
    if os.path.exists(dir):
        log.mal2_model_log.info("cleanup of mal2 crawler verify output_dir %s", dir)
        #False raises exception if files are still in use
        shutil.rmtree(dir,ignore_errors=True)

def nukedir_recursively(dir):
    """Force delete of directory and files recursively even if files/folders are still in use

    Arguments:
        dir {Str} -- folder path
    """
    if os.path.exists(dir):
        log.mal2_model_log.info("nuking of mal2 crawler verify output_dir %s", dir)
        if dir[-1] == os.sep: dir = dir[:-1]
        files = os.listdir(dir)
        for file in files:
            if file == '.' or file == '..': continue
            path = dir + os.sep + file
            if os.path.isdir(path):
                nukedir_recursively(path)
            else:
                os.unlink(path)
        os.rmdir(dir)