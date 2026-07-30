"""Discover which ATS job boards actually respond, and how relevant they are.

Curation is data-driven rather than guessed: probe a wide candidate list, keep
what answers, and record how many postings each board carries in the regions we
care about. Output feeds boards.json, which the ingester reads.

Run: python ingest/discover.py
"""
from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "ingest" / "boards.json"

ssl._create_default_https_context = ssl._create_unverified_context
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json",
}

# Candidate slugs. Deliberately over-broad: the probe decides what survives.
GREENHOUSE = """
airbnb airtable anthropic asana benchling betterment bird bolt brex calendly
chainalysis checkr cloudflare cockroachlabs coinbase confluentinc coursera
crowdstrike databricks datadog dbtlabs deliveroo digitalocean discord docker
doordash dropbox duolingo elastic figma fivetran flexport gitlab grafanalabs
hashicorpinc hopin hubspot instacart intercom jane kong lattice launchdarkly
lyft mongodb monzo mural neo4j netlify newrelic nium notion nubank okta
opendoor optiver palantir pagerduty pinterest planetscale plaid postman
quora rapyd reddit redis remitly retool revolut robinhood roblox samsara
scaleai sentry shieldai shopify sigmacomputing snyk sonarsource splunk
sproutsocial squarespace stripe stubhub temporal thoughtmachine tiktok
tripadvisor twilio unity upstart vimeo wealthsimple webflow wise wistia
xendit zapier zendesk zocdoc
"""

LEVER = """
aircall algolia amplitude blockchain brave carta cloudbeds coalition
crypto deel dialpad discourse doximity eventbrite figma flexport getir
grammarly hopper humaans klarna leapsome matterport medallia mistral netlify
nielsen pave payoneer plaid podium proton quantcast rakuten ramp ripple
scribd shieldai sift skyscanner sonatype spotangels swordhealth thescore
tide tinder trulioo turing upwork veeva veriff wave weedmaps whoop wolt
yougov zego zerohash
"""

ASHBY = """
airbyte anthropic astronomer browserbase clay cohere deepgram descript
elevenlabs fireworks getcensus hex highnote infisical instabase linear
loops mercury metabase modal notion openai orb perplexity pinecone posthog
railway ramp replit render resend runwayml scale sourcegraph supabase
temporal together tremor vanta vercel warp weights zed
"""

REGION_HINTS = ("indonesia", "jakarta", "singapore", "malaysia", "vietnam",
                "thailand", "philippines", "apac", "asia", "bangalore", "india",
                "tokyo", "sydney", "hong kong")


def fetch(url: str, timeout: int = 20):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001 - probe should never crash the run
        return None, type(e).__name__


def probe(spec):
    kind, slug = spec
    if kind == "greenhouse":
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        data, err = fetch(url)
        jobs = (data or {}).get("jobs", []) if data else []
    elif kind == "lever":
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        data, err = fetch(url)
        jobs = data if isinstance(data, list) else []
    else:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        data, err = fetch(url)
        jobs = (data or {}).get("jobs", []) if data else []

    if err or not jobs:
        return {"kind": kind, "slug": slug, "ok": False, "error": err or "empty"}

    blob = json.dumps(jobs).lower()
    apac = sum(1 for h in REGION_HINTS if h in blob)
    return {
        "kind": kind, "slug": slug, "ok": True,
        "count": len(jobs),
        "apac_hints": apac,
        "url": url,
    }


def main() -> int:
    specs = ([("greenhouse", s) for s in GREENHOUSE.split()]
             + [("lever", s) for s in LEVER.split()]
             + [("ashby", s) for s in ASHBY.split()])
    print(f"Probing {len(specs)} candidate boards...\n")

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(probe, specs))

    ok = sorted([r for r in results if r["ok"]], key=lambda r: -r["count"])
    bad = [r for r in results if not r["ok"]]

    total = sum(r["count"] for r in ok)
    apac_boards = [r for r in ok if r["apac_hints"] >= 3]

    for r in ok:
        mark = "*" if r["apac_hints"] >= 3 else " "
        print(f"  [v]{mark}{r['kind']:<11}/{r['slug']:<18} {r['count']:>5} postings"
              f"  apac-signal {r['apac_hints']}")
    print(f"\n  {len(bad)} boards did not answer (404 or empty) - dropped.")
    print(f"  {len(ok)} live boards, {total:,} postings, "
          f"{len(apac_boards)} with a strong APAC signal.")

    OUT.write_text(json.dumps(
        {"boards": [{k: r[k] for k in ("kind", "slug", "count", "apac_hints")} for r in ok]},
        indent=1), encoding="utf-8")
    print(f"\n  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
