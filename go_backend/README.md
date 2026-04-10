
# SpotTruth Go 后端

本目录为 SpotTruth 项目的 Go 后端框架。

## API 网关（已实现）

该网关作为现有 Flask Web 应用的反向代理入口。

### 主要特性
- `GET /healthz` 健康检查接口
- `GET /readyz` 就绪检查接口（主动探测上游）
- `GET /metrics` Prometheus 标准指标接口
- `GET /metrics/json` 网关指标 JSON 兼容接口
- 其余所有路由均反向代理到 Flask 应用
- 结构化请求日志
- 网关与代理层双重超时保护（请求读写、空闲连接、上游响应）
- 分桶限流（按 API Key/IP）与并发限流双重保护
- 熔断与降级保护（open/half-open/closed 状态迁移 + 结构化降级响应）
- JWT 鉴权主链路已接入（支持公共白名单路由）
- 优雅停机
- 基于环境变量的配置

### 鉴权白名单路由
- `/healthz`
- `/readyz`
- `/metrics`
- `/metrics/json`
- `/api/v1/auth/login`
- `/api/v1/auth/refresh`

### 最小登录签发（MVP）
1. 获取 Access Token（默认静态账号）

```bash
curl -sS -X POST http://127.0.0.1:8080/api/v1/auth/login \
	-H "Content-Type: application/json" \
	-d '{"account":"spottruth_user","password":"spottruth_user_123","login_type":"password"}'
```

2. 受保护接口携带 Bearer Token

```bash
curl -sS http://127.0.0.1:8080/api/v1/search \
	-H "Authorization: Bearer <access_token>" \
	-H "X-Request-ID: demo-auth-1"
```

说明：
- `401` 表示 token 缺失/非法/过期。
- `403` 表示 token 有效但角色权限不足。
- 若要修改默认账号，请在 `.env` 设置 `AUTH_USER_*`、`AUTH_ADMIN_*`、`AUTH_SYSTEM_*`。

### 快速启动

```bash
cd go_backend
cp .env.example .env
# 如有需要，可在 shell 中导出 .env 里的变量
go run ./cmd/api-gateway
```

默认行为：
- 网关监听 `:8080`
- 所有请求转发到 `http://127.0.0.1:5000`

### 生产环境建议
- 建议在入口层（如 Nginx/ALB/API Gateway）配置 TLS 与 WAF
- 可在 `internal/middleware` 目录添加限流、认证等中间件
- 当流量规模提升时，可将不同领域 API 拆分为独立 Go 服务

### 网关方案表与后续计划
- 最新版本：`go_backend/docs/设计与可扩展性说明.md` 第八节（更新于 2026-04-09）
- 当前重点：第六阶段已完成（Agent 联调主链路已穿网关），网关层建设已收口
- 方案2实施与验收：`go_backend/docs/第四阶段实施步骤.md`
- 方案2回归清单：`go_backend/docs/第四阶段回归清单.md`
- 方案5实施进展：`go_backend/docs/第五阶段实施步骤.md`
- 方案6实施进展：`go_backend/docs/第六阶段实施步骤.md`
- 可视化演示指南（录视频）：`go_backend/docs/可视化面板演示指南.md`
- 网关层设计总览：`go_backend/docs/网关层设计总览.md`
- 小白快速联调指引（仅 Agent + Go 网关）：`go_backend/Agent联调小白指南.md`

### 网关层作用总结
- 统一入口：把鉴权、限流、熔断、可观测能力统一下沉到网关，业务服务专注领域逻辑。
- 稳定性兜底：并发限流 + 分桶限流 + 熔断降级形成多层防护，避免上游抖动扩散。
- 可追踪联调：每个请求带 `X-Request-ID`，配合日志与 `/metrics` 可快速定位链路问题。
- 演示友好：支持 Prometheus + Grafana，本地即可完成录屏级可视化展示。

### 测试与联调

1. Go 网关自检

```bash
cd go_backend
go test ./...
go build ./...
go vet ./...
```

2. 启动 Go 网关

```bash
cd go_backend
go run ./cmd/api-gateway
```

3. 本地接口检查（建议另开终端）

```bash
curl -sS http://127.0.0.1:8080/healthz
curl -sS http://127.0.0.1:8080/readyz
curl -sS http://127.0.0.1:8080/metrics
curl -sS http://127.0.0.1:8080/metrics/json
```

4. 固定联调回归链路（gateway health -> python tool -> integration test）

```bash
# 1) gateway health
curl -sS "http://127.0.0.1:5001/api/gateway/health?gateway_url=http://127.0.0.1:8080"

# 2) python tool
curl -sS -X POST "http://127.0.0.1:5001/api/python/tool-test" \
	-H "Content-Type: application/json" \
	-d '{"product_name":"苹果手机"}'

# 3) integration test
curl -sS -X POST "http://127.0.0.1:5001/api/integration/test" \
	-H "Content-Type: application/json" \
	-d '{"gateway_url":"http://127.0.0.1:8080","product_name":"苹果手机"}'
```

说明：
- `5001` 为 `web_app` 示例端口，请按你本地实际端口替换。
- 第 4 步要求 `web_app` 服务已启动。

5. 熔断故障注入回归（第四阶段）

```bash
cd go_backend
bash scripts/fault_injection_circuit_breaker.sh http://127.0.0.1:8080 /api/v1/search 8
```

说明：
- 执行前请确保上游服务处于异常状态（例如停掉 Flask），用于验证 open-circuit 降级响应。
- 结果解读见 `go_backend/docs/第四阶段回归清单.md`。

---

## 代码规范

1. 目录结构遵循 Go 标准分层（cmd/internal/pkg）
2. 变量、函数、注释、提交信息均使用中文（如无特殊要求）
3. 重要接口、模块需配套注释说明
4. 所有配置项均支持通过环境变量覆盖
5. 提交信息格式：
	- feat: 新功能
	- fix: 修复问题
	- docs: 文档/注释
	- refactor: 重构
	- chore: 其他

---

## 贡献说明

1. 新增功能请先在 docs/ 目录补充设计文档
2. 代码合并前请确保 go build/go test 均通过
3. 重要变更需在 PR/提交说明中详细描述影响范围
