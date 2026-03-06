"""
RoBERTa-base + LoRA 好中差评分类器训练脚本
基于 PEFT 框架实现轻量级微调
"""

import json
import os
from dataclasses import dataclass
import torch
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification,
    TrainingArguments, 
    Trainer,
    DataCollatorWithPadding
)
from peft import LoraConfig, get_peft_model, TaskType
import numpy as np
from sklearn.metrics import accuracy_score, classification_report

# ============== 配置 ==============
MODEL_NAME = "hfl/chinese-roberta-wwm-ext"  # 中文RoBERTa
MAX_LENGTH = 128
BATCH_SIZE = 16
EPOCHS = 3
LEARNING_RATE = 2e-4
OUTPUT_DIR = "./output/sentiment_lora"
TRAIN_DATA_PATH = "data/train.json"
DEV_DATA_PATH = "data/dev.json"

# ============== 数据加载 ==============
class SentimentDataset(Dataset):
    """情感分析数据集"""
    def __init__(self, data_path, tokenizer, max_length=128):
        with open(data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        return {
            "text": item["text"],
            "label": item["label"],
            **self.tokenizer(
                item["text"],
                truncation=True,
                max_length=self.max_length,
                padding="max_length"
            )
        }

# ============== 指标计算 ==============
def compute_metrics(eval_pred):
    """计算准确率"""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    acc = accuracy_score(labels, predictions)
    return {"accuracy": acc}

# ============== 主训练 ==============
def main():
    # 1. 加载tokenizer和模型
    print(f"加载模型: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=3,  # 好/中/差
    )
    
    # 2. 配置LoRA
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,       # 文本分类任务
        r=8,                               # LoRA rank
        lora_alpha=16,                     # 缩放系数
        lora_dropout=0.1,                  # Dropout
        target_modules=["query", "value"], # Attention的q和v
        bias="none",
    )
    
    # 3. 应用LoRA
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    # 输出示例: trainable params: 296,820 || all params: 102,267,264 || trainable%: 0.29%
    
    # 4. 加载数据
    train_dataset = SentimentDataset(TRAIN_DATA_PATH, tokenizer, MAX_LENGTH)
    eval_dataset = SentimentDataset(DEV_DATA_PATH, tokenizer, MAX_LENGTH)
    
    # 5. 训练参数
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE * 2,
        learning_rate=LEARNING_RATE,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        logging_dir=f"{OUTPUT_DIR}/logs",
        logging_steps=10,
        warmup_ratio=0.1,
        fp16=True,                         # 混合精度
        save_total_limit=2,
    )
    
    # 6. Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_metrics,
        data_collator=DataCollatorWithPadding(tokenizer),
    )
    
    # 7. 开始训练
    print("开始训练...")
    trainer.train()
    
    # 8. 保存
    model.save_pretrained(f"{OUTPUT_DIR}/final_model")
    tokenizer.save_pretrained(f"{OUTPUT_DIR}/final_model")
    print(f"模型已保存到: {OUTPUT_DIR}/final_model")

if __name__ == "__main__":
    main()
