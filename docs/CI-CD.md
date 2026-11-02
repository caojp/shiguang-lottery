# 时光选彩 · GitHub CI/CD 接入说明

> 目标：**push 到 `main` 即自动构建镜像并部署到 www.aldus.cn 服务器（/opt/shiguang）**。
> 与手动部署（`deploy/docker-compose.prod.yml`，服务器本地构建）并存，两套编排不要混用。

## 1. 工作流架构（.github/workflows/ci-cd.yml）

```
push main / tag v*
   │
   ├─ ci       （ubuntu-latest）：Python 3.11 + pytest 冒烟测试 → Node 20 + 前端 build:h5
   │
   ├─ images   （依赖 ci）：backend / frontend 两个镜像 → buildx 构建 → 推 GHCR
   │           镜像名：ghcr.io/<owner>/<repo>-backend:<sha>  /  -frontend:<sha>（另有 :latest）
   │
   └─ deploy   （依赖 images，仅 main，environment: production）：
                SSH 上服务器 → 上传 docker-compose.cd.yml + nginx.conf
                → pull 镜像 → up -d --remove-orphans → alembic 兜底 → 健康检查（60×3s）
                → 失败自动输出 backend 最近日志并 exit 1
```

## 2. GitHub 仓库与本地配置

- 仓库：`git@github.com:caojp/shiguang-lottery.git`（或 https://github.com/caojp/shiguang-lottery）
- 本机已就绪：git 仓库（main）、已 merge origin/main、工作树干净、领先 origin 2 个提交待 push
- **部署专用密钥**已生成并装到服务器：
  - 私钥：`C:\Users\caojianping\.ssh\shiguang_deploy_ed25519`（内容用于 secrets.SERVER_SSH_KEY，勿外泄）
  - 公钥：已追加到服务器 `/root/.ssh/authorized_keys`（`shiguang-cicd-deploy@aldus`，已验证可登录）
- 本机 push 需 GitHub 可达（SSH 22 或 443）。若当前网络不通，可配置代理或稍后推送：
  `git push -u origin main`

## 3. 首次运行前需在 GitHub 配置（Settings → Secrets and variables → Actions）

### Secrets（仓库级即可；如用 environment: production 需同时配在该 environment 下）

| Secret | 必填 | 说明 | 值来源 |
| --- | --- | --- | --- |
| `SERVER_HOST` | 是 | 服务器地址 | `www.aldus.cn` |
| `SERVER_USER` | 是 | SSH 用户 | `root` |
| `SERVER_SSH_KEY` | 是 | 部署私钥全文 | `C:\Users\caojianping\.ssh\shiguang_deploy_ed25519` 内容 |
| `SERVER_PORT` | 否 | SSH 端口，默认 22 | `22` |
| `GHCR_USER` | 否 | GHCR 登录用户，默认取 github.actor | 一般无需填 |
| `GHCR_PAT` | 否 | 仅**私有**仓库且 GHCR 包为私有时需要（`packages: write` 的 PAT）；公开仓库可留空 | — |

### Variables

| Variable | 默认值 | 说明 |
| --- | --- | --- |
| `DEPLOY_PATH` | `/opt/shiguang/deploy` | 服务器编排目录 |
| `HEALTH_URL` | `http://127.0.0.1:8080/api/health` | 部署后健康检查地址 |

## 4. 服务器前置检查（已完成 ✓）

- [x] `/opt/shiguang/deploy/.env` 存在（含 POSTGRES_PASSWORD）
- [x] 服务器可访问 `ghcr.io`（已实测，registry 响应正常）
- [x] postgres 数据卷 `/opt/shiguang/pgdata`（bind mount，uid 70）
- [x] postgres `seccomp:unconfined`（CentOS 7 老内核必需，cd.yml 已内置）
- [ ] 首次部署由 workflow 自动上传 `docker-compose.cd.yml` + `nginx.conf`（无需手工）

## 5. 验证与排查

- 推送后到 **GitHub 仓库 → Actions** 看 `CI/CD` 运行；三个 job 依次 ci → images → deploy
- 常见失败：
  - `deploy` 报 `Required secret ... not defined` → 按第 3 节补 secrets
  - `deploy` 健康检查失败 → 输出会打印 backend 最近日志；先查 `.env` 是否存在、postgres 是否 healthy
  - `images` 推送失败（私有仓库）→ 补 `GHCR_PAT`；公开仓库无需
- 服务器手工验证：`curl http://127.0.0.1:8080/api/health` 应返回 `{"status":"ok","games":7}`

## 6. 回滚

- **代码回滚**：`git push --force-with-lease origin <旧sha>:main`（谨慎）或直接 push 新提交修复
- **服务器快速回滚**：若新镜像起不来，改回手动部署编排（服务器本地构建，不依赖网络拉镜像）：

```bash
cd /opt/shiguang/deploy
docker compose -f docker-compose.prod.yml build backend nginx
docker compose -f docker-compose.prod.yml up -d
# 注意：prod.yml 与 cd.yml 容器名相同，切换前先 down 另一套
```

## 7. 与手动部署的关系

| | 手动（prod.yml） | CI/CD（cd.yml） |
| --- | --- | --- |
| 镜像来源 | 服务器本地 docker build | GHCR（GitHub Actions 构建推送） |
| 触发 | `bash deploy.sh` / 手工 | push main / tag / workflow_dispatch |
| 适用 | 临时修复、无 GitHub 时 | 日常迭代、自动发布 |

> 两者共用同一套容器名（shiguang-postgres/backend/nginx）与数据卷，切换编排时先 `down` 再 `up`，避免容器重名冲突。
