# Extraction quality report

Generated: 2026-08-29T06:06:36.027734+00:00

## Extraction baseline (Tier A PDFs)

| Metric | Count |
|---|---|
| corpus_targets | 2806 |
| extracted | 390 |
| empty | 1 |
| failed | 0 |

## Filter summary

| Metric | Count |
|---|---|
| accepted (clean corpus) | 2408 |
| rejected | 2164 |
| rejected: EMPTY_EXTRACTION | 67 |
| rejected: NEAR_DUPLICATE | 331 |
| rejected: TIER_EXCLUDED | 1766 |

## Accepted token stats (after boilerplate strip)

{
  "min": 0,
  "max": 129440,
  "mean": 3501.9,
  "median": 570.5
}

## Top topic roots (accepted)

- `biosecurity-trade`: 581
- `drought-and-farm-support`: 512
- `animal-health`: 489
- `abares`: 190
- `agvet-chemicals`: 112
- `animal-welfare`: 99
- `agriculture-land`: 95
- `food-policy`: 92
- `climate-change`: 78
- `biosecurity`: 65
- `biotechnology`: 47
- `crops`: 23
- `plant-health`: 16
- `strategy-and-plans`: 9

## Artifacts

- Accepted manifest: `data/manifests/corpus_accepted.jsonl`
- Rejected manifest: `data/manifests/rejected.jsonl`
- Empty extraction review (CAI-018): `data/manifests/empty_extractions_review.md`
- Near-duplicate sample (CAI-019): `data/manifests/near_duplicate_review_sample.jsonl`

