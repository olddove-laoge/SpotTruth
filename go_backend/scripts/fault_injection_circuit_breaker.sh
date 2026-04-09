#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8080}"
TARGET_PATH="${2:-/api/v1/search}"
ROUNDS="${3:-8}"

if ! [[ "$ROUNDS" =~ ^[0-9]+$ ]]; then
  echo "[错误] 第三个参数 ROUNDS 必须是正整数"
  exit 1
fi

echo "[信息] 开始熔断故障注入"
echo "[信息] BASE_URL=$BASE_URL TARGET_PATH=$TARGET_PATH ROUNDS=$ROUNDS"
echo "[信息] 预期：上游异常时，前几次可能返回 5xx，随后出现 503 + GATEWAY_DEGRADED"

degraded_count=0
open_count=0

for i in $(seq 1 "$ROUNDS"); do
  tmp_file="$(mktemp)"
  request_id="fi-$(date +%s)-$i"

  http_code="$(curl -sS -o "$tmp_file" -w "%{http_code}" \
    -H "X-Request-ID: $request_id" \
    "$BASE_URL$TARGET_PATH" || true)"

  body="$(cat "$tmp_file")"
  rm -f "$tmp_file"

  degrade_reason=""
  if [[ "$body" == *"\"degrade_reason\""* ]]; then
    degrade_reason="$(echo "$body" | sed -n 's/.*"degrade_reason"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
  fi

  if [[ "$http_code" == "503" && "$body" == *"GATEWAY_DEGRADED"* ]]; then
    degraded_count=$((degraded_count + 1))
  fi
  if [[ "$degrade_reason" == "open_circuit" ]]; then
    open_count=$((open_count + 1))
  fi

  echo "[$i/$ROUNDS] code=$http_code request_id=$request_id degrade_reason=${degrade_reason:-none}"
done

echo "----------------------------------------"
echo "[统计] degraded_count=$degraded_count open_circuit_count=$open_count"

if [[ "$degraded_count" -gt 0 ]]; then
  echo "[结论] 已观测到熔断降级响应"
else
  echo "[结论] 未观测到熔断降级响应，请检查上游是否真的异常、CB配置是否启用"
fi
