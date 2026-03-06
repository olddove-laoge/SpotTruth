# 04_train_lora.py
"""
Step 4: LoRA微调训练
- 训练10个品类的LoRA适配器
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, TaskType
import json

CATEGORIES = ["book", "tablet", "phone", "fruit", "shampoo", "dairy", "clothing", "computer", "water_heater", "hotel"]
BASE_MODEL = "hfl/chinese-roberta-wwm-ext"
OUTPUT_DIR = "output/lora"


class SentimentDataset:
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


def train_category(category: str):
    """训练单个品类的LoRA模型"""
    print(f"\n{'='*20} 训练 {category} {'='*20}")
    
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=2
    )
    
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=8,
        lora_alpha=16,
        lora_dropout=0.1,
        target_modules=["query", "value"]
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    train_dataset = SentimentDataset(f"data/{category}/train.json", tokenizer)
    dev_dataset = SentimentDataset(f"data/{category}/dev.json", tokenizer)
    
    training_args = TrainingArguments(
        output_dir=f"{OUTPUT_DIR}/{category}",
        num_train_epochs=3,
        per_device_train_batch_size=16,
        learning_rate=2e-4,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=dev_dataset,
    )
    trainer.train()
    
    model.save_pretrained(f"{OUTPUT_DIR}/{category}")
    tokenizer.save_pretrained(f"{OUTPUT_DIR}/{category}")
    print(f"{category} 模型已保存")


if __name__ == "__main__":
    for cat in CATEGORIES:
        if os.path.exists(f"data/{cat}"):
            train_category(cat)
        else:
            print(f"跳过 {cat}，数据不存在")
