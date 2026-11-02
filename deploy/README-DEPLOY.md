# 时光选彩 · Web 生产部署文档（HTTP 回环版）

> 部署方式：**Docker Compose 全家桶**（PostgreSQL 16 + FastAPI 后端 + Nginx 前端）
> 服务器：CentOS 7（Docker 20.10 已装，需补 compose 插件）
> 访问形态：**HTTP 回环** —— 项目 nginx 只监听 `127.0.0.1:8080`，由服务器上已有的上层 nginx 反向代理转发到该地址对外，本站不直接占用 80/443

---

## 0. 目标架构

```
用户浏览器
        │ HTTPS / HTTP（你的上层入口，如 www.aldus.cn）
        ▼
上层 nginx（服务器已有，占用 80/443 —— 由你稍后配置反代）
        ▼ proxy_pass http://127.0.0.1:8080
项目 nginx 容器（仅监听 127.0.0.1:8080，不对外）
├── 静态托管：/ → frontend H5 构建产物（uni-app build:h5）
└── 反向代理：/api → backend:8000（含 Agent SSE 流式，已关 buffering）
        ▼
FastAPI 后端容器（Uvicorn :8000，--workers 2）
├── 启动时自动 alembic upgrade head（数据库迁移）
├── 启动时幂等写入 7 彩种配置（games 表）
└── Agent 编排层（LLM key 未配置自动降级内置路由）
        ▼ asyncpg
PostgreSQL 16 容器（数据卷 pgdata 持久化）
```

三个服务共用一个 `docker-compose.prod.yml`，`docker compose up -d` 一次拉起。

---

## 1. 前提清单

| 项 | 状态 |
| --- | --- |
| 服务器 | CentOS 7（本部署已验证），Docker 20.10.14 已装 |
| compose 插件 | **未装，需安装**（第 2 节） |
| 端口 | 项目占用 127.0.0.1:8080（已确认空闲）；80/443 留给上层 nginx |
| 代码 | `frontend/src/api/request.js` 的 BASE_URL 已改为 `''`（同源，部署必需） |

> ⚠️ 部署前必改（**不改成会部署失败**）：`frontend/src/api/request.js` 第 5 行
> `const BASE_URL = 'http://127.0.0.1:8000'` 必须改为 `const BASE_URL = ''`（同源部署）。
> 原理：不改的话，访客浏览器会去请求**访客自己电脑**的 8000 端口，页面必然白屏。
> 本次部署已由助手在本机直接改好，勿回退。

---

## 2. 一次性服务器准备（root）

```bash
# ① 安装 Docker Compose v2 插件（Docker 20.10 需要）
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version          # 验证

# ② 建项目目录（本部署已执行）
mkdir -p /opt/shiguang

# ③ 放行本机回环访问（firewalld 默认允许 lo 流量，一般无需操作）
#    如需公网直连调试（不建议）：firewall-cmd --permanent --add-port=8080/tcp && firewall-cmd --reload
```

> Docker Hub 拉镜像失败时：见附录 A（配置镜像加速）。

---

## 3. 上传代码

本机打包并上传（已排除虚拟环境与 node_modules）：

```powershell
tar --exclude='backend/.venv' --exclude='frontend/node_modules' --exclude='.pytest_cache' --exclude='backend/.pytest_cache' -czf shiguang.tar.gz -C D:\Projects\PycharmProjects shiguang-lottery
scp shiguang.tar.gz root@www.aldus.cn:/tmp/
```

服务器解包到 /opt/shiguang：

```bash
tar -xzf /tmp/shiguang.tar.gz -C /tmp/
mv /tmp/shiguang-lottery/* /opt/shiguang/ && rm -rf /tmp/shiguang-lottery /tmp/shiguang.tar.gz
```

---

## 4. 配置生产参数

```bash
cd /opt/shiguang/deploy

# 生成生产配置
cp .env.prod .env
vi .env          # 必改：POSTGRES_PASSWORD 换成强密码（≥16 位混合字符）
                 # 可选：LLM_API_KEY 留空则 Agent 自动降级；填入则启用 LLM 对话
```

---

## 5. 一键部署

```bash
cd /opt/shiguang/deploy
bash deploy.sh
```

脚本自动完成 5 步：生成/校验 `.env` → 构建并启动三容器 → alembic 迁移（兜底）→ 写入 60 期演示历史（幂等）→ 健康检查。

---

## 6. 配置上层反向代理（你稍后要做的部分）

在服务器已有的 nginx 上新增一个 server 块（编辑 `/etc/nginx/conf.d/` 下对应配置文件或新建 `aldus-lottery.conf`），把域名/路径转发到项目服务：

```nginx
# /etc/nginx/conf.d/aldus-lottery.conf（示例，按你的实际配置调整）
server {
    listen 80;
    server_name www.aldus.cn;      # 你的对外域名

    location / {
        proxy_pass http://127.0.0.1:8080;      # 转发到项目 nginx 容器
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection        "";
        proxy_buffering off;                 # Agent SSE 流式需要
        proxy_read_timeout 300s;
    }
}
nginx -t && nginx -s reload
```

> 说明：整个站点（含 `/api`）整段转发到 127.0.0.1:8080 即可，前端与 API 保持同源，无需 CORS 配置。
> 已有 nginx 若已占用 80 的 server_name，请把本段并入你的配置，避免 `server_name` 冲突。

---

## 7. 验证清单

| 检查项 | 命令 / 操作 | 预期 |
| --- | --- | --- |
| 本机健康 | `curl http://127.0.0.1:8080/api/health` | `{"status":"ok","games":7}` |
| 本机页面 | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/` | `200` |
| 接口文档 | 浏览器/curl `http://127.0.0.1:8080/api/docs` | Swagger UI 正常 |
| 数据库数据 | `docker exec shiguang-postgres psql -U shiguang -d shiguang_lottery -c "select count(*) from games;"` | 7 |
| 容器状态 | `docker compose -f /opt/shiguang/deploy/docker-compose.prod.yml ps` | 3 个服务 `Up` |
| 对外访问 | 配置反代后访问 `http://www.aldus.cn` | 页面正常、可开奖回测 |

---

## 8. 日常运维

### 8.1 更新版本

```bash
cd /opt/shiguang
# 重新上传新代码到 /opt/shiguang（保持 deploy/.env 与数据卷不动）
cd deploy
docker compose -f docker-compose.prod.yml build backend nginx
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
```

### 8.2 看日志

```bash
docker compose -f /opt/shiguang/deploy/docker-compose.prod.yml logs -f backend   # 后端
docker compose -f /opt/shiguang/deploy/docker-compose.prod.yml logs -f nginx     # 前端/反代
```

### 8.3 备份数据库（建议每天）

```bash
mkdir -p /opt/shiguang/backups
docker exec shiguang-postgres pg_dump -U shiguang -d shiguang_lottery | gzip > /opt/shiguang/backups/sg_$(date +%F).sql.gz
```

### 8.4 回滚

```bash
cd /opt/shiguang/deploy
docker compose -f docker-compose.prod.yml down
# 重新放回旧代码后
bash deploy.sh
```

---

## 9. 常见问题排查

| 现象 | 原因 / 处理 |
| --- | --- |
| `docker compose` 命令不存在 | compose 插件未装：执行第 2 节①，确认 `docker compose version` 有输出 |
| 构建时报网络错误 | Docker Hub 不可达：附录 A 配镜像加速后重跑 |
| 页面白屏，控制台请求 `127.0.0.1:8000` | 第 1 节 BASE_URL 改回旧值了：确认 request.js 是 `const BASE_URL = ''` 并重 build 前端镜像 |
| `/api/health` 通但页面 404 | 前端构建产物路径不符：`docker exec shiguang-nginx ls /usr/share/nginx/html`，为空则调整 Dockerfile.frontend 的 COPY 路径（uni-app 默认 `dist/build/h5`） |
| 后端反复重启 | `docker compose logs backend`：看 DATABASE_URL 是否指向 `postgres:5432`（compose 服务名，不是 localhost） |
| 上层反代后页面能开但 SSE 对话卡住 | 上层 nginx 也要 `proxy_buffering off;` 与 `proxy_read_timeout 300s;`（见第 6 节模板） |
| postgres 一直 unhealthy，日志报 `Operation not permitted` | CentOS 7 老内核（3.10）上 Docker 默认 seccomp 会拦 postgres 写盘；compose 已给 postgres 配置 `security_opt: seccomp:unconfined`，勿删除 |
| backend 反复重启，日志报 `No module named 'greenlet'` | SQLAlchemy asyncio 需要 greenlet；依赖已改为 `SQLAlchemy[asyncio]`，重新 `docker compose build backend` 即可 |

---

## 10. 安全与合规提示

- 本项目为**纯模拟工具**（README 已声明"不涉及真实投注"）；对外公开时保留页面免责声明，勿引导真实购彩。
- 已把项目服务绑定 127.0.0.1:8080 不对外直连，避免绕过你的上层反代裸奔；数据库 5432、后端 8000 均未映射到宿主机。
- 部署后立即修改 `POSTGRES_PASSWORD`（deploy/.env），不要用默认口令。

---

## 附录 A：Docker Hub 不可达时配置镜像加速

```bash
mkdir -p /etc/docker
echo '{"registry-mirrors":["https://docker.m.daocloud.io"]}' > /etc/docker/daemon.json
systemctl restart docker
docker info | grep -i mirror
```

## 附录 B：1C2G 小内存机器调整

`deploy/Dockerfile.backend` 的启动命令把 `--workers 2` 改为 `--workers 1`：

```dockerfile
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
```

## 附录 C：CentOS 7 实战踩坑记录（2026-10 已全部解决并固化进部署包）

服务器实测环境：CentOS 7 (kernel 3.10) + Docker 20.10.14 + overlay2。遇到 4 个坑，均已修复并固化在 `deploy/` 文件中：

| # | 现象 | 根因 | 修复（已内置） |
| --- | --- | --- | --- |
| 1 | `docker compose` 命令不存在 | CentOS 7 的 Docker 20.10 默认不带 compose v2 插件 | 手动安装 cli 插件：`curl -SL ... -o /usr/local/lib/docker/cli-plugins/docker-compose` |
| 2 | postgres 写 `postmaster.pid` 报 `Operation not permitted`（即使 bind mount 到 ext4 也一样） | **3.10 内核 + Docker 默认 seccomp profile 拦截写盘系统调用**（与权限位、存储驱动无关） | postgres 服务配置 `security_opt: [seccomp:unconfined]`（该容器仅内网、未映射端口，风险可控） |
| 3 | postgres 容器内 chown 数据目录不生效 | Alpine 版 postgres 用户 uid 是 **70**（Debian 版才是 999） | `deploy.sh` 第一步预置 `chown 70:70 /opt/shiguang/pgdata` |
| 4 | backend 502，日志报 `No module named 'greenlet'` | 项目 `requirements.txt` 缺 asyncio 依赖 | 改为 `SQLAlchemy[asyncio]>=2.0.36`，重建后端镜像 |

> 若服务器将来升级内核（elrepo kernel-lt/ml）或换新机器（CentOS 7 已 EOL），第 2、3 项可逐步移除；建议迁移至 Rocky/AlmaLinux 9。

---

*部署包目录结构*

```
deploy/
├── README-DEPLOY.md        # 本文档
├── deploy.sh               # 一键部署脚本（bash deploy.sh）
├── docker-compose.prod.yml # 生产编排（postgres + backend + nginx，nginx 绑 127.0.0.1:8080）
├── Dockerfile.backend      # 后端镜像（pip 依赖 + alembic + uvicorn）
├── Dockerfile.frontend     # 前端镜像（node 构建 H5 → nginx 托管）
├── nginx.conf              # 站点配置（HTTP 回环 + 静态 + /api 反代 + SSE）
└── .env.prod               # 环境变量模板（复制为 .env 后修改）
```
