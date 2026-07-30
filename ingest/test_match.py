"""Regression tests for the matcher.

These exist because the classifier is the whole product: get the role gate
wrong and the dashboard fills with jobs the CV cannot support. Run before any
change to match.py.

    python ingest/test_match.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match  # noqa: E402

MUST_REJECT = [
    "Physical Security Systems Engineer - APAC",
    "Customer Solutions Architect",
    "Sales Engineer, Cloud Platform",
    "iOS Engineer",
    "QA Engineer, Automation",
    "Senior Data Scientist",
    "Mobile Engineer, Android",
    "Technical Recruiter",
    "Mechanical Engineer",
    "Machine Learning Engineer",
]

MUST_ACCEPT = [
    "Site Reliability Engineer",
    "Cloud Infrastructure Engineer",
    "Infrastructure Engineer, Storage",
    "DevOps Engineer",
    "Systems Engineer",
    "Linux Systems Administrator",
    "Platform Engineer",
    "Production Engineer",
    "Observability Engineer",
]

# Titles containing a rejected substring inside a longer word must still pass.
NO_FALSE_REJECT = [
    "Various Systems Engineer",
    "Scenarios Platform Engineer",
    "Rebuilding Infrastructure Engineer",
]

SENIORITY_CASES = [
    ("Senior Site Reliability Engineer", "senior"),
    ("Staff Infrastructure Engineer", "staff"),
    ("Principal Systems Engineer", "principal"),
    ("Director of Infrastructure", "management"),
    ("Junior DevOps Engineer", "junior"),
    ("Site Reliability Engineer", "mid"),
]

GEO_CASES = [
    ("Jakarta, Indonesia", "", "apac"),
    ("Singapore", "", "apac"),
    ("Remote - Worldwide", "", "worldwide"),
    ("Remote", "", "remote-unspecified"),
    ("Berlin, Germany", "", "elsewhere"),
    ("Remote", "This role is US-only.", "restricted"),
]


def main() -> int:
    fails: list[str] = []

    for t in MUST_REJECT:
        role, _ = match.classify_role(t)
        if role is not None:
            fails.append(f"should reject but got role={role!r}: {t}")

    for t in MUST_ACCEPT + NO_FALSE_REJECT:
        role, _ = match.classify_role(t)
        if role is None:
            fails.append(f"should accept but was rejected: {t}")

    for t, want in SENIORITY_CASES:
        got, _ = match.classify_seniority(t)
        if got != want:
            fails.append(f"seniority {got!r} != {want!r}: {t}")

    for loc, text, want in GEO_CASES:
        got, _ = match.geo_bucket(loc, text)
        if got != want:
            fails.append(f"geo {got!r} != {want!r}: {loc!r} / {text!r}")

    # A senior role outside APAC must not outrank a mid-level APAC role.
    apac_mid = match.score({"title": "Site Reliability Engineer",
                            "location": "Jakarta, Indonesia",
                            "text": "aws linux prometheus grafana on-call incident"})
    us_senior = match.score({"title": "Senior Site Reliability Engineer",
                             "location": "Austin, Texas",
                             "text": "aws linux prometheus grafana on-call incident"})
    if apac_mid["score"] <= us_senior["score"]:
        fails.append(f"ranking: APAC mid {apac_mid['score']} should beat "
                     f"US senior {us_senior['score']}")

    total = len(MUST_REJECT) + len(MUST_ACCEPT) + len(NO_FALSE_REJECT) \
        + len(SENIORITY_CASES) + len(GEO_CASES) + 1
    if fails:
        print(f"FAILED {len(fails)} of {total} checks\n")
        for f in fails:
            print("  x", f)
        return 1
    print(f"all {total} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
