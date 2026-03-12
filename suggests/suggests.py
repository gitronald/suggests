"""Recursively retrieve autocomplete suggestions from Google and Bing."""

from __future__ import annotations

import json
import time
import urllib
from datetime import datetime, timezone
from typing import Any

import requests
from numpy import random

from . import logger, parsing

log = logger.Logger().start()


def sleep_random(x: float = 0.7, y: float = 1.4) -> None:
    """Sleep a random time with noise between x and y seconds.

    Args:
        x: Minimum sleep time in seconds
        y: Maximum sleep time in seconds
    """
    time.sleep(random.uniform(x, y))


def prepare_qry(qry: str) -> str:
    """Prepare query string for URL encoding.

    Args:
        qry: Raw query string

    Returns:
        URL encoded query string
    """
    return urllib.parse.quote_plus(qry)


def get_google_url(hl: str = "en", sclient: str = "psy-ab") -> str:
    """Get Google autocomplete API URL.

    Args:
        hl: Language code (e.g. 'en', 'de', 'fr')
        sclient: Google search client identifier

    Returns:
        Base Google autocomplete API URL
    """
    params = urllib.parse.urlencode({"sclient": sclient, "hl": hl, "q": ""})
    return f"https://www.google.com/complete/search?{params}"


def get_bing_url(
    mkt: str = "en-us", cvid: str = "CF23583902D944F1874B7D9E36F452CD"
) -> str:
    """Get Bing autocomplete API URL.

    Args:
        mkt: Market code (e.g. 'en-us', 'de-de', 'es-es')
        cvid: Bing API client ID

    Returns:
        Base Bing autocomplete API URL
    """
    params = urllib.parse.urlencode({"mkt": mkt, "cvid": cvid, "q": ""})
    return f"http://www.bing.com/AS/Suggestions?{params}"


def requester(
    qry: str,
    source: str = "bing",
    sesh: requests.Session | None = None,
    sleep: float | None = None,
    allow_zip: bool = False,
    hl: str | None = None,
    mkt: str | None = None,
) -> dict | str | None:
    """Requester with logging and specified user agent

    Args:
        qry: Search query to submit
        source: Search engine to submit query to, either "bing" or "google"
        sesh: Pass a custom requests session
        sleep: Custom sleep duration
        allow_zip: Enable response content unzipping
        hl: Google language code (e.g. 'en', 'de', 'fr')
        mkt: Bing market code (e.g. 'en-us', 'de-de', 'es-es')

    Returns:
        JSON response for Google, HTML string for Bing, None on error

    Raises:
        AssertionError: If source is not 'bing' or 'google'
    """
    assert source in ["bing", "google"], "Must select bing or google as source"

    sesh = sesh if sesh else requests.Session()

    if source == "bing":
        base = get_bing_url(mkt or "en-us")
    else:
        base = get_google_url(hl or "en")
    url = base + prepare_qry(qry)

    time.sleep(sleep) if sleep else sleep_random()
    log.info("%s | %s", "%s" % source, qry)
    try:
        response = sesh.get(url, timeout=10)
        if source == "google":
            return json.loads(response.text)
        elif source == "bing":
            return response.text
    except Exception:
        log.exception("ERROR SCRAPING: request[%s]", response.status_code)
        return None


def get_suggests(
    qry: str,
    source: str = "bing",
    sesh: requests.Session | None = None,
    sleep: float | None = None,
    sesh_headers: dict[str, str] | None = None,
    hl: str | None = None,
    mkt: str | None = None,
) -> dict[str, Any]:
    """Scrape and parse search engine suggestion data for a query.

    Args:
        qry: Query to obtain suggestions for
        source: The search engine to submit the query to
        sesh: Session for maintaining connection
        sleep: Custom sleep duration
        sesh_headers: Custom session headers
        hl: Google language code (e.g. 'en', 'de', 'fr')
        mkt: Bing market code (e.g. 'en-us', 'de-de', 'es-es')

    Returns:
        Dictionary containing query metadata and suggestions
    """
    sesh = sesh if sesh else requests.Session()
    if sesh_headers:
        sesh.headers.update(sesh_headers)

    tree: dict[str, Any] = {
        "qry": qry,
        "datetime": str(datetime.now(timezone.utc).replace(tzinfo=None)),
        "source": source,
        "data": requester(qry, source, sesh, sleep, hl=hl, mkt=mkt),
    }

    parser = parsing.parse_bing if source == "bing" else parsing.parse_google
    parsed = parser(tree["data"], qry)
    tree.update(parsed)
    return tree


def get_suggests_tree(
    root: str,
    source: str = "bing",
    max_depth: int = 3,
    save_to: str = "",
    sesh: requests.Session | None = None,
    sesh_headers: dict[str, str] | None = None,
    crawl_id: str | None = None,
    sleep: float | None = None,
    hl: str | None = None,
    mkt: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve autocomplete suggestions tree for a root query

    Args:
        root: Query to obtain a suggestion tree for
        source: The search engine to submit the query to
        max_depth: Maximum breadth first steps from root
        save_to: Optional filepath to append results as json lines
        sesh: Session for maintaining connection
        crawl_id: Unique identifier for the crawl session
        sleep: Custom sleep duration
        hl: Google language code (e.g. 'en', 'de', 'fr')
        mkt: Bing market code (e.g. 'en-us', 'de-de', 'es-es')

    Returns:
        List of suggestion trees with metadata
    """
    sesh = sesh if sesh else requests.Session()
    if sesh_headers:
        sesh.headers.update(sesh_headers)

    depth = 0
    root_branch = get_suggests(root, source, sesh, sleep, hl=hl, mkt=mkt)
    root_branch["depth"] = depth
    root_branch["root"] = root
    root_branch["crawl_id"] = crawl_id

    if save_to:
        outfile = open(save_to, "a+")
        outdata = json.dumps(root_branch)
        outfile.write(f"{outdata}\n")

    tree: list[dict[str, Any]] = [root_branch]
    all_suggests: set[str] = {root}

    while depth < max_depth:
        suggests = {d["qry"]: d["suggests"] for d in tree if d["depth"] == depth}
        depth += 1

        for qry, suggest_list in suggests.items():
            if suggest_list:
                for s in suggest_list:
                    if s not in all_suggests:  # Don't crawl self-loops or duplicates
                        branches = get_suggests(s, source, sesh, sleep, hl=hl, mkt=mkt)
                        branches["depth"] = depth
                        branches["root"] = root
                        branches["crawl_id"] = crawl_id
                        if save_to:
                            outfile.write(f"{json.dumps(branches)}\n")
                        tree.append(branches)
                        all_suggests.add(s)

    if save_to:
        outfile.close()
    return tree
