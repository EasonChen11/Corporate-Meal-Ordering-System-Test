# NOL One-Time Setup for TBD Deployment

All steps run **on the NOL host (A 機)** as a user with docker permission and sudo for nginx.
Re-running any block is safe (idempotent) unless explicitly noted.

This setup supports the Trunk-Based Development pipeline:
- `merge to main` → staging at `https://nol.cs.nycu.edu.tw/meal-staging/`
- `git tag v*.*.*` → production at `https://nol.cs.nycu.edu.tw/meal/`
- Root `/` 維持既有靜態網站，本作業不接管。

## Prerequisites

- Docker (with compose v2), curl, jq installed on the host
- Jenkins already serves `https://nol.cs.nycu.edu.tw/jenkins/`

> **Note**: a persistent source-code clone on the NOL host is **no longer required**. Jenkins checks
> out the repo into its own workspace and runs `docker compose` from there. The host only needs the
> Docker daemon — no `/home/nol/Corporate-Meal-Ordering-System` directory needed.

## 1. Shared docker network

```bash
docker network inspect preview-net >/dev/null 2>&1 \
  || docker network create preview-net
```

## 2. Shared internal router (run from any directory)

The router script can be run from any checkout (e.g. a one-time clone, or from inside a Jenkins
workspace). After initial setup, the router container is persistent and does not need to be re-run.

```bash
# Example using a temporary checkout — or any path that has the repo files:
bash infra/preview/router/run-router.sh
curl -s http://127.0.0.1:18080/ ; echo
# expect: preview-router OK
```

若改了 `Caddyfile`，重跑這個腳本即可。

## 3. Outer nginx — 新增 /meal-staging/ 與 /meal/ location

編輯既有 NOL nginx vhost（同一個 server block 已 serve `/jenkins/` 與 `/`）。在 catch-all `/` **之前**插入：

```nginx
location /meal-staging/ {
    proxy_pass         http://127.0.0.1:18080;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
}

location /meal/ {
    proxy_pass         http://127.0.0.1:18080;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
}
```

若 PR preview 仍保留（預設停用），維持原有 `location /preview/` 區塊；否則可一併移除。

Reload:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

驗證（注意：此時尚未部署，會回 502 / 404，只要不是 nginx config 錯誤即可）：

```bash
curl -skI https://nol.cs.nycu.edu.tw/meal-staging/health
curl -skI https://nol.cs.nycu.edu.tw/meal/health
```

## 4. Jenkins — Staging pipeline

In the Jenkins UI:

1. **New Item → Multibranch Pipeline**, name `mealorder-staging`.
2. **Branch Sources → GitHub**, point at the repo, credentials `github-app` (PAT with `repo` + `admin:repo_hook`).
3. **Behaviors → Filter by name**: include `main` only.
4. **Build Configuration → by Jenkinsfile**, script path: `Jenkinsfile.staging`.
5. Save.

## 5. Jenkins — Production pipeline

1. **New Item → Multibranch Pipeline**, name `mealorder-prod`.
2. **Branch Sources → GitHub**, point at the repo.
3. **Behaviors → Discover tags** (add the trait); remove the branches discovery trait (only tags).
4. **Behaviors → Filter by name (with regex)**: `^v\d+\.\d+\.\d+$`.
5. **Build Configuration → by Jenkinsfile**, script path: `Jenkinsfile.prod`.
6. Save.

> Note: Jenkins 在多分支建立後會先 scan 已存在的 tag — 第一次掃描時若 repo 上已經有 `v*.*.*` tag，pipeline 會立刻跑。Cutover 計畫是先確認 staging 通了再打第一個 tag，因此 scan 時應該沒有 tag。

## 6. Jenkins — Cleanup pipeline

1. **New Item → Pipeline**, name `mealorder-cleanup`.
2. **Pipeline → Pipeline script from SCM**, script path: `Jenkinsfile.cleanup`, branch `main`.
3. 不需額外 trigger（cron 由 Jenkinsfile 內部宣告）。

## 7. Jenkins-service mount requirements

The Jenkins container only needs one host mount: the Docker socket, so it can run `docker compose`
on the host daemon.

```yaml
# Minimum jenkins-service volume mounts (in docker-compose or systemd unit):
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
  - jenkins_home:/var/jenkins_home
```

There is **no** per-project source mount needed. Jenkins checks out each project into its own
ephemeral workspace (`$WORKSPACE`) and `docker compose` runs from there. Adding a new project means
writing a `Jenkinsfile` — the jenkins-service container does not need to be reconfigured or
restarted.

## 8. Jenkins credentials

| ID | Type | Used for |
|---|---|---|
| `gh-pat` | Secret text | `gh pr list` in sweep |
| `github-app` | GitHub App or PAT | Branch source |

## 9. Cutover from legacy `mealorder-main`

舊架構是 `mealorder-main` 直接吃 root path。新架構下 root 還給靜態網站，prod 走 `/meal/`。Cutover：

```bash
# 1. 確認新 staging 已通
curl -sk https://nol.cs.nycu.edu.tw/meal-staging/health

# 2. 從本機打第一個 tag（從 main 上某個 commit）
git tag v0.1.0
git push origin v0.1.0
# Jenkins mealorder-prod 會自動跑（workspace-based，無需 host 上有 source clone）

# 3. 等 prod 通了
curl -sk https://nol.cs.nycu.edu.tw/meal/health

# 4. 砍掉舊 stack（在 NOL host 上執行）
docker compose -p mealorder-main down -v --remove-orphans
```

## 10. End-to-end 驗證

開一個 throwaway branch、改一行、開 PR，確認：

- GitHub Actions `unit` + `integration` 綠
- Jenkins **不會**建立 preview stack（PR 階段不部署）
- Squash merge → Jenkins `mealorder-staging` 跑 → `https://nol.cs.nycu.edu.tw/meal-staging/health` 回 200
- `git tag v0.x.y && git push --tags` → Jenkins `mealorder-prod` 跑 → `https://nol.cs.nycu.edu.tw/meal/health` 回 200
- 再 merge 一次：staging 更新、prod 不變
- `docker compose ls` 應看到 `mealorder-staging`、`mealorder-prod`、以及 `caddy-preview-router`
- `https://nol.cs.nycu.edu.tw/` 原靜態網站不受影響
