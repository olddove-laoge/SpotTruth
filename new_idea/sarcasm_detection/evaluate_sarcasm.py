# evaluate_sarcasm.py
"""
评估反讽/阴阳怪气检测模型
- 基于LoRA微调的分类器
- 测试NTU讽刺语料库 + 正常评论
"""

import torch
import json
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel
import numpy as np

# 路径配置
CACHE_DIR = r"C:\Users\lyh23\.cache\huggingface\hub\models--hfl--chinese-roberta-wwm-ext\snapshots\5c58d0b8ec1d9014354d691c538661bf00bfdb44"
MODEL_DIR = "D:/C_data/SpotTruth/new_idea/sarcasm_detection/output"
TEST_DATA = "D:/C_data/SpotTruth/new_idea/sarcasm_detection/data/sarcasm_train.json"


def load_model():
    """加载LoRA模型"""
    print("加载模型...")
    tokenizer = AutoTokenizer.from_pretrained(CACHE_DIR)
    base_model = AutoModelForSequenceClassification.from_pretrained(CACHE_DIR, num_labels=2)
    model = PeftModel.from_pretrained(base_model, MODEL_DIR)
    model.eval()
    return model, tokenizer


def load_test_data():
    """加载测试数据"""
    with open(TEST_DATA, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def predict(text, model, tokenizer):
    """预测单条文本"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)
        pred = torch.argmax(probs, dim=-1).item()
        confidence = probs[0][pred].item()
    return pred, confidence


def evaluate(model, tokenizer, data):
    """评估模型"""
    model.eval()
    
    # 统计
    correct = 0
    total = 0
    
    # 按类别统计
    results = {
        'irony': {'correct': 0, 'total': 0},      # 阴阳怪气
        'normal': {'correct': 0, 'total': 0},     # 正常评论
    }
    
    # 混淆矩阵
    confusion = {
        'tp': 0,  # 预测讽刺，实际讽刺
        'tn': 0,  # 预测正常，实际正常
        'fp': 0,  # 预测讽刺，实际正常
        'fn': 0,  # 预测正常，实际讽刺
    }
    
    all_preds = []
    all_labels = []
    
    for item in data:
        text = item['text']
        label = item['label']  # 1=讽刺, 0=正常
        
        pred, confidence = predict(text, model, tokenizer)
        
        all_preds.append(pred)
        all_labels.append(label)
        
        # 统计
        total += 1
        if pred == label:
            correct += 1
            if label == 1:
                results['irony']['correct'] += 1
                confusion['tp'] += 1
            else:
                results['normal']['correct'] += 1
                confusion['tn'] += 1
        else:
            if label == 1:
                confusion['fn'] += 1  # 漏检
            else:
                confusion['fp'] += 1  # 误报
        
        if label == 1:
            results['irony']['total'] += 1
        else:
            results['normal']['total'] += 1
    
    # 计算指标
    accuracy = correct / total
    precision = confusion['tp'] / (confusion['tp'] + confusion['fp']) if (confusion['tp'] + confusion['fp']) > 0 else 0
    recall = confusion['tp'] / (confusion['tp'] + confusion['fn']) if (confusion['tp'] + confusion['fn']) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'results': results,
        'confusion': confusion,
        'all_preds': all_preds,
        'all_labels': all_labels
    }


def print_results(result):
    """打印评估结果"""
    print("\n" + "="*60)
    print("反讽检测模型评估结果")
    print("="*60)
    
    print(f"\n总体准确率: {result['accuracy']:.2%}")
    
    print(f"\n精确率 (Precision): {result['precision']:.2%}")
    print(f"召回率 (Recall): {result['recall']:.2%}")
    print(f"F1分数: {result['f1']:.2%}")
    
    print("\n" + "-"*40)
    print("各类别准确率:")
    print("-"*40)
    
    irony_acc = result['results']['irony']['correct'] / result['results']['irony']['total'] if result['results']['irony']['total'] > 0 else 0
    normal_acc = result['results']['normal']['correct'] / result['results']['normal']['total'] if result['results']['normal']['total'] > 0 else 0
    
    print(f"阴阳怪气: {result['results']['irony']['correct']}/{result['results']['irony']['total']} = {irony_acc:.2%}")
    print(f"正常评论: {result['results']['normal']['correct']}/{result['results']['normal']['total']} = {normal_acc:.2%}")
    
    print("\n" + "-"*40)
    print("混淆矩阵:")
    print("-"*40)
    c = result['confusion']
    print(f"                预测正常  预测讽刺")
    print(f"实际正常        {c['tn']:^6}   {c['fp']:^6}")
    print(f"实际讽刺        {c['fn']:^6}   {c['tp']:^6}")


def show_samples(model, tokenizer, data, n=10):
    """展示样本预测结果"""
    print("\n" + "="*60)
    print("样本预测示例")
    print("="*60)
    
    # 阴阳怪气样本
    irony_samples = [d for d in data if d['label'] == 1][:n]
    normal_samples = [d for d in data if d['label'] == 0][:n]
    
    print("\n【阴阳怪气样本】")
    for item in irony_samples:
        pred, conf = predict(item['text'], model, tokenizer)
        status = "✓" if pred == 1 else "✗"
        print(f"{status} 预测: {'讽刺' if pred==1 else '正常'} ({conf:.1%}) | {item['text'][:40]}...")
    
    print("\n【正常评论样本】")
    for item in normal_samples:
        pred, conf = predict(item['text'], model, tokenizer)
        status = "✓" if pred == 0 else "✗"
        print(f"{status} 预测: {'讽刺' if pred==1 else '正常'} ({conf:.1%}) | {item['text'][:40]}...")


def main():
    # 加载模型
    model, tokenizer = load_model()
    
    # 加载数据
    print("加载测试数据...")
    data = load_test_data()
    print(f"测试数据: {len(data)}条")
    print(f"阴阳怪气: {sum(1 for d in data if d['label']==1)}条")
    print(f"正常评论: {sum(1 for d in data if d['label']==0)}条")
    
    # 评估
    result = evaluate(model, tokenizer, data)
    
    # 打印结果
    print_results(result)
    
    # 展示样本
    show_samples(model, tokenizer, data)


if __name__ == "__main__":
    main()
