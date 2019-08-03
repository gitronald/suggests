""" Recursively retrieve autocomplete suggestions from Google and Bing.
"""

import time
import json
import urllib
import requests
from numpy import random
from datetime import datetime

from . import parsing
from . import logger
log = logger.Logger().start()

##-----------------------------------------------------------------------------
##  Scraper
##-----------------------------------------------------------------------------

def sleep_random(x=0.7, y=1.4):
    """Sleep a random time with noise between x and y seconds"""
    time.sleep(random.uniform(x,y))
    
def prepare_qry(qry):
    return urllib.parse.quote_plus(qry)

def get_google_url():
    return 'https://www.google.com/complete/search?sclient=psy-ab&hl=en&q='

def get_bing_url(cvid='&cvid=CF23583902D944F1874B7D9E36F452CD'):
    return f'http://www.bing.com/AS/Suggestions?&mkt=en-us{cvid}&q='

def scraper(qry, source='bing', sesh=None, sleep=None, allow_zip=False):
    """Scraper with logging and specified user agent
    
    Parameters
    ----------
    qry : str
        Search query to submit
    source : str
        Search engine to submit query to, either "bing" or "google"
    sesh : str, optional
        Pass a custom requests session
    allow_zip : bool, optional
        Boolean controlling whether to unzip response content before parsing.
        Will not work without enabling zip requests in the headers and passing
        the resulting session. To enable zip requests, you must set a header 
        of 'Accept-Encoding' to 'gzip, deflate, br'. This will lighten the load 
        on the servers you are submitting to.

    Returns
    -------
    request.reponse
        Either an HTML (bing) or a JSON (google) response based on source
    """
    assert source in ['bing','google'], "Must select bing or google as source"

    sesh = sesh if sesh else requests.Session()

    base = get_bing_url() if source == 'bing' else get_google_url() 
    url = base + prepare_qry(qry)

    # Sleep
    time.sleep(sleep) if sleep else sleep_random()
    log.info('%s | %s', '%s' % source, qry)
    try:
        response = sesh.get(url, timeout=10)
        if source == 'google':
            return json.loads(response.content)
        elif source == 'bing':
            return response.content.decode('utf-8')
    except Exception as e:
        log.exception('ERROR SCRAPING: request[%s]', response.status_code)
        pass


##-----------------------------------------------------------------------------
##  Get Suggestions
##-----------------------------------------------------------------------------

def get_suggests(qry, source='bing', sesh=None, sleep=None):
    """ Scrape and parse search engine suggestion data for a query.
    
    Parameters
    ----------
        qry : str
            Query to obtain suggestions for.
            
        source : str
            The search engine to submit the query to.

        sesh : requests.Session()
            Pass session to specify headers or maintain connection while building trees.
    """
    sesh = sesh if sesh else requests.Session()
    
    tree = {}
    tree['qry'] = qry
    tree['datetime'] = str(datetime.utcnow())
    tree['source'] = source
    tree['data'] = scraper(qry, source, sesh, sleep)
    
    # Attempt parsing
    parser = parsing.parse_bing if source == 'bing' else parsing.parse_google
    parsed = parser(tree['data'], qry)
    tree.update(parsed)
    return tree


# Suggestions tree
def get_suggests_tree(root, source='bing', max_depth=3, save_to='', sesh=None,
    crawl_id=None, sleep=None):
    """Retrieve autocomplete suggestions tree for a root query
    
    Parameters
    ----------
        root : str
            Query to obtain a suggestion tree for.
            
        source : str
            The search engine to submit the query to
            
        max_depth : int
            Maximum breadth first steps from root

        save_to : str
            Optional, filepath append results as json lines

        sesh : requests.Session()
            Pass session to specify headers and maintain connection
    """
    sesh = sesh if sesh else requests.Session()

    depth = 0
    root_branch = get_suggests(root, source, sesh, sleep)
    root_branch['depth'] = depth
    root_branch['root'] = root
    root_branch['crawl_id'] = crawl_id

    if save_to:
        outfile = open(save_to, 'a+')
        outdata = json.dumps(root_branch)
        outfile.write(f'{outdata}\n')

    # Initialize list of suggestion dicts for output
    tree = [root_branch]

    # Initialize tracking of all queries seen
    all_suggests = {root}

    # Recurse
    while depth < max_depth:
        suggests = {d['qry']: d['suggests'] for d in tree if d['depth']==depth}
        depth += 1
        
        for qry, suggest_list in suggests.items():
            if suggest_list:
                for s in suggest_list:
                    if s not in all_suggests: # Don't crawl self-loops or duplicates
                        branches = get_suggests(s, source, sesh, sleep)                    
                        branches['depth'] = depth
                        branches['root'] = root
                        branches['crawl_id'] = crawl_id
                        if save_to: 
                            outfile.write(f'{json.dumps(branches)}\n')
                        tree.append(branches)            
                        all_suggests.add(s)
                        
    if save_to: outfile.close()
    return tree
