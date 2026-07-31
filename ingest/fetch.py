"""Fetchers for every source, each returning raw dicts.

Design rule: a source that fails must not take the run down with it. Every
fetcher returns (rows, error) and the orchestrator records partial failure in
the run manifest rather than aborting. A job board going dark is routine.
"""
from __future__ import annotations

import json
import re
import ssl
import time
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


def get_json(url: str, timeout: int = TIMEOUT, retries: int = 3):
    """Return (data, error). Never raises.

    Retries on 429 and 5xx with backoff. Workable in particular rate-limits
    concurrent callers, and losing a 500-posting board to one 429 is the
    difference between covering an employer and not.
    """
    delay = 1.5
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read()), None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                wait = float(e.headers.get("Retry-After") or 0) or delay
                time.sleep(min(wait, 20))
                delay *= 2
                continue
            return None, f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return None, f"{type(e).__name__}: {str(e)[:60]}"
    return None, "retries exhausted"


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


def smartrecruiters(slug: str):
    """SmartRecruiters paginates; totalFound is often several times the page size."""
    out, offset = [], 0
    while offset < 400:
        url = (f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
               f"?limit=100&offset={offset}")
        d, err = get_json(url)
        if err:
            return (out, None) if out else ([], err)
        rows = (d or {}).get("content", [])
        if not rows:
            break
        for j in rows:
            loc = j.get("location") or {}
            city = ", ".join(x for x in (loc.get("city"), loc.get("country")) if x)
            out.append({
                "source": "smartrecruiters",
                "company": slug,
                "title": j.get("name", ""),
                "url": (j.get("ref") or "").replace("api.smartrecruiters.com/v1/companies",
                                                    "jobs.smartrecruiters.com")
                       or f"https://jobs.smartrecruiters.com/{slug}/{j.get('id','')}",
                "location": city or ("Remote" if loc.get("remote") else ""),
                "posted_at": str(j.get("releasedDate", ""))[:10],
                "text": " ".join(filter(None, [
                    j.get("name", ""),
                    (j.get("department") or {}).get("label", ""),
                    (j.get("function") or {}).get("label", ""),
                    (j.get("industry") or {}).get("label", ""),
                    (j.get("experienceLevel") or {}).get("label", ""),
                ])),
                "external_id": str(j.get("id", "")),
            })
        if len(rows) < 100:
            break
        offset += 100
    return out, None


def recruitee(slug: str):
    d, err = get_json(f"https://{slug}.recruitee.com/api/offers/")
    if err:
        return [], err
    out = []
    for j in (d or {}).get("offers", []):
        out.append({
            "source": "recruitee",
            "company": slug,
            "title": j.get("title", ""),
            "url": j.get("careers_url", "") or j.get("url", ""),
            "location": ", ".join(filter(None, [j.get("city"), j.get("country")])) or "",
            "posted_at": str(j.get("published_at", ""))[:10],
            "text": strip_html(j.get("description"))[:6000],
            "external_id": str(j.get("id", "")),
        })
    return out, None


def workable(slug: str):
    d, err = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    if err:
        return [], err
    out = []
    for j in (d or {}).get("jobs", []):
        out.append({
            "source": "workable",
            "company": slug,
            "title": j.get("title", ""),
            "url": j.get("url", "") or j.get("shortlink", ""),
            "location": ", ".join(filter(None, [j.get("city"), j.get("country")])) or "",
            "posted_at": str(j.get("published_on", ""))[:10],
            "text": strip_html(j.get("description"))[:6000],
            "external_id": str(j.get("shortcode", "")),
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

ATS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby,
       "smartrecruiters": smartrecruiters, "recruitee": recruitee,
       "workable": workable}
