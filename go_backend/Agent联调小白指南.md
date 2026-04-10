# Agent 联调小白指南（只看 Agent + Go 网关，不看前端）

补充：
1. 如果你在 Windows 环境联调，建议直接使用 [go_backend/docs/Windows一键联调命令清单.md](docs/Windows一键联调命令清单.md)。
2. 该清单已包含：登录拿 token、Bearer 传递、带鉴权熔断验证的可复制命令。


## 0. 先理解一件事（非常重要）

当前代码里：
1. Agent 主入口是 [new_idea/run.py](../new_idea/run.py)。
2. 联调用 API 入口是 [new_idea/agent_api.py](../new_idea/agent_api.py)。
3. Agent 核心实现位于 [new_idea/agent](../new_idea/agent) 目录。

第六阶段完成后，联调主链路已经改为“优先穿网关”：
1. 联调接口里的 Python 工具调用统一走 Go 网关入口（默认 `http://127.0.0.1:8080`）。
2. 网关再转发到上游服务（默认 `http://127.0.0.1:5000`）。
3. 响应会带回 request_id，便于日志与指标追踪。

这意味着：
1. 现在默认联调模式是“穿网关联调”，不再推荐旁路直连。
2. 本文按“最小可跑通”给出步骤，适合小白直接照做。

---

## 1. 准备 3 个终端

建议开 3 个终端窗口，分别做：
1. 终端 A：启动 Python 上游服务（给 Go 网关转发用）。
2. 终端 B：启动 Go 网关。
3. 终端 C：启动 Agent。

---

## 2. 第一次环境准备（只做一次）

在项目根目录执行：

~~~bash
cd /Users/yllmis/go_projects/SpotTruth

# 可选：创建虚拟环境（你如果已经有 conda 环境，可跳过）
python3 -m venv .venv
source .venv/bin/activate

# 安装 Python 依赖（项目已有）
pip install -r requirements.txt
pip install -r new_idea/requirements.txt

# Agent 运行常用依赖（new_idea/requirements.txt 未完整覆盖时补齐）
pip install selenium openai numpy requests
~~~

说明：
1. Agent 调用模型时依赖 torch/transformers/peft（已在 new_idea/requirements.txt 中）。
2. Agent 还会用到 selenium 和 openai，建议手动补装一次，避免缺包报错。

---

## 3. 启动上游 Python 服务（终端 A）

Go 网关默认把流量转发到 127.0.0.1:5000，所以先起一个 Python 服务监听 5000。

可以直接运行：

~~~bash
cd /Users/yllmis/go_projects/SpotTruth
python web_app/app.py
~~~

如果你有自己的 Flask 服务，也可以替换，只要保证监听地址和网关配置一致。

---

## 4. 启动 Go 网关（终端 B）

~~~bash
cd /Users/yllmis/go_projects/SpotTruth/go_backend
cp .env.example .env
go run ./cmd/api-gateway
~~~

启动后，另开一个终端执行自检：

~~~bash
curl -sS http://127.0.0.1:8080/healthz
curl -sS http://127.0.0.1:8080/readyz
curl -sS http://127.0.0.1:8080/metrics | head -n 20
curl -sS http://127.0.0.1:8080/metrics/json
~~~

常见现象：
1. healthz 正常返回 200，说明网关进程活着。
2. readyz 返回 503，通常是上游健康探测路径不匹配。

快速修复 readyz 503：
1. 打开 [go_backend/.env](.env)。
2. 把 UPSTREAM_HEALTH_PATH 从 /healthz 改为 /（如果你的上游服务没有 /healthz）。
3. 重启 Go 网关后再测 readyz。

---

## 5. 启动 Agent（终端 C）

### 5.1 先改 2 个路径（macOS 必看）

在 [new_idea/config.py](../new_idea/config.py) 里，默认是 Windows 路径：
1. driver_path = E 盘路径
2. profile_dir = C 盘路径

请改成你本机路径，例如：

~~~python
driver_path = "/Users/你的用户名/tools/msedgedriver"
profile_dir = "/Users/你的用户名/.spottruth_edge_profile"
~~~

如果不用 Edge，也可以后续改为 Chrome 驱动版本，但那是下一步优化，这份小白文档先按现有实现走。

### 5.2 启动命令

~~~bash
cd /Users/yllmis/go_projects/SpotTruth/new_idea
python run.py
~~~

启动后它会依次打开：淘宝 -> 小红书 -> 黑猫投诉，并提示你手动登录。

登录完按回车，进入聊天模式。

---

## 6. Agent + 网关并行联调（不看前端）

你可以按下面顺序做一次最小联调：

1. 在 Agent 里输入一个商品请求，例如：
   - 蓝月亮 洗衣液怎么样
2. 观察 Agent 终端：
   - 是否出现“调用工具”日志。
   - 是否返回分析结论。
3. 同时在另一个终端查看网关状态：

~~~bash
curl -sS http://127.0.0.1:8080/healthz
curl -sS http://127.0.0.1:8080/readyz
curl -sS http://127.0.0.1:8080/metrics | head -n 20
curl -sS http://127.0.0.1:8080/metrics/json
~~~

重点看 metrics/json 里的字段：
1. requests_total
2. in_flight_requests
3. status_2xx_total / status_4xx_total / status_5xx_total
4. limiter_rejected_total

---

## 7. 联调是否成功的判定标准

满足以下条件就算跑通：
1. Agent 可启动，且能进入聊天循环。
2. Agent 输入商品问题后，有工具调用和分析输出。
3. Go 网关 healthz 为 200。
4. Go 网关 readyz 可按你的上游配置返回正常状态。
5. metrics 接口可返回 JSON 且包含关键计数项。

备注：
1. `/metrics` 现在是 Prometheus 文本格式，用于可视化看板采集。
2. `/metrics/json` 是兼容联调调试端点。

---

## 8. 常见报错排查（小白速查）

1. 报错：No module named selenium/openai
   - 处理：重新执行依赖安装命令。

2. 报错：msedgedriver 不存在
   - 处理：检查 [new_idea/config.py](../new_idea/config.py) 里的 driver_path 是否是你本机真实路径。

3. 报错：readyz 一直 503
   - 处理：检查上游服务是否启动；确认 [go_backend/.env](.env) 的 UPSTREAM_HEALTH_PATH 是否和上游路由一致。

4. 报错：Agent 启动后卡在登录
   - 处理：这是正常的手动登录步骤，完成页面登录后回终端按回车即可继续。

---

## 9. 下一步（可选）

如果你下一步想做“全量 Agent CLI 工作流穿网关”（包括 `new_idea/run.py` 入口下 `new_idea/agent` 包的工具调用链），建议把工具调用层进一步抽象为统一 HTTP 客户端，并默认指向网关入口。当前阶段已完成联调主链路穿网关，可满足演示与排障。

---

## 10. 如何演示可视化面板（录视频版）

目标：不用 Docker，直接在本机演示网关指标变化。

### 10.1 安装 Prometheus + Grafana（只做一次）

~~~bash
brew install prometheus grafana
~~~

### 10.2 启动 Prometheus

~~~bash
cd /Users/yllmis/go_projects/SpotTruth/go_backend
prometheus --config.file=observability/prometheus.yml
~~~

默认访问：`http://127.0.0.1:9090`

### 10.3 启动 Grafana

~~~bash
grafana server --homepath /opt/homebrew/opt/grafana/share/grafana
~~~

默认访问：`http://127.0.0.1:3000`
默认账号密码：`admin/admin`

### 10.4 Grafana 里配置数据源

1. 登录 Grafana。
2. 添加 Prometheus 数据源。
3. URL 填 `http://127.0.0.1:9090`。
4. Save & test。

### 10.5 推荐演示的 6 个查询

1. `spottruth_requests_total`
2. `spottruth_in_flight_requests`
3. `spottruth_http_status_total`
4. `spottruth_limiter_rejected_total`
5. `spottruth_circuit_degraded_total`
6. `spottruth_circuit_state_value`

### 10.6 录视频建议动作

1. 先展示 `healthz/readyz/metrics` 正常。
2. 执行一次请求洪峰或故障注入，触发图表变化。
3. 展示限流与熔断曲线变化，再回到稳定状态。

可用命令：

~~~bash
cd /Users/yllmis/go_projects/SpotTruth/go_backend
bash scripts/fault_injection_circuit_breaker.sh http://127.0.0.1:8080 /api/v1/search 8
~~~
