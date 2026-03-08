# 04_train_lora_3cls.py
"""
Step 4: LoRA微调训练 - 三分类版本
针对electronics品类（手机+电脑）
解决中评占比低的问题：使用类别权重 + 过采样
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
import json
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output", "lora_3cls")
CACHE_DIR = r"C:\Users\lyh23\.cache\huggingface\hub\models--hfl--chinese-roberta-wwm-ext\snapshots\5c58d0b8ec1d9014354d691c538661bf00bfdb44"

CATEGORY = "electronics_3cls"
BASE_MODEL = "hfl/chinese-roberta-wwm-ext"


def load_data(data_path):
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def oversample(data, target_count, label):
    """过采样指定标签的数据"""
    label_data = [x for x in data if x['label'] == label]
    other_data = [x for x in data if x['label'] != label]
    
    if len(label_data) >= target_count:
        return data
    
    # 随机重复采样
    oversampled = label_data.copy()
    while len(oversampled) < target_count:
        oversampled.extend(label_data[:min(target_count - len(oversampled), len(label_data))])
    
    return other_data + oversampled


def compute_class_weights(labels):
    """计算类别权重，用于处理不平衡数据"""
    counter = Counter(labels)
    total = len(labels)
    weights = {}
    for label, count in counter.items():
        weights[label] = total / (len(counter) * count)
    return weights


def compute_metrics(eval_pred):
    """计算准确率"""
    predictions, labels = eval_pred
    predictions = predictions.argmax(axis=-1)
    accuracy = (predictions == labels).astype(float).mean()
    return {"accuracy": accuracy}


def main():
    print(f"\n{'='*20} 训练 {CATEGORY} (三分类) {'='*20}")
    
    # 加载数据
    train_data = load_data(f"{DATA_DIR}/{CATEGORY}/train.json")
    dev_data = load_data(f"{DATA_DIR}/{CATEGORY}/dev.json")
    
    print(f"原始 train: {len(train_data)}, dev: {len(dev_data)}")
    
    # 检查类别分布
    train_labels = [x['label'] for x in train_data]
    print(f"训练集分布: {dict(Counter(train_labels))}")
    
    # 过采样中评(label=1)，使其与差评/好评数量相当
    # 目标：中评数量 = 好评/差评数量
    max_count = max(Counter(train_labels).values())
    train_data_oversampled = oversample(train_data, max_count, 1)
    
    # 打乱数据
    import random
    random.shuffle(train_data_oversampled)
    
    print(f"过采样后 train: {len(train_data_oversampled)}")
    print(f"过采样后分布: {dict(Counter([x['label'] for x in train_data_oversampled]))}")
    
    # 加载tokenizer和模型
    tokenizer = AutoTokenizer.from_pretrained(CACHE_DIR)
    
    model = AutoModelForSequenceClassification.from_pretrained(
        CACHE_DIR,
        num_labels=3  # 三分类
    )
    
    # LoRA配置
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=8,
        lora_alpha=16,
        lora_dropout=0.1,
        target_modules=["query", "value"]
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # 准备数据集
    train_texts = [x['text'] for x in train_data_oversampled]
    train_labels = [x['label'] for x in train_data_oversampled]
    
    dev_texts = [x['text'] for x in dev_data]
    dev_labels = [x['label'] for x in dev_data]
    
    # Tokenize
    train_enc = tokenizer(train_texts, truncation=True, max_length=128, padding="max_length")
    dev_enc = tokenizer(dev_texts, truncation=True, max_length=128, padding="max_length")
    
    train_dataset = Dataset.from_dict({
        "input_ids": train_enc["input_ids"],
        "attention_mask": train_enc["attention_mask"],
        "labels": train_labels
    })
    
    dev_dataset = Dataset.from_dict({
        "input_ids": dev_enc["input_ids"],
        "attention_mask": dev_enc["attention_mask"],
        "labels": dev_labels
    })
    
    # 计算类别权重
    class_weights = compute_class_weights(train_labels)
    print(f"类别权重: {class_weights}")
    
    # 自定义Trainer，计算加权损失
    class WeightedTrainer(Trainer):
        def __init__(self, class_weights, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.class_weights = torch.tensor([class_weights[i] for i in range(len(class_weights))], dtype=torch.float32)
        
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            loss_fct = torch.nn.CrossEntropyLoss(weight=self.class_weights.to(model.device))
            loss = loss_fct(outputs.logits.view(-1, 3), labels.view(-1))
            return (loss, outputs) if return_outputs else loss
    
    # 训练参数
    training_args = TrainingArguments(
        output_dir=f"{OUTPUT_DIR}/{CATEGORY}",
        num_train_epochs=3,
        per_device_train_batch_size=16,
        learning_rate=2e-4,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
    )
    
    trainer = WeightedTrainer(
        class_weights=class_weights,
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=dev_dataset,
        compute_metrics=compute_metrics,
    )
    
    trainer.train()
    
    # 保存模型
    model.save_pretrained(f"{OUTPUT_DIR}/{CATEGORY}")
    tokenizer.save_pretrained(f"{OUTPUT_DIR}/{CATEGORY}")
    print(f"{CATEGORY} 三分类模型已保存")


if __name__ == "__main__":
    main()
