# Near-duplicate manual review (CAI-019)

**Status:** ✅ **Closed** 2026-08-28  
**Pairs reviewed:** 4 / 4  
**Verdict:** All auto-rejections confirmed correct. No annual-report false positives.

| # | Similarity | Rejected (dropped) | Kept | Verdict | Notes |
|---:|---:|---|---|---|---|
| 1 | 1.0 | [fmd-stats-feb14-0.pdf](../pdf/source/agriculture.gov.au/drought-and-farm-support/farm-management-deposits/statistics/fmd-stats-feb14-0.pdf) | [fmd-stats-feb14.pdf](../pdf/source/agriculture.gov.au/drought-and-farm-support/farm-management-deposits/statistics/fmd-stats-feb14.pdf) | **Confirm** | Same FMD stats table; `_0` URL duplicate |
| 2 | 1.0 | [fmdstats-may2014-0.pdf](../pdf/source/agriculture.gov.au/drought-and-farm-support/farm-management-deposits/statistics/fmdstats-may2014-0.pdf) | [fmdstats-may2014.pdf](../pdf/source/agriculture.gov.au/drought-and-farm-support/farm-management-deposits/statistics/fmdstats-may2014.pdf) | **Confirm** | Same May 2014 stats; `_0` URL duplicate |
| 3 | 1.0 | [fdf-funding-information-hrcpdi.pdf](../pdf/source/agriculture.gov.au/drought-and-farm-support/future-drought-fund/helping-regional-communities-prepare-for-drought-initiative/fdf-funding-information-hrcpdi.pdf) | [funding-information-drought-resilience-commercialisation-initiative.pdf](../pdf/source/agriculture.gov.au/drought-and-farm-support/future-drought-fund/drought-resilience-commercialisation-initiative/funding-information-drought-resilience-commercialisation-initiative.pdf) | **Confirm** | Identical generic FDF funding-information template; different program titles on site |
| 4 | 0.94 | [sources-of-agvet-data-australia.pdf](../pdf/source/agriculture.gov.au/agvet-chemicals/domestic-policy/independent-research-agvet-chemicals-monitoring/sources-of-agvet-data-australia.pdf) | [sources-of-agvet-data-in-australia-reissued.pdf](../pdf/source/agriculture.gov.au/agvet-chemicals/domestic-policy/independent-research-agvet-chemicals-monitoring/sources-of-agvet-data-in-australia-reissued.pdf) | **Confirm** | Reissued edition kept; original is near-duplicate |

## Checks performed

- [x] No annual reports with same title but different years were collapsed
- [x] Each `kept_doc_id` in `rejected.jsonl` points to the better copy (canonical URL or reissue)
- [x] All four pairs are true duplicates, not related-but-distinct policy documents

## Artifacts

- Sample JSONL: [`near_duplicate_review_sample.jsonl`](near_duplicate_review_sample.jsonl)
- Full rejections: [`rejected.jsonl`](rejected.jsonl) (`reason: NEAR_DUPLICATE`)
