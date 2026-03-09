# train_prompt.py
"""
TOSPrompt 风格的提示学习训练
核心思路：
1. 构造提示模板："{评论} 是对 {话题} 的讽刺吗？[MASK]"
2. 让BERT预测[MASK]位置是"是"还是"否"
3. 用预测结果判断讽刺/非讽刺
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForMaskedLM
import json
import os
from tqdm import tqdm

# 路径配置
CACHE_DIR = r"C:\Users\lyh23\.cache\huggingface\hub\models--hfl--chinese-roberta-wwm-ext\snapshots\5c58d0b8ec1d9014354d691c538661bf00bfdb44"
DATA_DIR = "D:/C_data/SpotTruth/new_idea/sarcasm_detection/data"
OUTPUT_DIR = "D:/C_data/SpotTruth/new_idea/sarcasm_detection/output_prompt"

# 训练超参数（按论文）
BATCH_SIZE = 32
EPOCHS = 5
LEARNING_RATE = 2e-5
DROPOUT = 0.1
MAX_LENGTH = 64

# 标签词
LABEL_WORDS = {
    1: "是",   # 讽刺 -> 填"是"
    0: "否"    # 非讽刺 -> 填"否"
}


class PromptDataset(Dataset):
    def __init__(self, data, tokenizer, max_length=64):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        text = item['text']
        topic = item['topic']
        label = int(item['label'])
        
        # 构造提示模板
        prompt = f"{text} 是对 {topic} 的讽刺吗？[MASK]"
        
        # tokenize
        encoded = self.tokenizer(
            prompt,
            truncation=True,
            max_length=self.max_length,
            padding='max_length',
            return_tensors='pt'
        )
        
        # 找到[MASK]的位置
        mask_token_id = self.tokenizer.mask_token_id
        mask_positions = (encoded['input_ids'] == mask_token_id).nonzero(as_tuple=True)
        
        # 取第一个[MASK]的位置
        mask_pos = mask_positions[1][0].item() if len(mask_positions[1]) > 0 else -1
        
        return {
            'input_ids': encoded['input_ids'].squeeze(0),
            'attention_mask': encoded['attention_mask'].squeeze(0),
            'label': label,
            'mask_pos': mask_pos
        }


class PromptModel(nn.Module):
    def __init__(self, model_name):
        super().__init__()
        self.bert = AutoModelForMaskedLM.from_pretrained(model_name)
        self.dropout = nn.Dropout(DROPOUT)
    
    def forward(self, input_ids, attention_mask, mask_pos, labels=None):
        """
        mask_pos: [batch] 每个样本的mask位置
        """
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        
        # 获取logits
        logits = outputs.logits  # [batch, seq_len, vocab_size]
        
        batch_size = input_ids.size(0)
        
        # 获取每个样本mask位置的logit
        mask_logits = []
        for i in range(batch_size):
            mp = mask_pos[i]
            if mp > 0:
                mask_logits.append(logits[i, mp, :])
            else:
                mask_logits.append(logits[i, 0, :])  # fallback
        
        mask_logits = torch.stack(mask_logits)  # [batch, vocab_size]
        
        # 获取"是"和"否"的logit
        yes_id = self.bert.config.vocab_size  # placeholder
        no_id = self.bert.config.vocab_size   # placeholder
        
        # 计算概率
        probs = torch.softmax(mask_logits, dim=-1)
        
        return probs, logits


def train_epoch(model, dataloader, optimizer, tokenizer, device):
    """训练一个epoch"""
    model.train()
    total_loss = 0
    
    for batch in tqdm(dataloader, desc="Training"):
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['label'].to(device)
        mask_pos = batch['mask_pos'].to(device)
        
        optimizer.zero_grad()
        
        # 前向传播
        probs, _ = model(input_ids, attention_mask, mask_pos)
        
        # 获取"是"和"否"的概率
        yes_id = tokenizer.encode("是", add_special_tokens=False)[0]
        no_id = tokenizer.encode("否", add_special_tokens=False)[0]
        
        # 预测概率
        pred_yes = probs[:, yes_id]
        pred_no = probs[:, no_id]
        
        # 拼接作为分类logit
        class_logits = torch.stack([pred_no, pred_yes], dim=1)  # [batch, 2]
        
        # 交叉熵损失
        loss = nn.CrossEntropyLoss()(class_logits, labels)
        
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
    
    return total_loss / len(dataloader)


def evaluate(model, dataloader, tokenizer, device):
    """评估"""
    model.eval()
    correct = 0
    total = 0
    
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['label'].to(device)
            mask_pos = batch['mask_pos'].to(device)
            
            probs, _ = model(input_ids, attention_mask, mask_pos)
            
            # 获取"是"和"否"的概率
            yes_id = tokenizer.encode("是", add_special_tokens=False)[0]
            no_id = tokenizer.encode("否", add_special_tokens=False)[0]
            
            pred_yes = probs[:, yes_id]
            pred_no = probs[:, no_id]
            
            # 预测：选概率大的
            preds = (pred_yes > pred_no).long()
            
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    
    return correct / total


def main():
    print("="*60)
    print("TOSPrompt Style - 提示学习训练")
    print("="*60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    
    # 加载tokenizer和模型
    print("\nLoading model...")
    tokenizer = AutoTokenizer.from_pretrained(CACHE_DIR)
    model = PromptModel(CACHE_DIR)
    model = model.to(device)
    
    # 加载数据
    print("Loading data...")
    with open(f"{DATA_DIR}/train.json", 'r', encoding='utf-8') as f:
        train_data = json.load(f)
    with open(f"{DATA_DIR}/dev.json", 'r', encoding='utf-8') as f:
        dev_data = json.load(f)
    
    print(f"Train: {len(train_data)}, Dev: {len(dev_data)}")
    
    # 统计标签
    train_label_1 = sum(1 for d in train_data if int(d['label']) == 1)
    train_label_0 = sum(1 for d in train_data if int(d['label']) == 0)
    print(f"Train: 讽刺={train_label_1}, 非讽刺={train_label_0}")
    
    # 创建数据集
    train_dataset = PromptDataset(train_data, tokenizer, MAX_LENGTH)
    dev_dataset = PromptDataset(dev_data, tokenizer, MAX_LENGTH)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    dev_loader = DataLoader(dev_dataset, batch_size=BATCH_SIZE)
    
    # 优化器
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    
    # 训练
    best_acc = 0
    for epoch in range(EPOCHS):
        print(f"\nEpoch {epoch+1}/{EPOCHS}")
        
        # 训练
        train_loss = train_epoch(model, train_loader, optimizer, tokenizer, device)
        
        # 评估
        val_acc = evaluate(model, dev_loader, tokenizer, device)
        
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Val Acc: {val_acc:.4f}")
        
        # 保存最佳模型
        if val_acc > best_acc:
            best_acc = val_acc
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            model.bert.save_pretrained(OUTPUT_DIR)
            tokenizer.save_pretrained(OUTPUT_DIR)
            print(f"  [Saved: {val_acc:.4f}]")
    
    print(f"\nBest Val Acc: {best_acc:.4f}")


if __name__ == "__main__":
    main()
