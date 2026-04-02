
# SpotTruth Go 后端

本目录为 SpotTruth 项目的 Go 后端框架。

## API 网关（已实现）

该网关作为现有 Flask Web 应用的反向代理入口。

### 主要特性
- `GET /healthz` 健康检查接口
- 其余所有路由均反向代理到 Flask 应用
- 结构化请求日志
- 网关与代理层双重超时保护（请求读写、空闲连接、上游响应）
- JWT 鉴权主链路已接入（支持公共白名单路由）
- 优雅停机
- 基于环境变量的配置

### 鉴权白名单路由
- `/healthz`
- `/api/v1/auth/login`
- `/api/v1/auth/refresh`

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
- 最新版本：`go_backend/docs/设计与可扩展性说明.md` 第八节（更新于 2026-04-01）
- 当前重点：补齐超时保护、接入鉴权主链路、新增 readiness 探针

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
