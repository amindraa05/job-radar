"""Fetchers for every source, each returning raw dicts.

Design rule: a source that fails must not take the run down with it. Every
fetcher returns (rows, error) and the orchestrator records partial failure in
the run manifest rather than aborting. A job board going dark is routine.
"""
from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from html import unescape

ssl._create_default_https_context = ssl._create_unverified_context

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json",
}
TIMEOUT = 30

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def strip_html(s: str | None) -> str:
    if not s:
        return ""
    return _WS.sub(" ", unescape(_TAG.sub(" ", s))).strip()


def get_json(url: str, timeout: int = TIMEOUT):
    """Return (data, error). Never raises."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {str(e)[:60]}"


# --------------------------------------------------------------------------
# Applicant tracking systems, per company board
# --------------------------------------------------------------------------

def greenhouse(slug: str):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    d, err = get_json(url)
    if err:
        return [], err
    out = []
    for j in (d or {}).get("jobs", []):
        out.append({
            "source": "greenhouse",
            "company": slug,
            "title": j.get("title", ""),
            "url": j.get("absolute_url", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "posted_at": j.get("updated_at") or j.get("first_published", ""),
            "text": strip_html(j.get("content"))[:6000],
            "external_id": str(j.get("id", "")),
        })
    return out, None


def lever(slug: str):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    d, err = get_json(url)
    if err:
        return [], err
    out = []
    for j in d or []:
        cat = j.get("categories") or {}
        out.append({
            "source": "lever",
            "company": slug,
            "title": j.get("text", ""),
            "url": j.get("hostedUrl", ""),
            "location": cat.get("location", "") or "",
            "posted_at": j.get("createdAt", ""),
            "text": strip_html(j.get("descriptionPlain") or j.get("description"))[:6000],
            "external_id": str(j.get("id", "")),
        })
    return out, None


def ashby(slug: str):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    d, err = get_json(url)
    if err:
        return [], err
    out = []
    for j in (d or {}).get("jobs", []):
        out.append({
            "source": "ashby",
            "company": slug,
            "title": j.get("title", ""),
            "url": j.get("jobUrl", "") or j.get("applyUrl", ""),
            "location": j.get("location", "") or "",
            "posted_at": j.get("publishedAt", ""),
            "text": strip_html(j.get("descriptionPlain") or j.get("descriptionHtml"))[:6000],
            "external_id": str(j.get("id", "")),
        })
    return out, None


# --------------------------------------------------------------------------
# Remote-first aggregators
# --------------------------------------------------------------------------

def remotive():
    d, err = get_json("https://remotive.com/api/remote-jobs")
    if err:
        return [], err
    out = []
    for j in (d or {}).get("jobs", []):
        out.append({
            "source": "remotive",
            "company": j.get("company_name", ""),
            "title": j.get("title", ""),
            "url": j.get("url", ""),
            "location": j.get("candidate_required_location", "") or "Remote",
            "posted_at": j.get("publication_date", ""),
            "text": strip_html(j.get("description"))[:6000],
            "external_id": str(j.get("id", "")),
        })
    return out, None


def remoteok():
    d, err = get_json("https://remoteok.com/api")
    if err:
        return [], err
    out = []
    for j in d or []:
        if not isinstance(j, dict) or not j.get("position"):
            continue          # first element is a legal notice, not a job
        out.append({
            "source": "remoteok",
            "company": j.get("company", ""),
            "title": j.get("position", ""),
            "url": j.get("url", ""),
            "location": j.get("location", "") or "Remote",
            "posted_at": str(j.get("date", "") or ""),
            "text": strip_html(j.get("description"))[:6000] + " " + " ".join(j.get("tags") or []),
            "external_id": str(j.get("id", "")),
        })
    return out, None


def arbeitnow():
    out, err_all = [], None
    for page in (1, 2, 3):
        d, err = get_json(f"https://www.arbeitnow.com/api/job-board-api?page={page}")
        if err:
            err_all = err
            break
        rows = (d or {}).get("data", [])
        if not rows:
            break
        for j in rows:
            out.append({
                "source": "arbeitnow",
                "company": j.get("company_name", ""),
                "title": j.get("title", ""),
                "url": j.get("url", ""),
                "location": j.get("location", "") or ("Remote" if j.get("remote") else ""),
                "posted_at": str(j.get("created_at", "")),
                "text": strip_html(j.get("description"))[:6000] + " " + " ".join(j.get("tags") or []),
                "external_id": str(j.get("slug", "")),
            })
    return out, err_all


def himalayas():
    out, err_all = [], None
    for offset in (0, 100, 200):
        d, err = get_json(f"https://himalayas.app/jobs/api?limit=100&offset={offset}")
        if err:
            err_all = err
            break
        rows = (d or {}).get("jobs", [])
        if not rows:
            break
        for j in rows:
            locs = j.get("locationRestrictions") or []
            out.append({
                "source": "himalayas",
                "company": j.get("companyName", ""),
                "title": j.get("title", ""),
                "url": j.get("applicationLink", "") or j.get("guid", ""),
                "location": ", ".join(locs) if locs else "Remote",
                "posted_at": str(j.get("pubDate", "")),
                "text": strip_html(j.get("description"))[:6000],
                "external_id": str(j.get("guid", "")),
            })
    return out, err_all


AGGREGATORS = {
    "remotive": remotive,
    "remoteok": remoteok,
    "arbeitnow": arbeitnow,
    "himalayas": himalayas,
}

ATS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby}
