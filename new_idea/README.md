# RoBERTa + LoRA 情感分析模型

## 项目结构

```
new_idea/
├── train_sentiment_lora.py    # 训练脚本
├── inference_sentiment.py    # 推理脚本
├── requirements.txt          # 依赖
├── data/
│   ├── train.json           # 训练数据
│   └── dev.json             # 验证数据
└── output/                  # 模型输出目录(训练后生成)
```

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 准备数据
- 编辑 `data/train.json` 添加训练数据
- 编辑 `data/dev.json` 添加验证数据
- 格式：`{"text": "评论内容", "label": 0/1/2}`
  - 0 = 差评
  - 1 = 中评
  - 2 = 好评
- 建议：每类至少100条，越多越好

### 3. 开始训练
```bash
python train_sentiment_lora.py
```

训练完成后模型保存在 `output/sentiment_lora/final_model/`

### 4. 推理测试
```bash
python inference_sentiment.py
```

## 配置说明

在 `train_sentiment_lora.py` 中可调整：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| MODEL_NAME | hfl/chinese-roberta-wwm-ext | 基座模型 |
| MAX_LENGTH | 128 | 最大序列长度 |
| BATCH_SIZE | 16 | 批大小 |
| EPOCHS | 3 | 训练轮数 |
| LEARNING_RATE | 2e-4 | 学习率 |
| r (LoRA) | 8 | LoRA rank |

## 显存要求

- LoRA模式：~4GB
- 全参数微调：~8GB

## 数据标注建议

### 好评 (label=2)
- 明确的正面表达
- 包含"推荐"、"好用"、"满意"等词

### 中评 (label=1)
- 一般、无明显情感倾向
- "还行"、"普通"、"一般"

### 差评 (label=0)
- 明确的负面表达
- 质量问题、态度差、不推荐
- **阴阳怪气**（看似好评实则差评）
