# Job Radar

*Scheduled ingestion from 87 public company job boards and four remote-work APIs, de-duplicated, scored against a fixed candidate profile, and published as a static dashboard that refreshes itself daily.*

**🔗 [Live board](https://amindraa05.github.io/job-radar/)**

---

## What it does

Roughly 12,000 postings are pulled on every run. About 9,900 survive de-duplication. Under 200 pass the relevance filter. That reduction is the product: a list of ten thousand jobs is noise, and the value lies in discarding most of them for a reason you can read.

Each surviving posting carries its score, the reasons behind it, the skills it matches, and the technologies it asks for that the profile does not claim.

| Stage | Typical volume |
|---|---|
| Fetched from all sources | ~12,000 |
| After de-duplication | ~9,900 |
| Passed the relevance gate | ~190 |
| Scored *strong* | ~25 |

## Sources

**Applicant tracking systems**, one public board per company: Greenhouse, Lever, Ashby. The board list in [`ingest/boards.json`](ingest/boards.json) is not hand-written. [`discover.py`](ingest/discover.py) probes a wide candidate list, keeps whatever answers, and records how many postings each board carries in the regions that matter. Of 201 candidates probed, 87 responded.

**Remote-work aggregators**: Remotive, RemoteOK, Arbeitnow, Himalayas.

**Not used, deliberately.** LinkedIn, Indeed, Glassdoor, Jobstreet, Glints and Kalibrr publish no API, and scraping them would breach their terms. Indonesian coverage is therefore thin and arrives mostly through global companies hiring into Jakarta or Singapore. The dashboard says so on its face rather than implying completeness.

## Scoring

Defined in [`ingest/match.py`](ingest/match.py), against a profile of about two and a half years of infrastructure experience, based in Indonesia.

- **Role is a gate, not a bonus.** A marketing posting that mentions AWS is still a marketing posting. Titles are classified first; a block list catches the near misses, such as physical security systems engineers and pre-sales solution architects, which otherwise score well on vocabulary alone.
- **Seniority is penalised, not hidden.** Senior, staff and principal titles carry large negative weights, because occasionally one is worth a speculative application.
- **Geography is the sharpest filter.** Postings advertised as remote are frequently restricted to a single country. Those are detected and the restriction is named. Roles needing relocation are kept but flagged, since they also need a visa.

[`ingest/test_match.py`](ingest/test_match.py) holds 35 regression checks over the classifier and runs in CI before any refresh. The matcher is the whole product; a silent regression there fills the board with jobs the CV cannot support.

## Reliability

- A source that fails does not fail the run. Each fetcher returns `(rows, error)`, and partial failure is recorded in [`docs/assets/run.json`](docs/assets/run.json) rather than hidden.
- The workflow **refuses to publish a run producing fewer than 20 rows**, so a network fault cannot wipe a working dashboard.
- Board discovery re-runs weekly. Boards appear and disappear; a static list rots.
- The dashboard marks its own data stale after 60 hours, rather than presenting old figures as current.

## Privacy

Applied and dismissed marks live in `localStorage` and are never transmitted or committed. The repository is public; a job hunt is not. Nothing in this repository identifies which roles anyone applied to.

## Run it locally

```bash
python ingest/discover.py     # optional: re-probe the board list
python ingest/test_match.py   # 35 classifier checks
python ingest/run.py          # fetch, dedupe, score, write docs/assets/
python -m http.server --directory docs
```

No third-party Python packages. Standard library only.

## Layout

```
ingest/
  discover.py      probe candidate boards, write boards.json
  fetch.py         one function per source, none of which can crash the run
  match.py         profile, role gate, seniority and geography rules, scoring
  run.py           orchestrate, dedupe, score, write the payload and manifest
  test_match.py    regression checks over the classifier
docs/
  index.html       dashboard
  assets/app.js    filtering, sorting, local application tracking
  assets/jobs.json generated payload
  assets/run.json  manifest: counts, timings, per-source failures
.github/workflows/refresh.yml   daily cron, tests, empty-run guard, commit
```

## Limitations

Salary is absent from most postings. Whether a role is still open cannot be verified. Visa sponsorship is rarely stated. The scoring is a heuristic and will misjudge individual postings, which is why every row shows its reasoning instead of only a number.

## Licence

[MIT](LICENSE) for the code. Postings belong to their respective employers and are linked, not republished.
