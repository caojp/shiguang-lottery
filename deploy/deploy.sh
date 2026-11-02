#!/usr/bin/env bash
# 时光选彩 · 一键部署脚本（HTTP 回环版：nginx 仅监听 127.0.0.1:8080，供上层反代转发）
# 用法：在 deploy/ 目录下执行  bash deploy.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "==> [1/6] 准备 postgres 数据目录（预置 70:70 所有权 = Alpine 镜像 postgres 用户）"
mkdir -p /opt/shiguang/pgdata
chown -R 70:70 /opt/shiguang/pgdata
chmod 700 /opt/shiguang/pgdata

echo "==> [2/6] 生成 .env"
if [ ! -f .env ]; then
  cp .env.prod .env
  echo "已生成 .env —— 请先编辑 .env 把 POSTGRES_PASSWORD 改为强密码，然后重新执行本脚本"
  exit 0
fi
grep -q "请改为强密码" .env && { echo "错误：.env 中的 POSTGRES_PASSWORD 仍是占位值，请先修改"; exit 1; }

echo "==> [3/6] 构建并启动全部服务（postgres / backend / nginx）"
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

echo "==> [4/6] 数据库迁移（backend 启动命令已自动执行，此处兜底）"
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head || true

echo "==> [5/6] 写入演示历史数据（幂等，可重复执行）"
docker compose -f docker-compose.prod.yml exec -T backend python scripts/fetch_history.py --seed-demo --demo-periods 60 || true

echo "==> [6/6] 健康检查"
sleep 8
curl -fsS http://127.0.0.1:8080/api/health && echo ""
curl -s -o /dev/null -w "前端页面 HTTP 状态码：%{http_code}\n" http://127.0.0.1:8080/

echo "=========================================="
echo "✅ 部署完成：服务已监听 127.0.0.1:8080（仅本机可访问）"
echo "   在上层 nginx 中反代到 http://127.0.0.1:8080 即可对外提供服务"
echo "=========================================="
