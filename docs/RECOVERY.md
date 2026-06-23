# Recovery Guide

Use this when a run stalls, fails, or needs to be resumed.

## 1. Model Quota Or Rate Limit

**Symptoms**
- Logs mention `429`, `RESOURCE_EXHAUSTED`, quota, or rate limit.
- The incident status becomes `WAITING_FOR_RETRY`.
- `checkpoint_state` and `failure_reason` are saved on the incident record.

**Recovery**
1. Verify the model key is still valid.
2. Confirm the model provider is reachable.
3. Resume the incident with `POST /api/incidents/{incident_id}/resume`.

## 2. Resume Fails Immediately

**Symptoms**
- The resume endpoint returns `400` because no checkpoint exists.
- The checkpoint payload is corrupted.

**Recovery**
1. Inspect the incident row in SQLite.
2. Confirm `checkpoint_state` is populated.
3. Start a fresh incident if the checkpoint is missing or unreadable.

## 3. Validation Failure

**Symptoms**
- Validation logs show failing tests.
- The workflow loops back to patch generation once.

**Recovery**
1. Read the validation logs attached to the incident.
2. Compare the generated patch against the affected source file.
3. Check `test_target` in the incident template.
4. If the retry already happened, fix the source of the regression manually and rerun.

## 4. GitLab Access Failure

**Symptoms**
- Repository validation fails.
- File fetches, branch creation, or MR creation fail.

**Recovery**
1. Confirm the GitLab PAT has `api` scope.
2. Verify `target_repo` and `target_branch`.
3. Confirm `target_app_path` matches the repository layout.
4. Re-run repository validation before triggering the incident again.

## 5. Missing Log Evidence

**Symptoms**
- The log service returns little or no evidence.

**Recovery**
1. Check `APPLICATION_LOG_PATH`.
2. Confirm the benchmark or runtime trigger actually produced a log file.
3. Recreate the incident with the correct log path.

## 6. Safe Restart Sequence

1. Stop the backend and frontend.
2. Keep the SQLite database if you want to preserve prior incidents.
3. Restart the backend.
4. Restart the frontend.
5. Resume any checkpointed incident if needed.
