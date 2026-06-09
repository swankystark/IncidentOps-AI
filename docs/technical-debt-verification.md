# Technical Debt Verification

Date: 2026-06-05

## Repository Configuration UX

The dashboard now exposes all per-run repository settings:

```text
GitLab Target Repository
Target Branch
Target Application Path
Application Log Path
```

These values are sent with each `POST /api/incidents` request and persisted on the incident record:

```text
target_repo
target_branch
target_app_path
application_log_path
```

Verification:

```text
target_repo: swankystark20-group/incidentops-demo-app
target_branch: main
target_app_path: invoice-app
application_log_path: invoice-app/application.log
```

The incident detail API returned the same persisted values.

## Pipeline Attribution Logic

Pipeline selection now prefers:

1. configured target branch plus incident SHA when available
2. configured target branch
3. incident-related commit SHA
4. latest successful pipeline
5. latest pipeline as a final fallback

Selected metadata is persisted on the incident:

```text
selected_pipeline_id
selected_pipeline_ref
selected_pipeline_sha
selected_pipeline_status
selected_pipeline_web_url
selected_pipeline_source
```

Benchmark verification selected the configured branch instead of an MR ref:

```text
id: 2569151101
status: failed
ref: main
sha: 89ccc4e1bbcb60b96d0b9c1c3ddf6c2b7dc9121d
source: target_branch
url: https://gitlab.com/swankystark20-group/incidentops-demo-app/-/pipelines/2569151101
```

## INC-103 Runtime Log Evidence

Before:

```text
2026-06-05 09:36:30 [INFO] Initializing serialization library...
```

After:

```text
2026-06-05 10:23:51 [INFO] Initializing serialization library...
2026-06-05 10:23:51 [INFO] Loading billing tax engine during container startup dependency check...
2026-06-05 10:23:51 [DEBUG] Resolved requirements.txt dependency pin: pydantic==1.9.0
2026-06-05 10:23:51 [DEBUG] billing.tax_engine imports pydantic.model_validator, which requires pydantic>=2.0
2026-06-05 10:23:51 [WARNING] Detected declared dependency/runtime contract mismatch before import.
2026-06-05 10:23:51 [ERROR] ImportError: cannot import name 'model_validator' from 'pydantic' under requirements.txt pin pydantic==1.9.0
2026-06-05 10:23:51 [ERROR]   File "billing/tax_engine.py", line 15, in <module>
2026-06-05 10:23:51 [ERROR]     from pydantic import BaseModel, model_validator
2026-06-05 10:23:51 [WARNING] Container startup blocked before API routes were mounted.
2026-06-05 10:23:51 [WARNING] Dependency graph points to requirements.txt as the remediation target.
2026-06-05 10:23:51 [CRITICAL] Dependency mismatch detected: billing.tax_engine requires pydantic>=2.0 but requirements.txt pins pydantic==1.9.0.
```

## Verification Commands

Backend compile:

```text
python -m compileall app
PASS
```

Backend import:

```text
from app.main import app
PASS
```

Frontend lint:

```text
npm run lint
PASS
```

Frontend production build:

```text
npm run build
PASS
```

## Result

Repository-agnostic execution no longer depends on hidden process-level assumptions for target repository, branch, target application path, or runtime log path. Pipeline evidence is now attributed to the configured target branch before falling back to less-specific pipeline sources.
