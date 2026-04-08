# 完整测试流程 - 预期输出示例

## 📋 准备工作

### 环境检查
```bash
# 检查KIMI_API_KEY
$env:KIMI_API_KEY
# 预期输出: sk-xxxxxxxxxxxxx
```

---

## 终端1: 启动 Agent API 服务

```bash
cd D:\C_data\SpotTruth\new_idea
python agent_api.py
```

### 预期输出
```
============================================================
🤖 避雷真 Agent API 服务
============================================================

📋 使用方式:
   终端A: python agent_api.py
   终端B: go run ./cmd/api-gateway
   终端C: python run.py

🔗 API端点:
   健康检查: http://127.0.0.1:5000/healthz
   评论分析: POST http://127.0.0.1:5000/api/analyze
   品类分类: POST http://127.0.0.1:5000/api/classify

============================================================

2024-01-08 15:30:00,123 - Agent - INFO - 正在初始化 Agent API 服务...
2024-01-08 15:30:02,456 - httpx - INFO - HTTP Request: GET https://api.moonshot.cn/v1/models "HTTP/1.1 200 OK"
2024-01-08 15:30:02,789 - Agent - INFO - ✅ Agent API 服务初始化完成
 * Running on http://0.0.0.0:5000
 * 按 Ctrl+C 退出
```

---

## 终端2: 启动 Go 网关

```bash
cd D:\C_data\SpotTruth\go_backend
go run ./cmd/api-gateway
```

### 预期输出
```
2024/01/08 15:30:10 INFO Starting API Gateway...
2024/01/08 15:30:10 INFO Upstream URL: http://127.0.0.1:5000
2024/01/08 15:30:10 INFO Health check path: /healthz
2024/01/08 15:30:10 INFO Rate limit: 100 req/s
2024/01/08 15:30:10 INFO Server listening on :8080
```

---

## 测试1: Agent API 健康检查

```bash
curl http://127.0.0.1:5000/healthz
```

### 预期输出
```json
{
  "status": "ok",
  "service": "agent-api",
  "version": "2.0.0",
  "components": {
    "llm": "initialized",
    "analyzer": "initialized",
    "classifier": "initialized"
  }
}
```

---

## 测试2: 网关健康检查

```bash
curl http://127.0.0.1:8080/healthz
```

### 预期输出
```json
{
  "status": "ok"
}
```

---

## 测试3: 网关就绪检查（会检查上游）

```bash
curl http://127.0.0.1:8080/readyz
```

### 预期输出（成功）
```json
{
  "status": "ready",
  "upstream": "http://127.0.0.1:5000",
  "upstream_status": "healthy"
}
```

### 如果返回503
```json
{
  "status": "not_ready",
  "error": "upstream unhealthy"
}
```
**解决**: 检查终端1的Agent API是否正常运行

---

## 测试4: Agent API - 品类分类

```bash
curl -X POST http://127.0.0.1:5000/api/classify `
  -H "Content-Type: application/json" `
  -d "{\"product_name\": \"德芙巧克力\"}"
```

### 预期输出
```json
{
  "product_name": "德芙巧克力",
  "category": "dairy",
  "keywords_match": true
}
```

---

## 测试5: Agent API - 评论分析

```bash
curl -X POST http://127.0.0.1:5000/api/analyze `
  -H "Content-Type: application/json" `
  -d "{
    \"comments\": [
      \"真的很好吃，推荐购买\",
      \"一般般，没有想象中好\",
      \"呵呵，真是太好了呢，甜到掉牙\",
      \"包装精美，物流快\",
      \"这个质量，真是没谁了（狗头）\"
    ],
    \"product_name\": \"德芙巧克力\"
  }"
```

### 预期输出
```json
{
  "product_name": "德芙巧克力",
  "category": "dairy",
  "statistics": {
    "total": 5,
    "positive_count": 3,
    "negative_count": 2,
    "sarcasm_count": 2,
    "positive_rate": 0.6,
    "negative_rate": 0.4
  },
  "results": [
    {
      "text": "真的很好吃，推荐购买",
      "sentiment": "positive",
      "is_sarcasm": false,
      "confidence": 0.9234,
      "sarcasm_confidence": 0,
      "llm_analysis": null
    },
    {
      "text": "一般般，没有想象中好",
      "sentiment": "negative",
      "is_sarcasm": false,
      "confidence": 0.8567,
      "sarcasm_confidence": 0,
      "llm_analysis": null
    },
    {
      "text": "呵呵，真是太好了呢，甜到掉牙",
      "sentiment": "negative",
      "is_sarcasm": true,
      "confidence": 0.9123,
      "sarcasm_confidence": 0.8234,
      "llm_analysis": "该评论表面夸赞但实际表达不满，\"甜到掉牙\"暗示过甜不好吃，判定为负面评价"
    },
    {
      "text": "包装精美，物流快",
      "sentiment": "positive",
      "is_sarcasm": false,
      "confidence": 0.9456,
      "sarcasm_confidence": 0,
      "llm_analysis": null
    },
    {
      "text": "这个质量，真是没谁了（狗头）",
      "sentiment": "negative",
      "is_sarcasm": true,
      "confidence": 0.8876,
      "sarcasm_confidence": 0.7567,
      "llm_analysis": "\"没谁了\"配合狗头表情为反讽，实际表达对质量的不满，判定为负面评价"
    }
  ]
}
```

**关键点验证**:
- `is_sarcasm: true` 的应该是第3条和第5条
- 这两条虽然字面像好评，但 `sentiment` 应该是 `negative`
- 应该有 `llm_analysis` 字段解释判断理由

---

## 测试6: 网关监控指标

```bash
curl http://127.0.0.1:8080/metrics
```

### 预期输出
```json
{
  "requests_total": 12,
  "requests_per_second": 0.5,
  "in_flight_requests": 1,
  "status_2xx_total": 10,
  "status_4xx_total": 0,
  "status_5xx_total": 0,
  "limiter_rejected_total": 0,
  "upstream_health": {
    "healthy": true,
    "last_check": "2024-01-08T15:35:00Z"
  }
}
```

---

## 终端3: 启动 Agent 客户端

```bash
cd D:\C_data\SpotTruth\new_idea
python run.py
```

### 预期输出
```
检查环境...
✅ KIMI_API_KEY 已设置

============================================================
🤖 避雷真 - 商品口碑分析Agent
═══════════════════════════════════════════════════════════════

您好！我是避雷真，一个专业的商品口碑分析助手。
...
═══════════════════════════════════════════════════════════════

初始化Agent...
2024-01-08 15:35:10,123 - Agent - INFO - KimiClient初始化完成，模型: moonshot-v1-8k
2024-01-08 15:35:12,456 - Agent - INFO - 讽刺检测模型(TOSPrompt)加载成功
2024-01-08 15:35:15,789 - Agent - INFO - ✅ Agent初始化完成

请先登录以下平台：
1. 按回车打开淘宝并登录...
```

---

## 终端3: Agent 交互测试

### 用户输入
```
👤 您: 分析 德芙 巧克力
```

### 预期输出（简化版）
```
2024-01-08 15:36:00,123 - Agent - INFO - 解析意图: {'intent': 'analyze', 'brand': '德芙', 'product': '巧克力', ...}
2024-01-08 15:36:00,456 - Agent - INFO - 开始分析商品: 德芙 巧克力
2024-01-08 15:36:00,789 - Agent - INFO - 🚀 开始分析: 德芙 巧克力
2024-01-08 15:36:01,012 - Agent - INFO - [1/6] 搜索商品: 德芙 巧克力
  ✅ 找到商品: 德芙巧克力碗装丝滑牛奶巧克力...
2024-01-08 15:36:05,345 - Agent - INFO - [2/6] 获取淘宝评论...
  ✅ 获取到 100 条评论
2024-01-08 15:36:10,678 - Agent - INFO - [3/6] 分析评论（讽刺检测+情感分析）...
  自动判断品类: dairy
  ✅ 分析完成: 好评率85%, 讽刺5条
...

🤖 避雷真:

📦 德芙 巧克力
──────────────────────────────────────────────────
💰 价格: ¥29.9
🏪 店铺: 德芙官方旗舰店
📊 评论分析:
   总评论: 100条
   好评率: 85%
   差评率: 15%
   ⚠️ 疑似虚假好评: 5条
📝 分析总结:
   ## 综合评价
   德芙巧克力整体评价较好，好评率达到85%...
   ## 主要问题点
   - 部分用户反映产品过甜
   ...
💡 购买建议:
   ## 购买建议
   推荐
   ## 适合人群
   喜欢甜食的消费者...
```

---

## 测试7: 上下文测试

### 用户输入序列
```
👤 您: 分析 德芙 巧克力
🤖 避雷真: [返回分析结果]

👤 您: 黑猫投诉怎么样
```

### 预期行为
Agent应该理解"黑猫投诉"是指"德芙巧克力的黑猫投诉"，而不是问"什么是黑猫投诉"。

### 预期输出
```
🤖 避雷真:
📦 德芙 巧克力
...
⚠️ 黑猫投诉: 10条
[黑猫投诉分析结果...]
```

---

## 测试8: 总结查询测试

### 用户输入
```
👤 您: 综上所述，你的购买建议是什么
```

### 预期行为
Agent应该直接返回当前商品的总结，而不是重新分析或询问"您指什么商品"。

---

## ✅ 测试通过清单

| 测试项 | 预期结果 | 实际结果 |
|--------|---------|---------|
| Agent API启动 | 成功，监听5000 | ⬜ |
| Go网关启动 | 成功，监听8080 | ⬜ |
| Agent客户端启动 | 成功，进入登录 | ⬜ |
| /healthz (API) | 200 OK | ⬜ |
| /healthz (网关) | 200 OK | ⬜ |
| /readyz (网关) | 200 OK | ⬜ |
| /metrics (网关) | 返回JSON | ⬜ |
| 品类分类API | 正确返回品类 | ⬜ |
| 评论分析API | 正确识别讽刺 | ⬜ |
| Agent完整分析 | 返回分析报告 | ⬜ |
| 上下文理解 | 正确理解"它"指代 | ⬜ |
| 总结查询 | 直接返回结果 | ⬜ |

---

## ❌ 常见问题

### 问题1: Agent API 启动失败
```
ImportError: cannot import name 'xxx' from 'agent'
```
**解决**: 确保在 `new_idea` 目录下运行，且 `agent/__init__.py` 存在

### 问题2: 503 Service Unavailable
```
{"status": "not_ready"}
```
**解决**: 
1. 检查Agent API是否启动
2. 或修改 `go_backend/.env`:
   ```
   UPSTREAM_HEALTH_PATH=/
   ```

### 问题3: KIMI_API_KEY 错误
```
ToolError: KIMI_API_KEY未设置
```
**解决**:
```bash
$env:KIMI_API_KEY="sk-你的密钥"
```

### 问题4: 端口被占用
```
Address already in use: 5000
```
**解决**:
```bash
# 查找占用5000的进程
netstat -ano | findstr :5000
# 结束进程
taskkill /PID <进程ID> /F
```
