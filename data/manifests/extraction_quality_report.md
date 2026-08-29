# Extraction quality report

Generated: 2026-08-28T01:52:07.946701+00:00

## Extraction baseline (Tier A PDFs)

| Metric | Count |
|---|---|
| tier_a_targets | 639 |
| extracted | 605 |
| empty | 34 |
| failed | 0 |

## Filter summary

| Metric | Count |
|---|---|
| accepted (clean corpus) | 601 |
| rejected | 235 |
| rejected: EMPTY_EXTRACTION | 34 |
| rejected: NEAR_DUPLICATE | 4 |
| rejected: TIER_EXCLUDED | 197 |

## Accepted token stats (after boilerplate strip)

{
  "min": 0,
  "max": 129440,
  "mean": 8678.8,
  "median": 1139
}

## Top topic roots (accepted)

- `drought-and-farm-support`: 336
- `animal-health`: 132
- `agvet-chemicals`: 50
- `animal-welfare`: 30
- `biotechnology`: 15
- `biosecurity`: 13
- `agriculture-land`: 7
- `climate-change`: 7
- `crops`: 7
- `strategy-and-plans`: 4

## Artifacts

- Accepted manifest: `data/manifests/corpus_accepted.jsonl`
- Rejected manifest: `data/manifests/rejected.jsonl`
- Empty extraction review (CAI-018): `data/manifests/empty_extractions_review.md`
- Near-duplicate sample (CAI-019): `data/manifests/near_duplicate_review_sample.jsonl`

