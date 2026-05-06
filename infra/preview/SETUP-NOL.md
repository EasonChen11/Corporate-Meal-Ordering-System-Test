# NOL One-Time Setup for Preview Environments

All steps run **on the NOL host (A 機)** as a user with docker permission and sudo for nginx.
Re-running any block is safe (idempotent) unless explicitly noted.

## Prerequisites

- Docker (with compose v2), git, curl, jq, gh CLI installed
- Repo cloned at `/home/nol/Corporate-Meal-Ordering-System` (adjust `DEPLOY_PATH` below if different)
- Jenkins already serves `https://nol.cs.nycu.edu.tw/jenkins/`

```bash
export DEPLOY_PATH=/home/nol/Corporate-Meal-Ordering-System
cd "$DEPLOY_PATH"
git pull
```

## 1. Shared docker network

```bash
docker network inspect preview-net >/dev/null 2>&1 \
  || docker network create preview-net
```

## 2. Shared preview router

```bash
bash "$DEPLOY_PATH/infra/preview/router/run-router.sh"
curl -s http://127.0.0.1:18080/ ; echo
# expect: preview-router OK
```

## 3. Outer nginx — add /preview/ location

Edit the existing NOL nginx vhost (the one already serving `/jenkins/` and `/`). Add inside the `server { ... }` block, **before** the catch-all `/`:

```nginx
location /preview/ {
    proxy_pass         http://127.0.0.1:18080;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
}
```

Reload:

```bash
sudo nginx -t && sudo systemctl reload nginx
curl -sk https://nol.cs.nycu.edu.tw/preview/ ; echo
# expect: preview-router OK
```

## 4. Jenkins — Multibranch Pipeline for CD

In the Jenkins UI:

1. **New Item → Multibranch Pipeline**, name `mealorder-cd`.
2. **Branch Sources → GitHub**, point at the repo. Add credentials (PAT with `repo` + `admin:repo_hook`).
3. **Build Configuration → by Jenkinsfile**, script path: `Jenkinsfile`.
4. **Property strategy → Suppress automatic SCM triggering for `main` only if you want manual prod deploys** (default: auto on every push to main).
5. **Project Recognizers → Pipeline Jenkinsfile**, **Trust: From users with Admin or Write permission**.
6. Save. First scan will pick up open PRs and `main`.

Webhook is created automatically by the GitHub Branch Source plugin.

## 5. Jenkins — Cleanup pipeline

1. **New Item → Pipeline**, name `mealorder-cleanup`.
2. **Build Triggers → GitHub hook trigger for GITScm polling** + add **Generic Webhook Trigger** (plugin) listening for `pull_request.action == "closed"`. Map payload:
   - `BRANCH_NAME` ← `$.pull_request.head.ref`
   - `PR_STATE`    ← `$.pull_request.state`
3. **Pipeline → Pipeline script from SCM**, script path: `Jenkinsfile.cleanup`.
4. Add a **Build periodically** trigger: `H * * * *` (hourly sweep).

Add a webhook on the GitHub repo (Settings → Webhooks) targeting:
`https://nol.cs.nycu.edu.tw/jenkins/generic-webhook-trigger/invoke?token=<token>`
Events: **Pull requests** only.

## 6. Jenkins credentials

| ID | Type | Used for |
|---|---|---|
| `gh-pat` | Secret text | `gh auth login --with-token < $GH_PAT_FILE` in pipelines (PR comments, sweep) |
| `github-app` | GitHub App or PAT | Branch source above |

Inject in pipelines via:
```groovy
withCredentials([string(credentialsId: 'gh-pat', variable: 'GH_TOKEN')]) { ... }
```

## 7. Verification end-to-end

After both pipelines exist, push a throwaway branch, open a PR, and confirm:
- `unit` + `integration` GitHub Actions go green
- Jenkins `mealorder-cd` runs Deploy preview → posts a `Preview: https://...` comment on the PR
- `https://nol.cs.nycu.edu.tw/preview/<branch>/health` returns `200`
- Close the PR → within seconds (webhook) the stack is gone (`docker compose ls | grep mealorder-`)
- If webhook missed: within 1 hour the cron sweep removes it
