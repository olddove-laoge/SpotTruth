# miarn_sarcasm_detector.py
"""
MIARN模型 - 基于论文 "Reasoning with Sarcasm by Reading In-between"
读取SemEval2018-T3数据集进行训练
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import re
import os
from collections import defaultdict
from sklearn.model_selection import train_test_split

DATA_PATH = r"D:\C_data\SpotTruth\new_idea\sarcasm_detection\data\SemEval2018-T3-train-taskA.txt"


def clean_text(text):
    """
    清洗文本：
    - 去除@xxx（用户名）
    - 去除#xxx（话题标签，保留文字部分）
    - 去除网址
    """
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#(\w+)', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def load_semeval_data(file_path):
    """加载SemEval2018数据集"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines[1:]:
        parts = line.strip().split('\t')
        if len(parts) >= 3:
            idx = parts[0]
            label = int(parts[1])
            text = parts[2]
            cleaned_text = clean_text(text)
            if cleaned_text:
                data.append((cleaned_text, label))
    
    return data


def build_vocab(data, min_freq=2):
    """构建词汇表"""
    vocab = defaultdict(int)
    for text, _ in data:
        tokens = text.lower().split()
        for token in tokens:
            vocab[token] += 1
    
    filtered_vocab = {token: freq for token, freq in vocab.items() if freq >= min_freq}
    
    sorted_vocab = sorted(filtered_vocab.items(), key=lambda x: x[1], reverse=True)
    vocab = {token: idx+2 for idx, (token, _) in enumerate(sorted_vocab)}
    vocab['<PAD>'] = 0
    vocab['<UNK>'] = 1
    return vocab


class SarcasmDataset(Dataset):
    def __init__(self, data, vocab, max_len=32):
        self.data = data
        self.vocab = vocab
        self.max_len = max_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        text, label = self.data[idx]
        tokens = text.lower().split()[:self.max_len]
        token_ids = [self.vocab.get(token, self.vocab['<UNK>']) for token in tokens]
        pad_len = self.max_len - len(token_ids)
        token_ids += [self.vocab['<PAD>']] * pad_len
        return torch.tensor(token_ids, dtype=torch.long), torch.tensor(label, dtype=torch.float)


class MIARN(nn.Module):
    def __init__(self, vocab_size, embed_dim=128, hidden_dim=128, max_len=32):
        super(MIARN, self).__init__()
        self.max_len = max_len
        self.hidden_dim = hidden_dim
        
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hidden_dim,
            batch_first=True,
            bidirectional=True
        )
        
        self.attention_score = nn.Linear(hidden_dim * 4, 1)
        
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid()
        )

    def compute_intra_attention(self, lstm_out):
        """计算句内Attention表示"""
        batch_size, max_len, hidden = lstm_out.shape
        
        lstm_i = lstm_out.unsqueeze(2).expand(batch_size, max_len, max_len, hidden)
        lstm_j = lstm_out.unsqueeze(1).expand(batch_size, max_len, max_len, hidden)
        pair_embeds = torch.cat([lstm_i, lstm_j], dim=-1)
        
        attn_scores = self.attention_score(pair_embeds).squeeze(-1)
        
        row_max = torch.max(attn_scores, dim=2)[0]
        row_max = F.softmax(row_max, dim=1)
        
        intra_attn = torch.bmm(row_max.unsqueeze(1), lstm_out).squeeze(1)
        return intra_attn

    def forward(self, x):
        embeds = self.embedding(x)
        
        lstm_out, (hidden, _) = self.lstm(embeds)
        
        h_forward = hidden[0]
        h_backward = hidden[1]
        lstm_repr = torch.cat([h_forward, h_backward], dim=-1)
        
        intra_attn_repr = self.compute_intra_attention(lstm_out)
        
        concat_repr = torch.cat([lstm_repr, intra_attn_repr], dim=-1)
        output = self.classifier(concat_repr)
        return output


def train_model(model, dataloader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    for token_ids, labels in dataloader:
        token_ids = token_ids.to(device)
        labels = labels.to(device).unsqueeze(1)
        
        outputs = model(token_ids)
        loss = criterion(outputs, labels)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
    return total_loss / len(dataloader)


def evaluate_model(model, dataloader, device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for token_ids, labels in dataloader:
            token_ids = token_ids.to(device)
            labels = labels.to(device).unsqueeze(1)
            
            outputs = model(token_ids)
            preds = (outputs > 0.5).float()
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    return correct / total


def evaluate_model_loss(model, dataloader, criterion, device):
    model.eval()
    total_loss = 0
    with torch.no_grad():
        for token_ids, labels in dataloader:
            token_ids = token_ids.to(device)
            labels = labels.to(device).unsqueeze(1)
            outputs = model(token_ids)
            loss = criterion(outputs, labels)
            total_loss += loss.item()
    return total_loss / len(dataloader)


if __name__ == "__main__":
    EMBED_DIM = 128
    HIDDEN_DIM = 128
    MAX_LEN = 32
    BATCH_SIZE = 32
    EPOCHS = 10
    LR = 0.001
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
    print("加载数据...")
    data = load_semeval_data(DATA_PATH)
    print(f"总样本数: {len(data)}")
    
    labels = [d[1] for d in data]
    print(f"反讽样本: {sum(labels)}, 正常样本: {len(labels) - sum(labels)}")
    
    print("构建词汇表...")
    vocab = build_vocab(data)
    print(f"词汇表大小: {len(vocab)}")
    
    train_data, val_data = train_test_split(data, test_size=0.2, random_state=42, stratify=labels)
    
    train_dataset = SarcasmDataset(train_data, vocab, MAX_LEN)
    val_dataset = SarcasmDataset(val_data, vocab, MAX_LEN)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE)
    
    model = MIARN(vocab_size=len(vocab), embed_dim=EMBED_DIM, hidden_dim=HIDDEN_DIM, max_len=MAX_LEN)
    model = model.to(device)
    
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=LR)
    
    print("\n开始训练...")
    best_loss = float('inf')
    for epoch in range(EPOCHS):
        train_loss = train_model(model, train_loader, criterion, optimizer, device)
        val_loss = evaluate_model_loss(model, val_loader, criterion, device)
        val_acc = evaluate_model(model, val_loader, device)
        print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f}")
        if val_loss < best_loss:
            best_loss = val_loss
            torch.save({
                'model_state_dict': model.state_dict(),
                'vocab': vocab,
                'embed_dim': EMBED_DIM,
                'hidden_dim': HIDDEN_DIM,
                'max_len': MAX_LEN
            }, 'miarn_model.pth')
            print(f"  -> 保存最佳模型 (Val Loss: {best_loss:.4f})")
    
    print(f"\n训练完成! 最佳验证Loss: {best_loss:.4f}")
    
    print("\n========== 测试模型 ==========")
    checkpoint = torch.load('miarn_model.pth')
    model.load_state_dict(checkpoint['model_state_dict'])
    
    test_texts = [
        "I love being ignored by everyone",
        "Oh great another Monday morning",
        "Thanks for waiting two hours for nothing",
        "Wow this is exactly what I wanted",
        "The weather is nice today",
        "I am going to work now"
    ]
    
    model.eval()
    for text in test_texts:
        cleaned = clean_text(text)
        tokens = cleaned.lower().split()[:MAX_LEN]
        token_ids = [vocab.get(t, vocab['<UNK>']) for t in tokens]
        token_ids += [vocab['<PAD>']] * (MAX_LEN - len(token_ids))
        input_tensor = torch.tensor([token_ids], dtype=torch.long).to(device)
        
        with torch.no_grad():
            output = model(input_tensor)
            prob = output.item()
            pred = "反讽" if prob > 0.5 else "正常"
        
        print(f"文本: {text}")
        print(f"预测: {pred} (概率: {prob:.4f})")
        print("-" * 40)
