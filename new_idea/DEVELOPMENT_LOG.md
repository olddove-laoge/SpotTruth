# SpotTruth 项目开发日志

## 项目信息
- **对话时间**：2025-03-06 ~ 2025-03-07
- **项目目标**：构建基于MCP/LoRA的多品类商品评论分析系统

---

## 一、项目背景

### 1.1 原项目问题
原项目SpotTruth是一个淘宝商品评价分析平台，存在以下问题：
- 技术含量低（Selenium爬虫+SnowNLP）
- 简历无亮点
- 情感分析准确率低（无法识别阴阳怪气评价）

### 1.2 优化目标
- 提升技术含量：使用LoRA微调 + MCP架构
- 提升准确率：领域适应训练
- 支持阴阳怪气检测

---

## 二、数据概况

### 2.1 原始数据
- **位置**：`new_idea/data/train.csv`
- **总量**：62774条评论
- **品类**：10个原始品类 → 合并为9个

### 2.2 品类合并
| 原始品类 | 合并后 | 数据量 |
|----------|--------|--------|
| 书籍 | book | 3851 |
| 平板 | tablet | ~10000 |
| 手机 + 计算机 | electronics | 6315 |
| 水果 | fruit | ~10000 |
| 洗发水 | shampoo | ~10000 |
| 奶制品 | dairy | ~10000 |
| 衣服 | clothing | 3992 |
| 热水器 | water_heater | ~10000 |
| 酒店 | hotel | 575 |

### 2.3 数据格式
- **标签**：0=差评，1=好评（二分类）
- **训练集/验证集**：8:2划分

---

## 三、完成的工作

### Step 1: 数据确认 ✅
- 确认数据位置和格式
- 分析品类分布

### Step 2: 品类判断模块 ✅
- **文件**：`step2_category_classifier.py`
- **实现**：名称关键词匹配 + Kimi LLM兜底
- **API**：sk-NxnJvWVKw9cun9Y80gjfQp7PyWR9rOMwy9VH2aNU28xOdxcr

```python
# 品类关键词映射
CATEGORY_KEYWORDS = {
    "book": ["书", "图书", "小说", "教材", "绘本"],
    "tablet": ["平板", "ipad", "平板电脑", "surface"],
    "electronics": ["手机", "iphone", "安卓", "电脑", "笔记本", "计算机", "电子产品"],
    ...
}
```

### Step 3: 数据预处理 ✅
- **文件**：`step3_data_preprocessor.py`
- **功能**：
  - 文本清洗（去除URL、特殊字符）
  - 划分训练集/验证集(8:2)
- **输出**：`data/{category}/train.json` 和 `dev.json`

### Step 4: LoRA微调训练 ✅
- **基础模型**：hfl/chinese-roberta-wwm-ext
- **LoRA参数**：r=8, lora_alpha=16, lora_dropout=0.1
- **训练结果**：

| 品类 | 训练数据 | 验证准确率 | 状态 |
|------|----------|------------|------|
| book | 3081 | ~98% | ✅ 已训练 |
| tablet | ~8000 | - | ✅ 已训练 |
| electronics | 5052 | - | ✅ 已训练 |
| fruit | ~8000 | - | ✅ 已训练 |
| shampoo | ~8000 | - | ✅ 已训练 |
| dairy | ~8000 | - | ✅ 已训练 |
| clothing | 3194 | - | ✅ 已训练 |
| water_heater | ~8000 | - | ✅ 已训练 |
| hotel | 460 | - | ✅ 已训练 |

- **模型保存位置**：`output/lora/{category}`

### Step 5-8: 框架搭建 ⚠️
- **step5_sarcasm_detector.py**：阴阳怪气检测（框架）
- **step6_mcp_tools.py**：MCP工具注册（框架）
- **step7_router.py**：路由逻辑
- **step8_integration_test.py**：集成测试

---

## 四、测试验证

### 4.1 LoRA效果对比（全部9个类别）
测试脚本：`test_book_model.py`, `test_all_models.py`

**测试结果汇总**：

| 品类 | 好评准确率 | 差评准确率 | 中评倾向 | 状态 |
|------|------------|------------|----------|------|
| **Book** | 20% ❌ | 100% | 全部→负面 | ⚠️ 需优化 |
| **Tablet** | 100% ✅ | 100% | 全部→正面 | ✅ |
| **Electronics** | 100% ✅ | 100% | 混合(3正2负) | ✅ |
| **Fruit** | 100% ✅ | 100% | 全部→正面 | ✅ |
| **Shampoo** | 100% ✅ | 100% | 全部→正面 | ✅ |
| **Dairy** | 100% ✅ | 100% | 全部→正面 | ✅ |
| **Clothing** | 100% ✅ | 100% | 全部→正面 | ✅ |
| **Water Heater** | 100% ✅ | 100% | 全部→正面 | ✅ |
| **Hotel** | 100% ✅ | 100% | 全部→正面 | ✅ |

**关键发现**：
- **8/9类别表现优秀**：100%正负分类准确率
- **Book模型严重问题**：只有20%好评准确率，所有评论被错分为差评
- **中性评论倾向**：除Book外，大多数中性评论倾向于被分类为正面

### 4.2 发现的问题
1. **Book模型训练不完整**：可能因断电仅完成2个epoch，导致分类头未充分训练
2. **短文本效果差**：训练数据多为长文本（150-190字），短文本判断不准确
3. **中评难以识别**：二分类模型将中评归入好评或差评
4. **阴阳怪气问题**：需要独立模块解决

---

## 五、技术细节

### 5.1 模型架构
```
基座模型: hfl/chinese-roberta-wwm-ext (102M参数)
    ↓
LoRA适配器: r=8, lora_alpha=16 (297K参数, 0.29%)
    ↓
分类头: 2或3分类
```

### 5.2 依赖环境
- Python 3.12
- PyTorch (GPU)
- Transformers
- PEFT (LoRA)
- Kimi API (Moonshot)

### 5.3 关键文件
| 文件 | 说明 |
|------|------|
| `step2_category_classifier.py` | 品类判断 |
| `step3_data_preprocessor.py` | 数据预处理 |
| `step4_train_lora.py` | 分类训练 |
| `test_all_models.py` | 批量测试 |

---

## 六、讽刺/阴阳怪气检测模块（Step 5 扩展）

### 6.1 数据收集

#### 6.1.1 NTU讽刺语料库
- **来源**：台湾大学Plurk讽刺语料库
- **文件**：`sarcasm_detection/data/NTU_Irony_Corpus.txt`
- **格式**：XML风格标注，包含`<message>`、`<ironic>`、`<context>`、`<rhetoric>`标签
- **数量**：1012条（处理后1005条）
- **处理**：
  - 繁体→简体转换
  - 提取纯文本
  - 标记为"讽刺"(label=1)

#### 6.1.2 SemEval 2018讽刺数据集
- **来源**：SemEval 2018 Task 3
- **文件**：`sarcasm_detection/data/SemEval2018-T3-train-taskA.txt`
- **说明**：英文讽刺数据集，可用于对比实验

#### 6.1.3 正常评论数据
- **来源**：11个品类评论数据
- **数量**：1100条（每品类100条，50好评+50差评）
- **格式**：label=0（正常评论）

#### 6.1.3 训练数据集
- **文件**：`sarcasm_detection/data/sarcasm_train.json`
- **总量**：2105条
- **分布**：
  - 阴阳怪气：1005条
  - 正常评论：1100条

### 6.2 模型实现

#### 6.2.1 MIARN模型（基于论文）
参考论文：Reasoning with Sarcasm by Reading In-between (Yi Tay et al. ACL 2018)

**核心思想**：
- 检测"前后情感矛盾式"的反讽
- 如："I love being ignored"（love和ignored情感矛盾）

**模型架构**：
```
1. 预训练词嵌入 → 复用RoBERTa词向量
2. BiLSTM编码 → 双向序列表示
3. 词对attention → 任意词对计算相似度矩阵
4. max-pooling + softmax → 句内attention表示
5. 拼接 → LSTM表示 + 句内attention
6. 分类 → 讽刺/正常
```

**关键文件**：
- `sarcasm_detection/miarn_sarcasm_detector.py` - MIARN模型实现
- `sarcasm_detection/train_sarcasm.py` - LoRA训练脚本
- `sarcasm_detection/attention_sarcasm_detector.py` - 基于注意力的检测

#### 6.2.2 可解释性
- 输出高注意力词对
- 展示模型认为"对着干"的词
- 示例：
```
文本: 很好又失眠了!!
预测: 阴阳怪气/讽刺 (置信度: 75.3%)
高注意力词对:
  '好' <-> '眠': 0.8523
  '很' <-> '好': 0.7234
```

### 6.3 文件结构
```
sarcasm_detection/
├── data/
│   ├── NTU_Irony_Corpus.txt    # 原始语料
│   ├── irony_corpus.json         # 处理后讽刺数据
│   ├── sarcasm_train.json         # 训练数据
│   └── train.json / dev.json     # 划分后数据
├── output/                        # 模型输出
├── preprocess_ntu_corpus.py       # 语料预处理
├── prepare_sarcasm_data.py       # 数据准备
├── train_sarcasm.py              # LoRA训练
├── miarn_sarcasm_detector.py     # MIARN模型
└── attention_sarcasm_detector.py  # 注意力检测
```

---

## 九、新增工作

1. **淘宝爬虫修复** (2025-03-09)
   - 优化评论去重逻辑
   - 修复评论元素定位（class名称包含hash变化）
   - 文件位置：`AIGC/Comment_crawling_and_analysis/taobao_new.py`

2. **MCP工具框架重构** (2025-03-09)
   - 完整MCP工具体系（12个工具）
   - 多场景支持：商品分析、书评分析、酒店分析
   - 知识库RAG管理（查询+更新）
   - Kimi LLM集成（讽刺判断、总结、建议）
   - 情感分析流程：LoRA + TOSPrompt + LLM判断
   - 文件位置：`new_idea/step6_mcp_tools.py`

---

## 八、待完成任务

1. ~~【高优先级】修复Book模型~~ ✅ 已完成
   - 方法：增加训练epoch(5) + 添加短评数据(max_length=64)
   - 结果：验证集准确率92.9%
2. ~~讽刺/阴阳怪气检测模块~~ ✅ 数据+模型已完成
3. 完善Step6 MCP工具注册
4. 完成Step7-8 集成测试
5. 端到端测试

---

## 七、经验总结

### 7.1 遇到的问题
1. **训练中断**：断电导致训练未完成，需从断点恢复
2. **标签混淆**：基座模型分类头随机初始化，需确保训练完成
3. **模型路径**：加载本地缓存模型需使用完整snapshot路径

### 7.2 解决方案
1. 训练时设置checkpoint保存策略
2. 使用merge_and_unload()合并LoRA权重后推理
3. 验证集准确率作为训练效果指标
