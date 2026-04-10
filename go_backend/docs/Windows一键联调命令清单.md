# Windows 一键联调命令清单（含登录拿 token、带鉴权熔断）

更新时间：2026-04-10
适用范围：Go 网关 + Agent API 上游 + 鉴权 + 熔断验证

## 0. 当前完成度结论（忽略暂缓项）

### 0.1 网关整体完成度（当前口径）

1. 网关治理能力（限流、熔断、可观测、request_id）：已完成。
2. 最小登录鉴权（登录签发 Access Token + Bearer 校验 + 401/403 区分）：已完成。
3. 联调链路 Bearer 透传（web_app -> gateway）：已完成。

结论：按当前必须项口径，网关整体完成度可视为 100%。

### 0.2 登录鉴权完成度（当前口径）

已完成：
1. `POST /api/v1/auth/login` 可签发合法 Access Token。
2. 受保护接口通过 `Authorization: Bearer <token>` 访问。
3. Token 基础校验完整：角色、过期时间、issuer、签名密钥。
4. 错误语义区分完整：
   - `401`：未登录/Token 非法/Token 过期
   - `403`：角色不足

忽略暂缓项后，还缺什么：
1. 当前口径下无阻塞缺口。

说明（暂缓项，不计入本清单范围）：
1. Refresh Token 实现。
2. Token 黑名单与主动失效。
3. 审计日志落库与完整 RBAC 表模型。

## 1. Windows 是否能成功联调

可以。只要满足以下前提即可稳定联调：
1. 已安装 Go（建议 1.22+）。
2. 已安装 Python（建议 3.10+）并安装依赖。
3. 使用 PowerShell 执行本清单命令。
4. 使用 3 个 PowerShell 窗口分别启动上游、网关和压测命令。

## 2. 目录与变量（先在每个窗口执行）

~~~powershell
$RepoRoot = "D:\C_data\SpotTruth"
$GatewayDir = "$RepoRoot\go_backend"
$NewIdeaDir = "$RepoRoot\new_idea"
~~~

如果你的代码目录不是上面路径，请先改成实际路径。

## 3. 终端 A：启动上游 Agent API（5000）

~~~powershell
Set-Location $NewIdeaDir
python agent_api.py
~~~

保持该窗口不关闭。

## 4. 终端 B：启动网关（默认读取配置文件）

~~~powershell
Set-Location $GatewayDir
# 默认会自动读取 gateway.env（若存在 .env 则优先读取 .env）
go run ./cmd/api-gateway
~~~

如果你要显式指定配置文件：

~~~powershell
Set-Location $GatewayDir
$env:GATEWAY_CONFIG_FILE = "$GatewayDir\gateway.env"
go run ./cmd/api-gateway
~~~

保持该窗口不关闭。

## 5. 终端 C：登录拿 token（可直接复制）

~~~powershell
Set-Location $GatewayDir

$loginBody = @{
  account = "spottruth_user"
  password = "spottruth_user_123"
  login_type = "password"
} | ConvertTo-Json

$loginResp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8080/api/v1/auth/login" -ContentType "application/json" -Body $loginBody
$token = $loginResp.data.access_token

"token长度=$($token.Length)"
"token前缀=$($token.Substring(0,32))..."
~~~

## 6. 终端 C：带鉴权访问受保护接口（验证 Bearer）

~~~powershell
$headers = @{
  Authorization = "Bearer $token"
  "X-Request-ID" = "win-auth-check-1"
}

Invoke-WebRequest -Method Get -Uri "http://127.0.0.1:8080/api/v1/search" -Headers $headers -UseBasicParsing
~~~

说明：
1. 上游正常时，此请求不应返回 401。
2. 若返回 403，说明角色路由不匹配（可检查访问路径是否为 admin/internal 路由）。

## 7. 带鉴权熔断验证（推荐：重启网关后执行）

步骤：
1. 先停止终端 B 的网关进程（Ctrl+C）。
2. 在终端 B 重新启动网关，但把上游改为不可达地址 5999。

终端 B（重启命令）：

~~~powershell
Set-Location $GatewayDir
# 默认先吃 gateway.env，再覆盖你要调试的熔断参数
$env:UPSTREAM_BASE_URL = "http://127.0.0.1:5999"
$env:CB_ENABLED = "true"
$env:CB_MIN_REQUESTS = "2"
$env:CB_MAX_REQUESTS = "1"
$env:CB_ERROR_RATE_THRESHOLD = "50"
$env:CB_TIMEOUT = "8s"
$env:CB_INTERVAL = "20s"

go run ./cmd/api-gateway
~~~

终端 C（压测命令，带鉴权）：

~~~powershell
$headers = @{
  Authorization = "Bearer $token"
}

$degraded = 0
$openCircuit = 0
for ($i=1; $i -le 8; $i++) {
  $reqId = "win-fi-$i"
  $headers["X-Request-ID"] = $reqId
  try {
    $resp = Invoke-WebRequest -Method Get -Uri "http://127.0.0.1:8080/api/v1/search" -Headers $headers -UseBasicParsing -ErrorAction Stop
    $status = [int]$resp.StatusCode
    $body = $resp.Content
  } catch {
    $status = [int]$_.Exception.Response.StatusCode.value__
    $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    $body = $sr.ReadToEnd()
    $sr.Close()
  }

  $reason = "none"
  if ($body -match '"degrade_reason"\s*:\s*"([^"]+)"') {
    $reason = $Matches[1]
  }
  if ($status -eq 503 -and $body -like '*GATEWAY_DEGRADED*') {
    $degraded++
  }
  if ($reason -eq "open_circuit") {
    $openCircuit++
  }

  "[$i/8] code=$status request_id=$reqId degrade_reason=$reason"
}

"统计: degraded_count=$degraded open_circuit_count=$openCircuit"
~~~

预期：
1. 前几次通常 502。
2. 随后出现 503 且 `degrade_reason=open_circuit`。
3. 若出现 401，优先检查 token 是否过期，或网关签名参数是否一致。

## 8. 常见问题速查

1. 一直 401：
   - 确认请求里实际带了 `Authorization`。
   - 确认 `AUTH_SIGNING_KEY`、`AUTH_ISSUER` 与登录签发时一致。
2. 一直 200/404，不触发熔断：
   - 确认网关当前上游是 `http://127.0.0.1:5999`。
3. PowerShell 解析响应失败：
   - 使用本文中的 try/catch 读取错误响应体。

## 9. 可选：Git Bash 一条命令跑熔断脚本

如果你在 Windows 安装了 Git Bash，可直接在 Git Bash 里执行：

~~~bash
cd /d/D/C_data/SpotTruth/go_backend
bash scripts/fault_injection_circuit_breaker.sh http://127.0.0.1:8080 /api/v1/search 8 "Bearer $token"
~~~

其中 `$token` 请替换为你在 PowerShell 登录拿到的 token。
