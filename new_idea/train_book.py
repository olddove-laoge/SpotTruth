# train_book.py
"""
单独训练Book模型
- 增加epoch数到5，解决之前训练不充分的问题
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, TaskType
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output", "lora")
BASE_MODEL = "hfl/chinese-roberta-wwm-ext"

CATEGORY = "book"
NUM_EPOCHS = 5


class SentimentDataset:
    def __init__(self, data_path, tokenizer, max_length=64):
        # 支持加载多个文件并合并
        if isinstance(data_path, list):
            self.data = []
            for p in data_path:
                with open(p, 'r', encoding='utf-8') as f:
                    self.data.extend(json.load(f))
        else:
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


def train_book():
    print(f"\n{'='*20} 训练 {CATEGORY} ({NUM_EPOCHS} epochs) {'='*20}")
    
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
    
    train_dataset = SentimentDataset(
        [f"{DATA_DIR}/{CATEGORY}/train.json", f"{DATA_DIR}/{CATEGORY}/train_synthetic.json"],
        tokenizer
    )
    dev_dataset = SentimentDataset(f"{DATA_DIR}/{CATEGORY}/dev.json", tokenizer)
    
    print(f"训练集: {len(train_dataset)}条")
    print(f"验证集: {len(dev_dataset)}条")
    
    training_args = TrainingArguments(
        output_dir=f"{OUTPUT_DIR}/{CATEGORY}",
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=16,
        learning_rate=2e-4,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=dev_dataset,
    )
    
    trainer.train()
    
    model.save_pretrained(f"{OUTPUT_DIR}/{CATEGORY}")
    tokenizer.save_pretrained(f"{OUTPUT_DIR}/{CATEGORY}")
    print(f"{CATEGORY} 模型已保存到 {OUTPUT_DIR}/{CATEGORY}")


if __name__ == "__main__":
    train_book()
