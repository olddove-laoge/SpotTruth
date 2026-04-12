# Windows 比赛彩排与压测指南

更新时间：2026-04-12  
适用范围：Windows 联调机（前端 + Go 网关 + Agent API）

## 1. 彩排目标

1. 确认前端请求确实经过 Go 网关。
2. 确认主链路可用：登录 -> 业务接口 -> 结果返回。
3. 运行压测并保留原始数据，同时自动生成图表。
4. 在 Prometheus/Grafana 中展示可观测指标变化。

## 2. 启动顺序（建议 3 个 PowerShell 窗口）

### 终端 A：启动 Agent API（上游）

```powershell
cd D:\C_data\SpotTruth\new_idea
python agent_api.py
```

### 终端 B：启动 Go 网关

```powershell
cd D:\C_data\SpotTruth\go_backend
go run ./cmd/api-gateway
```

### 终端 C：启动前端

```powershell
cd D:\C_data\SpotTruth\frontend
npm run dev
```

前端默认地址：`http://127.0.0.1:3000`

## 3. 如何确认前端消息经过网关

做以下三步即可确认。

### 3.1 网关日志确认

在终端 B 观察日志，前端发送消息时应出现类似路径：

1. `/api/v1/auth/login`
2. `/api/parse_intent`
3. `/api/classify`
4. `/api/analyze`

如果这些请求只在终端 B（网关）可见，说明前端请求已穿网关。

### 3.2 指标增量确认

在发送消息前后各执行一次：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/metrics/json" -Method Get | ConvertTo-Json -Depth 10
```

重点看：

1. `requests_total`
2. `status_2xx_total`
3. `status_4xx_total`
4. `status_5xx_total`

### 3.3 前端代理配置确认（一次性）

前端开发代理将 `/api` 与 `/crawler` 都转发到 `127.0.0.1:8080`。  
对应文件：`frontend/vite.config.ts`

## 4. 自动压测与出图

本仓库已提供脚本：

1. `go_backend/scripts/run_gateway_loadtest.ps1`（执行压测并汇总）
2. `go_backend/scripts/plot_hey_results.py`（把 CSV 原始数据转图）
3. `go_backend/scripts/generate_loadtest_report_page.py`（读取 `combined.summary.json` 自动生成一页图文结论）

### 4.1 安装依赖

#### 安装 hey

```powershell
go install github.com/rakyll/hey@latest
```

确保 `hey` 在 PATH 中可执行。

#### 安装 Python 绘图库

```powershell
pip install matplotlib
```

### 4.2 执行压测

```powershell
cd D:\C_data\SpotTruth\go_backend
powershell -ExecutionPolicy Bypass -File .\scripts\run_gateway_loadtest.ps1
```

也可以自定义参数，例如：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_gateway_loadtest.ps1 `
  -BaseUrl "http://127.0.0.1:8080" `
  -HealthRequests 5000 -HealthConcurrency 120 `
  -LoginRequests 2000 -LoginConcurrency 80 `
  -ClassifyRequests 1500 -ClassifyConcurrency 60 `
  -ClassifyProductName "苹果手机"
```

### 4.3 结果产物说明

脚本会在 `go_backend/observability/loadtest_results/<时间戳>/` 下生成：

1. `*.raw.txt`：hey 原始摘要输出（保留原始压测信息）。
2. `*.raw.csv`：hey 每请求明细（保留原始采样数据）。
3. `metrics.before.json` / `metrics.after.json`：压测前后网关指标快照。
4. `charts/*.png`：自动生成图表（延迟直方图、时序散点图、状态码柱状图）。
5. `charts/combined.summary.json`：机器可读汇总。
6. `charts/combined.summary.md`：可直接贴到汇报材料的摘要。
7. `loadtest_report.html`：自动生成的一页比赛汇报模板页（图文结论）。

### 4.4 一页汇报模板页使用

压测脚本已自动生成 `loadtest_report.html`，可直接浏览器打开。  
建议把以下内容作为答辩展示主页面：

1. 顶部 KPI（总请求量、成功率、5xx 增量）。
2. 一页结论（最佳吞吐、最高 P99、限流/熔断增量）。
3. 场景明细卡片（每个场景的延迟、吞吐、状态码与图表）。

## 5. 监控大屏查看（Prometheus + Grafana）

## 5.1 Prometheus

使用仓库配置启动：

```powershell
cd D:\C_data\SpotTruth\go_backend
prometheus.exe --config.file=observability/prometheus.yml
```

默认地址：`http://127.0.0.1:9090`

## 5.2 Grafana

如前端占用 3000，建议 Grafana 改为 3001：

```powershell
$env:GF_SERVER_HTTP_PORT="3001"
grafana-server.exe
```

打开：`http://127.0.0.1:3001`

## 5.3 推荐面板查询

```promql
spottruth_requests_total
```

```promql
spottruth_in_flight_requests
```

```promql
spottruth_http_status_total
```

```promql
spottruth_limiter_rejected_total
```

```promql
spottruth_circuit_degraded_total
```

```promql
spottruth_circuit_state_value
```

## 6. 比赛现场建议流程（5-8 分钟）

1. 启动三服务（上游、网关、前端）。
2. 前端发起一次分析请求。
3. 展示网关日志中的请求路径与 request_id。
4. 展示 `/metrics/json` 计数增长。
5. 执行压测脚本并展示生成的图表与摘要。
6. 打开 Grafana 面板展示实时曲线。

## 7. 常见问题

1. `401`：先检查是否已登录（`/api/v1/auth/login` 成功）。
2. `readyz` 不通过：检查上游 `agent_api.py` 是否监听在 5000。
3. 无法出图：检查 `matplotlib` 是否已安装。
4. 找不到 `hey`：重新执行安装并确认 PATH。
