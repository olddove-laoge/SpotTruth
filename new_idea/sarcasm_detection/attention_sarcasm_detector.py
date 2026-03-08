# attention_sarcasm_detector.py
"""
基于注意力机制的讽刺检测（无需情感词典）
- LSTM/Transformer + 句内注意力
- max-pooling 找出最显著的矛盾特征
- 模型自己学习哪些词在"对着干"
"""

import torch
import torch.nn as nn
import numpy as np
from transformers import AutoModel, AutoTokenizer
import json
import os

# 预训练模型
CACHE_DIR = r"C:\Users\lyh23\.cache\huggingface\hub\models--hfl--chinese-roberta-wwm-ext\snapshots\5c58d0b8ec1d9014354d691c538661bf00bfdb44"


def load_model():
    """加载预训练模型"""
    print("加载预训练模型...")
    tokenizer = AutoTokenizer.from_pretrained(CACHE_DIR)
    model = AutoModel.from_pretrained(CACHE_DIR)
    model.eval()
    return model, tokenizer


def get_attention_weights(model, tokenizer, text):
    """获取文本的注意力权重"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128, padding=True)
    input_ids = inputs['input_ids'][0]
    
    # 获取模型输出和注意力权重
    with torch.no_grad():
        outputs = model(**inputs, output_attentions=True)
        attentions = outputs.attentions  # list of (batch, heads, seq, seq)
    
    # 取最后一层注意力
    last_attn = attentions[-1][0]  # (heads, seq, seq)
    
    # 平均所有head
    avg_attn = last_attn.mean(dim=0)  # (seq, seq)
    
    # 获取token
    tokens = tokenizer.convert_ids_to_tokens(input_ids)
    
    return avg_attn, tokens


def max_pooling(attention, tokens):
    """
    max-pooling 找出最显著的矛盾特征
    思路：高注意力权重的地方就是模型认为"重要的词对"
    """
    n = len(tokens)
    
    # 排除特殊token
    valid_mask = [t not in ['[PAD]', '[CLS]', '[SEP]', '[UNK]'] for t in tokens]
    
    # 获取交叉注意力（排除对角线-自我注意）
    cross_attn = attention.numpy()
    np.fill_diagonal(cross_attn, 0)
    
    # 找出最高注意力的词对
    max_idx = np.unravel_index(np.argmax(cross_attn * np.outer(valid_mask, valid_mask)), cross_attn.shape)
    i, j = max_idx
    
    word_i = tokens[i].replace('##', '')
    word_j = tokens[j].replace('##', '')
    max_attn = cross_attn[i, j]
    
    # 获取top-k高注意力词对
    pairs = []
    for ii in range(n):
        for jj in range(n):
            if ii != jj and valid_mask[ii] and valid_mask[jj]:
                pairs.append((ii, jj, cross_attn[ii, jj]))
    
    pairs.sort(key=lambda x: x[2], reverse=True)
    top_pairs = [(tokens[p[0]].replace('##', ''), tokens[p[1]].replace('##', ''), p[2]) for p in pairs[:5]]
    
    return {
        'max_pair': (word_i, word_j, max_attn),
        'top_pairs': top_pairs,
        'all_tokens': [t for t in tokens if t not in ['[PAD]', '[CLS]', '[SEP]', '[UNK]']]
    }


def detect_sarcasm(text, model, tokenizer):
    """主函数：基于注意力+max-pooling检测讽刺"""
    # 获取注意力
    attention, tokens = get_attention_weights(model, tokenizer, text)
    
    # max-pooling
    pool_result = max_pooling(attention, tokens)
    
    # 可解释性：展示哪些词对有高注意力
    print(f"\n文本: {text}")
    print(f"Tokens: {pool_result['all_tokens']}")
    print(f"最高注意力词对: '{pool_result['max_pair'][0]}' <-> '{pool_result['max_pair'][1]}' (attn={pool_result['max_pair'][2]:.4f})")
    print(f"Top-5词对:")
    for w1, w2, attn in pool_result['top_pairs']:
        print(f"  - '{w1}' <-> '{w2}' (attn={attn:.4f})")
    
    return pool_result


def main():
    # 加载模型
    model, tokenizer = load_model()
    
    # 测试样本
    test_samples = [
        # 讽刺样本
        "很好又失眠了!!",
        "太好了，飞蚊症越来越明显了!!!",
        "很好用的产品，三天就坏了",
        "服务态度真不错，等了2小时",
        # 正常样本
        "这本书写得很好，内容丰富",
        "东西质量不错，推荐购买",
    ]
    
    print("\n" + "="*60)
    print("注意力机制讽刺检测 (max-pooling)")
    print("="*60)
    
    for text in test_samples:
        detect_sarcasm(text, model, tokenizer)
        print("-"*40)


if __name__ == "__main__":
    main()
