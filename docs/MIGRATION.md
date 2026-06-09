# GitHub Migration Guide

Target repository: [github.com/swankystark/IncidentOps-AI](https://github.com/swankystark/IncidentOps-AI)

## What Migrates

| Included | Excluded (stays in GitLab) |
|----------|---------------------------|
| `backend/` | `invoice-app/` (benchmark target) |
| `frontend/` | `currency/` (legacy local copy) |
| `docs/` | |
| `tests/` | |
| `tools/` | |
| `incidents.json` | |
| `run_scenario.py` | |
| `docker-compose.yml` | |
| `.env.example` | |

## Push to GitHub

```bash
# From repository root
git add .gitignore .env.example README.md docker-compose.yml
git add backend/ frontend/ docs/ tests/ tools/ incidents.json run_scenario.py

git commit -m "Prepare IncidentOps AI for public GitHub release"

git push github main
```

If `main` does not exist yet:

```bash
git branch -M main
git push -u github main
```

## Remote Configuration

- `origin` — GitLab benchmark repository (invoice-app)
- `github` — GitHub platform repository (IncidentOps AI)

To make GitHub the default:

```bash
git remote rename origin gitlab
git remote rename github origin
```

## Security Note

Remove embedded credentials from git remotes before sharing the repository:

```bash
git remote set-url origin https://github.com/swankystark/IncidentOps-AI.git
```

Never commit `.env` files containing `GEMINI_API_KEY` or `GITLAB_PAT`.
