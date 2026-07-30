"""Match profile and scoring.

The profile is derived from the CV in ~/Downloads/CV_2026 but holds only what
matching needs: skills, seniority band, geography. No contact details, because
this repository is public.

Scoring is deliberately harsh. A board of ten thousand postings is worthless;
the value is in throwing most of them away for a stated reason. Every score
carries the reasons that produced it so a bad ranking can be argued with.
"""
from __future__ import annotations

import re

# --------------------------------------------------------------------------
# Profile
# --------------------------------------------------------------------------

PROFILE = {
    "years_experience": 2.5,
    "based": "Indonesia",
    "timezone": "UTC+7",
    "open_to": ["remote", "hybrid", "onsite jakarta", "relocation"],
    "needs_sponsorship": True,     # for roles outside Indonesia

    # Weighted: the first group is what the CV can defend in depth.
    "core_skills": {
        "aws": 3, "ec2": 2, "rds": 2, "vpc": 2, "iam": 2, "cloudwatch": 2,
        "linux": 3, "rhel": 2, "red hat": 2, "centos": 2, "ubuntu": 2,
        "windows server": 2, "active directory": 2, "dns": 2, "group policy": 1,
        "vmware": 3, "vcenter": 2, "esxi": 2, "virtualization": 2,
        "prometheus": 3, "grafana": 3, "monitoring": 2, "observability": 3,
        "sql server": 2, "always on": 1, "postgresql": 2, "mariadb": 1,
        "mysql": 1, "mongodb": 1, "database": 1,
        "python": 2, "bash": 2, "shell": 1, "powershell": 2, "sql": 1,
        "on-call": 2, "incident": 2, "sre": 3, "reliability": 3,
        "infrastructure": 2, "change management": 1, "itil": 1,
        "bare metal": 2, "hardware": 1, "datacenter": 2, "data center": 2,
        "banking": 1, "regulated": 1, "hybrid cloud": 2, "on-premise": 2,
    },

    # Present in postings but NOT on the CV. Not disqualifying; they lower
    # confidence and are surfaced as gaps so the application can address them.
    "gap_skills": {
        "kubernetes", "k8s", "terraform", "ansible", "docker", "helm",
        "ci/cd", "jenkins", "gitops", "argocd", "istio", "service mesh",
        "golang", "go ", "rust", "kafka", "spark", "airflow", "gcp",
        "azure", "openshift", "puppet", "chef", "saltstack",
    },
}

# --------------------------------------------------------------------------
# Role and seniority classification
# --------------------------------------------------------------------------

ROLE_PATTERNS = [
    (r"\bsite reliability\b|\bsre\b", "sre", 1.00),
    (r"\bplatform engineer|platform engineering\b", "platform", 0.95),
    (r"\bdevops\b", "devops", 0.95),
    (r"\bcloud (infrastructure |infra |systems )?engineer\b", "cloud", 1.00),
    (r"\binfrastructure engineer|infra engineer\b", "infra", 1.00),
    (r"\bsystems? engineer\b", "systems", 0.90),
    (r"\bsystems? administrator|sysadmin\b", "sysadmin", 0.85),
    (r"\bproduction engineer\b", "production", 0.90),
    (r"\bnetwork engineer\b", "network", 0.60),
    (r"\bdatabase (administrator|engineer)|\bdba\b", "dba", 0.70),
    (r"\bsolutions? architect\b", "architect", 0.55),
    (r"\btechnical support engineer|support engineer\b", "support", 0.45),
    (r"\bobservability|monitoring engineer\b", "observability", 0.90),
]

SENIORITY = [
    (r"\bintern\b|\binternship\b|\bworking student\b", "intern", -60),
    (r"\bgraduate\b|\bentry.level\b|\bjunior\b|\bassociate\b", "junior", 12),
    (r"\bprincipal\b|\bdistinguished\b|\bfellow\b", "principal", -45),
    (r"\bstaff\b", "staff", -35),
    (r"\bsenior\b|\bsr\.?\b|\blead\b", "senior", -18),
    (r"\bhead of\b|\bdirector\b|\bvp\b|\bmanager\b", "management", -55),
]

# --------------------------------------------------------------------------
# Geography
# --------------------------------------------------------------------------

ID_APAC = ("indonesia", "jakarta", "bali", "bandung", "surabaya",
           "singapore", "malaysia", "kuala lumpur", "vietnam", "thailand",
           "bangkok", "philippines", "manila", "apac", "asia pacific",
           "southeast asia", "sea region", "hong kong", "tokyo", "japan",
           "australia", "sydney", "india", "bangalore")

WORLDWIDE = ("worldwide", "anywhere", "global", "any location",
             "remote - global", "fully remote", "location independent")

# A posting restricted to these is out of reach without relocation and a visa.
EXCLUSIVE = [
    (r"\bus[- ]only\b|\bunited states only\b|\busa only\b|\bmust be (located |based )?in the (us|united states)\b", "US-only"),
    (r"\beu[- ]only\b|\beurope only\b|\bmust be (located |based )?in (the )?(eu|europe)\b", "EU-only"),
    (r"\buk[- ]only\b|\bmust be (located |based )?in the uk\b", "UK-only"),
    (r"\bcanada only\b|\bmust be (located |based )?in canada\b", "Canada-only"),
    (r"\bsecurity clearance\b|\bts/sci\b|\bpolygraph\b", "clearance required"),
    (r"\bmust be a us citizen\b|\bus citizenship required\b", "US citizenship"),
]


# Titles that match an infrastructure pattern but are a different job. Without
# these, "Physical Security Systems Engineer" scores as a systems role and
# "Customer Solutions Architect" scores as an architecture role.
NOT_INFRA = re.compile(
    r"\bphysical security\b|\bsecurity systems\b|\bfire alarm\b"
    r"|\bcustomer (success|solutions?|engineer)\b|\bsolutions? consultant\b"
    r"|\bpre.?sales\b|\bsales engineer\b|\baccount (executive|manager)\b"
    r"|\bfield (engineer|technician)\b|\bmechanical\b|\belectrical\b"
    r"|\bmanufacturing\b|\bhardware design\b|\bfirmware\b|\bsilicon\b"
    r"|\bqa engineer\b|\btest engineer\b|\bdata (scientist|analyst)\b"
    r"|\bmachine learning engineer\b|\bresearch (scientist|engineer)\b"
    r"|\bfrontend\b|\bfront.end\b|\bmobile\b|\bios\b|\bandroid\b"
    r"|\bgame\b|\bgraphic\b|\brecruit\b|\bteacher\b|\bnurse\b"
)


def classify_role(title: str):
    t = title.lower()
    if NOT_INFRA.search(t):
        return None, 0.0
    best = (None, 0.0)
    for pat, name, weight in ROLE_PATTERNS:
        if re.search(pat, t) and weight > best[1]:
            best = (name, weight)
    return best


def classify_seniority(title: str):
    t = title.lower()
    for pat, name, delta in SENIORITY:
        if re.search(pat, t):
            return name, delta
    return "mid", 8          # unlabelled usually means mid-level


def geo_bucket(location: str, text: str):
    loc = (location or "").lower()
    blob = f"{loc} {text[:1500].lower()}"

    for pat, label in EXCLUSIVE:
        if re.search(pat, blob):
            return "restricted", label

    if any(k in loc for k in ID_APAC):
        return "apac", None
    if any(k in loc for k in WORLDWIDE):
        return "worldwide", None
    if "remote" in loc:
        # Remote, but the region is unstated. Treat as unknown rather than open.
        return "remote-unspecified", None
    if loc.strip():
        return "elsewhere", None
    return "unknown", None


def score(job: dict) -> dict:
    """Return the job enriched with score, band and human-readable reasons."""
    title = job.get("title", "")
    text = job.get("text", "") or ""
    blob = f"{title} {text}".lower()

    role, role_weight = classify_role(title)
    seniority, sen_delta = classify_seniority(title)
    geo, restriction = geo_bucket(job.get("location", ""), text)

    reasons: list[str] = []

    # Role is a gate, not a bonus: a marketing job with AWS in the text is
    # still a marketing job.
    if not role:
        return {**job, "score": 0, "band": "out", "role": None,
                "seniority": seniority, "geo": geo, "restriction": restriction,
                "matched": [], "gaps": [], "reasons": ["not an infrastructure role"]}

    base = 40 * role_weight
    reasons.append(f"{role} role")

    base += sen_delta
    if sen_delta < 0:
        reasons.append(f"{seniority} level, above ~{PROFILE['years_experience']:.0f}y experience")
    elif seniority == "junior":
        reasons.append("junior/associate level")

    geo_delta = {"apac": 24, "worldwide": 16, "remote-unspecified": 4,
                 "unknown": -2, "elsewhere": -22, "restricted": -70}[geo]
    base += geo_delta
    if geo == "apac":
        reasons.append("hiring in Indonesia or APAC")
    elif geo == "worldwide":
        reasons.append("open worldwide")
    elif geo == "restricted":
        reasons.append(f"blocked: {restriction}")
    elif geo == "elsewhere":
        reasons.append("onsite outside APAC, needs relocation and a visa")

    matched = sorted({s for s in PROFILE["core_skills"] if s in blob})
    weight = sum(PROFILE["core_skills"][s] for s in matched)
    skill_points = min(weight * 1.6, 34)
    base += skill_points
    if matched:
        reasons.append(f"{len(matched)} matching skills")

    gaps = sorted({g.strip() for g in PROFILE["gap_skills"] if g in blob})
    if gaps:
        base -= min(len(gaps) * 1.6, 12)
        reasons.append(f"{len(gaps)} unlisted technologies")

    total = max(0, min(100, round(base)))
    band = ("strong" if total >= 62 else
            "worth a look" if total >= 45 else
            "stretch" if total >= 30 else "out")

    return {**job, "score": total, "band": band, "role": role,
            "seniority": seniority, "geo": geo, "restriction": restriction,
            "matched": matched[:14], "gaps": gaps[:10], "reasons": reasons}
