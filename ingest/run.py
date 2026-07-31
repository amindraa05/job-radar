"""Orchestrate a full refresh: fetch every source, normalise, dedupe, score.

Writes docs/assets/jobs.json (the dashboard payload) and docs/assets/run.json
(the manifest: what succeeded, what failed, how long it took). Partial failure
is normal and recorded rather than hidden.

Run: python ingest/run.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch          # noqa: E402
import match          # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOARDS = ROOT / "ingest" / "boards.json"
OUT_JOBS = ROOT / "docs" / "assets" / "jobs.json"
OUT_RUN = ROOT / "docs" / "assets" / "run.json"

# Only these bands reach the dashboard. Everything else is counted and dropped;
# the manifest records how many, so the filter itself stays auditable.
KEEP_BANDS = {"strong", "worth a look", "stretch"}
MAX_ROWS = 1200


def job_id(j: dict) -> str:
    key = f"{j.get('company','').lower()}|{re.sub(r'[^a-z0-9]+', '', j.get('title','').lower())}"
    return hashlib.sha1(key.encode()).hexdigest()[:14]


def main() -> int:
    t0 = time.time()
    boards = json.loads(BOARDS.read_text(encoding="utf-8"))["boards"]
    print(f"Refreshing from {len(boards)} ATS boards + {len(fetch.AGGREGATORS)} aggregators\n")

    raw: list[dict] = []
    failures: list[dict] = []
    per_source: dict[str, int] = {}

    def pull_board(b):
        fn = fetch.ATS[b["kind"]]
        rows, err = fn(b["slug"])
        return b, rows, err

    # Workable rate-limits concurrent callers, so it is pulled serially while
    # everything else runs in parallel.
    serial = [b for b in boards if b["kind"] == "workable"]
    parallel = [b for b in boards if b["kind"] != "workable"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(pull_board, b) for b in parallel]
        for fut in as_completed(futures):
            b, rows, err = fut.result()
            if err:
                failures.append({"source": f"{b['kind']}/{b['slug']}", "error": err})
                continue
            raw.extend(rows)
            per_source[b["kind"]] = per_source.get(b["kind"], 0) + len(rows)

    for b in serial:
        _, rows, err = pull_board(b)
        if err:
            failures.append({"source": f"{b['kind']}/{b['slug']}", "error": err})
            continue
        raw.extend(rows)
        per_source[b["kind"]] = per_source.get(b["kind"], 0) + len(rows)
        time.sleep(1.2)

    for name, fn in fetch.AGGREGATORS.items():
        rows, err = fn()
        if err and not rows:
            failures.append({"source": name, "error": err})
            continue
        if err:
            failures.append({"source": name, "error": f"partial: {err}"})
        raw.extend(rows)
        per_source[name] = len(rows)

    print(f"  fetched {len(raw):,} raw postings")
    for k in sorted(per_source, key=lambda x: -per_source[x]):
        print(f"    {k:<12} {per_source[k]:>6,}")
    if failures:
        print(f"  {len(failures)} source(s) failed:")
        for f in failures[:8]:
            print(f"    ! {f['source']}: {f['error']}")

    # dedupe on company+title; the same role often appears on several boards
    seen: dict[str, dict] = {}
    for j in raw:
        if not j.get("title") or not j.get("url"):
            continue
        jid = job_id(j)
        if jid in seen:
            seen[jid].setdefault("also_on", []).append(j["source"])
            continue
        j["id"] = jid
        seen[jid] = j
    deduped = list(seen.values())
    print(f"  {len(deduped):,} after dedupe ({len(raw) - len(deduped):,} duplicates merged)")

    scored = [match.score(j) for j in deduped]
    bands: dict[str, int] = {}
    for s in scored:
        bands[s["band"]] = bands.get(s["band"], 0) + 1

    kept = [s for s in scored if s["band"] in KEEP_BANDS]
    kept.sort(key=lambda s: -s["score"])
    kept = kept[:MAX_ROWS]

    print("\n  band distribution:")
    for b in ("strong", "worth a look", "stretch", "out"):
        print(f"    {b:<14} {bands.get(b, 0):>6,}")
    print(f"\n  {len(kept):,} rows written to the dashboard")

    payload = []
    for s in kept:
        payload.append({
            "id": s["id"], "t": s["title"], "c": s["company"], "u": s["url"],
            "l": s["location"][:90], "src": s["source"], "d": str(s.get("posted_at") or "")[:10],
            "sc": s["score"], "b": s["band"], "r": s["role"], "sen": s["seniority"],
            "geo": s["geo"], "rx": s["restriction"],
            "m": s["matched"], "g": s["gaps"], "why": s["reasons"],
            "snip": (s.get("text") or "")[:220],
        })

    OUT_JOBS.parent.mkdir(parents=True, exist_ok=True)
    OUT_JOBS.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    manifest = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seconds": round(time.time() - t0, 1),
        "boards_probed": len(boards),
        "raw": len(raw),
        "deduped": len(deduped),
        "bands": bands,
        "written": len(kept),
        "per_source": per_source,
        "failures": failures,
    }
    OUT_RUN.write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    kb = OUT_JOBS.stat().st_size / 1024
    print(f"  jobs.json {kb:.0f} KB, run.json written, {manifest['seconds']}s total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
