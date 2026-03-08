# train_sarcasm.py
"""
训练讽刺/阴阳怪气检测模型
- 基于RoBERTa + LoRA微调
- 二分类：讽刺 vs 正常
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, TaskType
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "data", "sarcasm_train.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
BASE_MODEL = "hfl/chinese-roberta-wwm-ext"

NUM_EPOCHS = 5
MAX_LENGTH = 128


class SarcasmDataset:
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


def train_sarcasm():
    print(f"\n{'='*20} 训练讽刺检测模型 ({NUM_EPOCHS} epochs) {'='*20}")
    
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
    
    # 划分训练集/验证集 (8:2)
    full_dataset = SarcasmDataset(DATA_FILE, tokenizer, MAX_LENGTH)
    
    # 简单划分
    n_train = int(len(full_dataset) * 0.8)
    n_val = len(full_dataset) - n_train
    
    train_dataset, val_dataset = torch.utils.data.random_split(
        full_dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(42)
    )
    
    print(f"训练集: {n_train}条")
    print(f"验证集: {n_val}条")
    
    # 统计标签分布
    train_labels = [full_dataset[i]['label'] for i in train_dataset.indices]
    val_labels = [full_dataset[i]['label'] for i in val_dataset.indices]
    print(f"训练集: 正常={train_labels.count(0)}, 讽刺={train_labels.count(1)}")
    print(f"验证集: 正常={val_labels.count(0)}, 讽刺={val_labels.count(1)}")
    
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
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
        eval_dataset=val_dataset,
    )
    
    trainer.train()
    
    # 保存模型
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"\n模型已保存到: {OUTPUT_DIR}")


if __name__ == "__main__":
    train_sarcasm()
