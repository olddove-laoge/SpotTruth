# SpotTruth Token 鉴权设计方案

## 一、背景

当前 SpotTruth 已具备 Go API 网关基础能力，包括反向代理、健康检查、请求日志、并发限制与优雅停机。随着后续用户查询、后台任务、社区版登录态和管理员运维能力逐步接入，网关侧需要建立统一的 Token 鉴权机制，用于明确“谁可以访问什么能力”。

本方案面向当前 SpotTruth 的实际阶段，目标是在不推翻现有 `net/http` 网关结构的前提下，落地一版轻量、可演进、可扩展到完整 RBAC 的 Token 鉴权体系。

## 二、设计目标

1. 在当前 Go 网关基础上增加统一身份校验能力。
2. 区分普通用户、管理员、系统任务三类调用方。
3. 将查询能力与底层工具调用能力解耦。
4. 与异步任务队列、管理后台、社区版用户系统兼容。
5. 为后续限流、审计、黑名单、刷新令牌等能力预留扩展空间。

## 三、核心原则

1. 普通用户可以发起查询请求，但不能直接操作底层爬虫或重分析工具。
2. 管理员拥有高权限运维能力，但所有敏感操作必须可审计。
3. 系统任务通过受控方式调用内部工具，不直接暴露给前端。
4. 用户提需求，系统异步补数；不把高成本工具调用绑定到用户同步请求中。
5. 第一阶段先做最小可用方案，后续再逐步扩展为完整 RBAC。

## 四、角色模型

### 4.1 普通用户（user）

允许：

1. 查询商品分析结果。
2. 查看自己触发的任务状态。
3. 管理个人收藏、浏览历史等用户侧数据。

禁止：

1. 直接调用爬虫工具。
2. 强制重跑任务。
3. 修改系统执行参数。

### 4.2 管理员（admin）

允许：

1. 强制触发抓取与重分析。
2. 重试失败任务。
3. 调整部分任务执行参数。
4. 查看执行日志与错误原因。

约束：

1. 所有高权限动作必须写入审计日志。
2. 管理员接口不能默认暴露给普通前端页面。

### 4.3 系统任务（system / worker）

允许：

1. 从队列中消费任务。
2. 调用内部抓取与分析工具。
3. 回写任务状态、分析结果、缓存数据。

约束：

1. 仅通过服务内网或受控服务凭证访问。
2. 不直接面向浏览器和普通客户端发放。

## 五、Token 设计

### 5.1 Token 类型

1. Access Token
   - 用于访问业务接口。
   - 建议有效期：15 到 60 分钟。
2. Refresh Token
   - 用于刷新 Access Token。
   - 建议有效期：7 到 30 天。
   - 当前阶段可作为第二步实现，不强制首版落地。

### 5.2 Claims 设计

Access Token 建议包含以下字段：

```json
{
  "sub": "123",
  "role": "user",
  "username": "demo_user",
  "jti": "uuid",
  "iat": 1710000000,
  "exp": 1710001800,
  "iss": "spottruth-gateway"
}
```

字段说明：

1. `sub`：用户唯一标识。
2. `role`：角色，候选值为 `user`、`admin`、`system`。
3. `username`：可选字段，用于日志与展示。
4. `jti`：Token 唯一 ID，便于后续黑名单与主动失效。
5. `iat`：签发时间。
6. `exp`：过期时间。
7. `iss`：签发者标识，建议固定为 `spottruth-gateway`。

### 5.3 签名算法

1. 第一阶段推荐 `HS256`
   - 实现简单，适合当前单体/轻量服务阶段。
2. 后续如演进到多服务或多环境统一鉴权，可升级为 `RS256`。

### 5.4 传输方式

统一采用：

`Authorization: Bearer <token>`

## 六、鉴权链路设计

### 6.1 中间件执行顺序

推荐顺序：

1. `RequestLogger`
2. `AuthMiddleware`
3. `RequireRole`
4. `ConcurrencyLimiter`
5. `Proxy or Local Handler`

### 6.2 这样排序的原因

1. 先记录请求，保证所有访问都有日志留痕。
2. 再做身份校验，尽早拒绝未授权请求。
3. 再按角色做权限判断，明确 user/admin/system 的边界。
4. 最后才进入限流和业务处理，减少无效资源占用。

### 6.3 返回语义

1. `401 Unauthorized`
   - 未携带 Token。
   - Token 非法。
   - Token 已过期。
2. `403 Forbidden`
   - 身份有效，但角色不足。

## 七、路由分层建议

当前 SpotTruth 网关除 `/healthz` 外，其余路径默认全部代理到 Flask。为引入鉴权，建议逐步拆分为以下类型：

### 7.1 公共路由

1. `GET /healthz`
2. `POST /api/v1/auth/login`
3. `POST /api/v1/auth/refresh`

### 7.2 用户路由

1. `GET /api/v1/search`
2. `GET /api/v1/jobs/{id}`

### 7.3 管理路由

1. `POST /api/v1/admin/jobs/rebuild`
2. `POST /api/v1/admin/jobs/retry/{id}`

### 7.4 内部路由

1. `POST /internal/v1/worker/report`

说明：

1. 当前尚未迁移的业务路由，仍可保持代理到 Flask。
2. 新增的 Go 原生接口优先放在 `/api/v1/*` 下，便于统一治理。

## 八、统一接口约定

### 8.1 基础约定

1. 所有新接口统一使用 JSON 作为请求与响应格式。
2. 时间字段统一使用 RFC3339 格式，例如 `2026-03-12T10:00:00+08:00`。
3. 业务接口统一挂载在 `/api/v1` 下，内部回调接口挂载在 `/internal/v1` 下。
4. 受保护接口统一通过 `Authorization: Bearer <token>` 传递身份信息。
5. 网关应为每个请求注入 `X-Request-ID`，便于日志、审计与问题排查。

### 8.2 成功响应结构

```json
{
   "code": "OK",
   "message": "success",
   "data": {},
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:00:00+08:00"
}
```

字段说明：

1. `code`：业务状态码，成功固定为 `OK`。
2. `message`：简要说明。
3. `data`：具体业务载荷。
4. `request_id`：请求唯一标识。
5. `timestamp`：网关响应时间。

### 8.3 失败响应结构

```json
{
   "code": "AUTH_TOKEN_INVALID",
   "message": "token 非法或已过期",
   "error": {
      "type": "unauthorized",
      "details": "signature validation failed"
   },
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:00:00+08:00"
}
```

建议首版统一以下错误码：

1. `AUTH_TOKEN_MISSING`
2. `AUTH_TOKEN_INVALID`
3. `AUTH_PERMISSION_DENIED`
4. `REQUEST_INVALID`
5. `RESOURCE_NOT_FOUND`
6. `JOB_NOT_READY`
7. `INTERNAL_ERROR`
8. `SERVICE_BUSY`

## 九、认证接口设计

### 9.1 登录接口

接口：`POST /api/v1/auth/login`

权限：公共接口

用途：校验用户身份并签发 Access Token；当前阶段可先接管理员后台账号或社区版用户表。

请求体：

```json
{
   "account": "admin",
   "password": "123456",
   "login_type": "password"
}
```

字段说明：

1. `account`：用户名、邮箱或手机号，首版建议先支持用户名。
2. `password`：明文口令，仅在 HTTPS 下传输。
3. `login_type`：登录方式，首版固定为 `password`，为后续验证码或 OAuth 预留扩展位。

成功响应：`200 OK`

```json
{
   "code": "OK",
   "message": "success",
   "data": {
      "access_token": "<jwt>",
      "refresh_token": "<refresh-jwt>",
      "token_type": "Bearer",
      "expires_in": 1800,
      "user": {
         "id": "u_1001",
         "username": "admin",
         "role": "admin"
      }
   },
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:00:00+08:00"
}
```

失败语义：

1. `400 Bad Request`：请求字段缺失。
2. `401 Unauthorized`：账号或密码错误。
3. `429 Too Many Requests`：登录尝试过于频繁。

### 9.2 刷新令牌接口

接口：`POST /api/v1/auth/refresh`

权限：公共接口，但必须携带合法 Refresh Token

请求体：

```json
{
   "refresh_token": "<refresh-jwt>"
}
```

成功响应：`200 OK`

```json
{
   "code": "OK",
   "message": "success",
   "data": {
      "access_token": "<new-jwt>",
      "token_type": "Bearer",
      "expires_in": 1800
   },
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:05:00+08:00"
}
```

失败语义：

1. `400 Bad Request`：请求体为空或格式错误。
2. `401 Unauthorized`：Refresh Token 无效、过期或已失效。

### 9.3 当前用户信息接口

接口：`GET /api/v1/auth/profile`

权限：`user` / `admin` / `system`

用途：前端在刷新页面后恢复登录态；后台页面可据此判断当前角色。

成功响应：`200 OK`

```json
{
   "code": "OK",
   "message": "success",
   "data": {
      "id": "u_1001",
      "username": "demo_user",
      "role": "user"
   },
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:10:00+08:00"
}
```

## 十、用户查询与任务接口设计

### 10.1 发起搜索接口

接口：`GET /api/v1/search`

权限：`user` / `admin`

查询参数：

1. `keyword`：必填，用户输入的商品或主题关键词。
2. `platform`：可选，平台标识，如 `taobao`、`jd`、`xhs`。
3. `scene`：可选，业务场景，如 `comment_analysis`、`product_compare`。
4. `force_refresh`：可选，仅管理员可为 `true`，普通用户强制传入也会按 `false` 处理。

返回策略：

1. 命中缓存或数据库时，直接返回结果。
2. 未命中时，返回任务已创建状态，而不是同步阻塞等待抓取完成。

命中结果响应：`200 OK`

```json
{
   "code": "OK",
   "message": "success",
   "data": {
      "hit": true,
      "source": "cache",
      "keyword": "苹果手机",
      "summary": {
         "positive_ratio": 0.72,
         "negative_ratio": 0.12,
         "neutral_ratio": 0.16
      },
      "result_id": "analysis_20260312_001"
   },
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:20:00+08:00"
}
```

未命中并创建任务响应：`202 Accepted`

```json
{
   "code": "JOB_ACCEPTED",
   "message": "结果不存在，已创建后台任务",
   "data": {
      "hit": false,
      "job_id": "job_20260312_001",
      "status": "queued",
      "polling_url": "/api/v1/jobs/job_20260312_001"
   },
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:20:00+08:00"
}
```

### 10.2 查询任务详情接口

接口：`GET /api/v1/jobs/{id}`

权限：

1. 普通用户只能查看自己创建的任务。
2. 管理员可以查看全部任务。

成功响应：`200 OK`

```json
{
   "code": "OK",
   "message": "success",
   "data": {
      "job_id": "job_20260312_001",
      "status": "running",
      "progress": 60,
      "keyword": "苹果手机",
      "created_at": "2026-03-12T10:20:00+08:00",
      "updated_at": "2026-03-12T10:21:10+08:00",
      "result_id": ""
   },
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:21:10+08:00"
}
```

状态说明：

1. `queued`：已入队，等待消费。
2. `running`：Worker 正在执行。
3. `succeeded`：已完成，可结合 `result_id` 拉取结果。
4. `failed`：执行失败，可由管理员触发重试。

### 10.3 获取结果详情接口

接口：`GET /api/v1/results/{id}`

权限：`user` / `admin`

用途：当搜索返回 `result_id`，或任务执行完成后，前端按结果 ID 拉取完整分析数据。

成功响应：`200 OK`

```json
{
   "code": "OK",
   "message": "success",
   "data": {
      "result_id": "analysis_20260312_001",
      "keyword": "苹果手机",
      "platform": "taobao",
      "summary": {
         "positive_ratio": 0.72,
         "negative_ratio": 0.12,
         "neutral_ratio": 0.16
      },
      "top_keywords": ["续航", "拍照", "价格"],
      "generated_at": "2026-03-12T10:25:00+08:00"
   },
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:25:01+08:00"
}
```

## 十一、管理接口设计

### 11.1 强制重建任务接口

接口：`POST /api/v1/admin/jobs/rebuild`

权限：仅 `admin`

用途：管理员绕过现有缓存与结果，强制重新抓取并分析。

请求体：

```json
{
   "keyword": "苹果手机",
   "platform": "taobao",
   "scene": "comment_analysis",
   "reason": "数据过旧，需人工刷新"
}
```

成功响应：`202 Accepted`

```json
{
   "code": "JOB_ACCEPTED",
   "message": "已创建强制重建任务",
   "data": {
      "job_id": "job_20260312_101",
      "status": "queued"
   },
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:30:00+08:00"
}
```

补充要求：

1. 请求必须落审计日志。
2. `reason` 建议设为必填，避免管理员无理由触发高成本任务。

### 11.2 重试失败任务接口

接口：`POST /api/v1/admin/jobs/retry/{id}`

权限：仅 `admin`

用途：对失败任务做人工重试。

请求体：

```json
{
   "reason": "上游超时已恢复，重新执行"
}
```

成功响应：`202 Accepted`

```json
{
   "code": "JOB_ACCEPTED",
   "message": "任务已重新入队",
   "data": {
      "job_id": "job_20260312_001",
      "status": "queued"
   },
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:35:00+08:00"
}
```

### 11.3 查看任务执行日志接口

接口：`GET /api/v1/admin/jobs/{id}/logs`

权限：仅 `admin`

用途：查看任务执行轨迹、错误堆栈与重试记录，支撑排障与运营。

成功响应：`200 OK`

```json
{
   "code": "OK",
   "message": "success",
   "data": {
      "job_id": "job_20260312_001",
      "logs": [
         {
            "time": "2026-03-12T10:20:05+08:00",
            "level": "info",
            "message": "job picked by worker"
         },
         {
            "time": "2026-03-12T10:20:40+08:00",
            "level": "error",
            "message": "upstream timeout"
         }
      ]
   },
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:36:00+08:00"
}
```

## 十二、内部 Worker 接口设计

### 12.1 Worker 回写任务状态接口

接口：`POST /internal/v1/worker/report`

权限：仅 `system`

用途：Worker 执行完抓取、分析或缓存回填后，向网关或任务服务回写最新状态。

请求体：

```json
{
   "job_id": "job_20260312_001",
   "status": "succeeded",
   "progress": 100,
   "result_id": "analysis_20260312_001",
   "error_message": ""
}
```

字段说明：

1. `job_id`：任务唯一标识。
2. `status`：`running`、`succeeded`、`failed` 之一。
3. `progress`：0 到 100 的进度值。
4. `result_id`：成功时写入。
5. `error_message`：失败时写入。

成功响应：`200 OK`

```json
{
   "code": "OK",
   "message": "success",
   "data": {
      "job_id": "job_20260312_001",
      "accepted": true
   },
   "request_id": "req_01HXYZ",
   "timestamp": "2026-03-12T10:40:00+08:00"
}
```

安全要求：

1. 不对浏览器开放。
2. 除 JWT `system` Token 外，也可首版先采用单独的 `INTERNAL_WORKER_TOKEN` 做服务间校验。
3. 建议配合来源 IP 白名单或内网访问控制。

## 十三、用户请求与后台任务的协作方式

### 8.1 查询未命中时的处理原则

普通用户不是直接调用底层工具，而是触发受控任务。

链路如下：

1. 用户查询商品，例如“苹果手机评价推荐”。
2. 系统优先查缓存。
3. 缓存未命中后查数据库。
4. 若数据库也没有结果，则创建后台任务（`jobs`）并投递到队列（Redis / MQ）。
5. Worker 以 `system` 身份异步调用抓取与分析工具。
6. 任务完成后回写数据库与缓存。
7. 前端显示“请稍候”，并轮询任务状态或接收通知。

### 8.2 这样设计的价值

1. 避免用户请求被长耗时爬虫任务阻塞。
2. 避免普通用户直接触发高成本底层工具。
3. 便于做重试、幂等、失败兜底和任务审计。

## 十四、配置项建议

在现有网关配置基础上，建议新增：

1. `JWT_SIGNING_KEY`
   - Token 签名密钥。
2. `JWT_ACCESS_TOKEN_TTL`
   - Access Token 有效期，建议 `30m`。
3. `JWT_REFRESH_TOKEN_TTL`
   - Refresh Token 有效期，建议 `7d`。
4. `JWT_ISSUER`
   - 建议为 `spottruth-gateway`。
5. `INTERNAL_WORKER_TOKEN`
   - 内部 Worker 调用受控接口时使用的服务凭证。

## 十五、目录结构建议

```text
go_backend/
├── internal/
│   ├── auth/
│   │   ├── token.go          # Token生成与解析
│   │   ├── claims.go         # 自定义Claims
│   │   ├── middleware.go     # 鉴权中间件
│   │   ├── context.go        # 上下文注入用户信息
│   │   └── role.go           # 角色判断辅助函数
│   ├── handler/
│   │   ├── auth.go           # login/refresh/profile
│   │   └── job.go            # 查询任务状态
│   ├── queue/
│   │   └── job.go            # 后台任务结构定义
│   └── ...
```

## 十六、第一阶段最小可交付版本（MVP）

第一阶段仅落地最必要能力：

1. JWT Access Token。
2. 三类角色：`user`、`admin`、`system`。
3. 用户查询接口与管理接口的基础权限控制。
4. 标准化 `401/403` 返回语义。
5. 单元测试覆盖以下关键路径：
   - 无 Token -> `401`
   - 非法 Token -> `401`
   - 角色不足 -> `403`
   - 合法 Token 放行 -> `200`

## 十七、预期效果

1. 安全性提升：阻断未授权工具调用，降低滥用风险。
2. 稳定性提升：高成本操作统一进入队列，避免接口被重任务拖垮。
3. 成本可控：按角色与配额治理请求，减少重复抓取与重复分析。
4. 可运维：管理员可以强制刷新、重试失败任务，系统任务自动化执行。
5. 可审计：关键接口调用与高权限操作可追踪，便于后续运营与合规管理。

## 十八、后续演进方向

1. 增加 Refresh Token。
2. 引入 Redis 黑名单与主动失效机制。
3. 增加管理员审计日志落库。
4. 与限流、熔断、监控指标打通。
5. 从轻量角色控制逐步演进到完整 RBAC（用户-角色-权限）模型。

## 十九、结论

SpotTruth 当前最合适的方案，不是直接移植完整 RBAC 项目，而是在现有 `net/http` 网关上先实现一版轻量 Token 鉴权。

这版方案的重点不在于一次性做全，而在于先把以下三个问题解决：

1. 谁能访问接口。
2. 谁能触发高成本任务。
3. 谁能调用内部工具链。

在此基础上，再逐步接入用户系统、异步任务、管理后台和更完整的权限体系，改动成本最低，演进路径也最清晰。