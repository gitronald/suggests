""" Recursively retrieve autocomplete suggestions from Google and Bing.
"""

import time
import json
import urllib
import requests
from numpy import random
from datetime import datetime, timezone
from typing import Optional, List, Dict, Union, Any

from . import parsing
from . import logger
log = logger.Logger().start()

def sleep_random(x: float = 0.7, y: float = 1.4) -> None:
    """Sleep a random time with noise between x and y seconds
    
    Args:
        x (float): Minimum sleep time in seconds
        y (float): Maximum sleep time in seconds
    """
    time.sleep(random.uniform(x,y))
    
def prepare_qry(qry: str) -> str:
    """Prepare query string for URL encoding
    
    Args:
        qry (str): Raw query string
    
    Returns:
        str: URL encoded query string
    """
    return urllib.parse.quote_plus(qry)

def get_google_url() -> str:
    """Get Google autocomplete API URL
    
    Returns:
        str: Base Google autocomplete API URL
    """
    return 'https://www.google.com/complete/search?sclient=psy-ab&hl=en&q='

def get_bing_url(cvid: str = '&cvid=CF23583902D944F1874B7D9E36F452CD') -> str:
    """Get Bing autocomplete API URL
    
    Args:
        cvid (str): Bing API client ID
    
    Returns:
        str: Base Bing autocomplete API URL
    """
    return f'http://www.bing.com/AS/Suggestions?&mkt=en-us{cvid}&q='

def requester(
    qry: str,
    source: str = 'bing',
    sesh: Optional[requests.Session] = None,
    sleep: Optional[float] = None,
    allow_zip: bool = False
) -> Optional[Union[dict, str]]:
    """Requester with logging and specified user agent
    
    Args:
        qry (str): Search query to submit
        source (str): Search engine to submit query to, either "bing" or "google"
        sesh (Optional[requests.Session]): Pass a custom requests session
        sleep (Optional[float]): Custom sleep duration
        allow_zip (bool): Enable response content unzipping
    
    Returns:
        Optional[Union[dict, str]]: JSON response for Google, HTML string for Bing, None on error
    
    Raises:
        AssertionError: If source is not 'bing' or 'google'
    """
    assert source in ['bing','google'], "Must select bing or google as source"

    sesh = sesh if sesh else requests.Session()

    base = get_bing_url() if source == 'bing' else get_google_url() 
    url = base + prepare_qry(qry)

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
        return None

def get_suggests(
    qry: str,
    source: str = 'bing',
    sesh: Optional[requests.Session] = None,
    sleep: Optional[float] = None
) -> Dict[str, Any]:
    """Scrape and parse search engine suggestion data for a query.
    
    Args:
        qry (str): Query to obtain suggestions for
        source (str): The search engine to submit the query to
        sesh (Optional[requests.Session]): Session for maintaining connection
        sleep (Optional[float]): Custom sleep duration
    
    Returns:
        Dict[str, Any]: Dictionary containing query metadata and suggestions
    """
    sesh = sesh if sesh else requests.Session()
    
    tree: Dict[str, Any] = {
        'qry': qry,
        'datetime': str(datetime.now(timezone.utc).replace(tzinfo=None)),
        'source': source,
        'data': requester(qry, source, sesh, sleep)
    }
    
    parser = parsing.parse_bing if source == 'bing' else parsing.parse_google
    parsed = parser(tree['data'], qry)
    tree.update(parsed)
    return tree

def get_suggests_tree(
    root: str,
    source: str = 'bing',
    max_depth: int = 3,
    save_to: str = '',
    sesh: Optional[requests.Session] = None,
    crawl_id: Optional[str] = None,
    sleep: Optional[float] = None
) -> List[Dict[str, Any]]:
    """Retrieve autocomplete suggestions tree for a root query
    
    Args:
        root (str): Query to obtain a suggestion tree for
        source (str): The search engine to submit the query to
        max_depth (int): Maximum breadth first steps from root
        save_to (str): Optional filepath to append results as json lines
        sesh (Optional[requests.Session]): Session for maintaining connection
        crawl_id (Optional[str]): Unique identifier for the crawl session
        sleep (Optional[float]): Custom sleep duration
    
    Returns:
        List[Dict[str, Any]]: List of suggestion trees with metadata
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

    tree: List[Dict[str, Any]] = [root_branch]
    all_suggests: set = {root}

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
                        
    if save_to:
        outfile.close()
    return tree