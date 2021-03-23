from url_normalize import url_normalize
from w3lib.url import url_query_cleaner
from urllib.parse import urlparse

def extract_base_url(url):
    """validity of http url is checked by swagger - extracts the netloc from the url, removes trailing path or www
    and returns the baseurl e.g. google.at

    """
    #validity of url is checked by swagger
    url = url_normalize(url)
    #removes http https etc
    url = urlparse(url).netloc
    #but not query params
    url = url.replace("www.","")
    if url.endswith('/'):
        url = url[:-1]
    return url