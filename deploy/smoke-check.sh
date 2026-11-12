#!/bin/bash
set -e
echo "==> health"; curl -s http://127.0.0.1:8080/api/health; echo
REG=$(curl -s -X POST http://127.0.0.1:8080/api/auth/register -H 'Content-Type: application/json' -d '{"username":"deploycheck","password":"deploy12345"}')
echo "REG=$REG"
TOKEN=$(echo "$REG" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
[ -n "$TOKEN" ] || { echo "NO_TOKEN"; exit 1; }
echo "==> me"; curl -s http://127.0.0.1:8080/api/auth/me -H "Authorization: Bearer $TOKEN"; echo
echo "==> save"; curl -s -X POST http://127.0.0.1:8080/api/picks/save -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" -d '{"game_code":"ssq","mode":"random","count":1,"cost":2,"tickets":[{"digits":"01 05 12 18 23 30 + 07","zones":{"red":[1,5,12,18,23,30],"blue":[7]}}],"draw":{"zones":{"red":[2,11,17,24,29,33],"blue":[8]}},"win":0}'; echo
echo "==> mine count"; curl -s "http://127.0.0.1:8080/api/picks/mine?limit=5" -H "Authorization: Bearer $TOKEN" | grep -c game_code
echo "==> front"; curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/; echo
echo "==> containers"; docker ps --format '{{.Names}} {{.Status}}' | grep shiguang
docker exec shiguang-postgres psql -U shiguang -d shiguang_lottery -c "DELETE FROM user_picks WHERE user_id=(SELECT id FROM users WHERE username='deploycheck'); DELETE FROM users WHERE username='deploycheck';" >/dev/null && echo "==> CLEANED"
