# Benchmark Evaluation

Harness for measuring IncidentOps AI end-to-end performance against planted incidents in the GitLab benchmark repository.

## Run

```bash
cd tools/benchmark
python run_benchmark.py --runs 3
```

## Artifacts

| Path | Description |
|------|-------------|
| `run_benchmark.py` | Main benchmark runner |
| `benchmark_report.md` | Generated results report |
| `.benchmark_cache/` | Cached retrieval evidence (v2 JSON) |

## Defaults

- Scenarios: `INC-101`, `INC-102`, `INC-103`
- Target repo: from `GITLAB_TARGET_REPO` env var
- Benchmark mode: enabled by default (caches retrieval, re-runs fusion/patch/validation/MR)

See [benchmark_report.md](benchmark_report.md) for latest results.
