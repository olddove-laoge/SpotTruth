"""
用验证集测试模型准确率
"""

import torch
import json
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel

MODEL_PATH = "D:/C_data/SpotTruth/new_idea/output/lora/book/checkpoint-386"
CACHE_DIR = r"C:\Users\lyh23\.cache\huggingface\hub\models--hfl--chinese-roberta-wwm-ext\snapshots\5c58d0b8ec1d9014354d691c538661bf00bfdb44"


def load_lora_model():
    tokenizer = AutoTokenizer.from_pretrained(CACHE_DIR)
    base_model = AutoModelForSequenceClassification.from_pretrained(CACHE_DIR, num_labels=2)
    model = PeftModel.from_pretrained(base_model, MODEL_PATH)
    model.eval()
    return model, tokenizer


def main():
    with open("D:/C_data/SpotTruth/new_idea/data/book/dev.json", encoding="utf-8") as f:
        dev_data = json.load(f)
    
    model, tokenizer = load_lora_model()
    
    correct = 0
    total = len(dev_data)
    
    pred_0 = 0  # 预测为差评的数量
    pred_1 = 0  # 预测为好评的数量
    
    for item in dev_data[:total]:
        text = item["text"]
        label = item["label"]
        
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            outputs = model(**inputs)
            pred = torch.argmax(outputs.logits, dim=-1).item()
        
        if pred == 0:
            pred_0 += 1
        else:
            pred_1 += 1
            
        if pred == label:
            correct += 1
    
    print(f"验证集准确率: {correct}/{total} = {correct/total:.2%}")
    print(f"预测分布: 差评={pred_0} ({pred_0/total*100:.1f}%), 好评={pred_1} ({pred_1/total*100:.1f}%)")


if __name__ == "__main__":
    main()
