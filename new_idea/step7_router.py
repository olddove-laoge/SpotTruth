# 07_router.py
"""
Step 7: 路由逻辑
- 根据品类自动选择对应模型
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel

from step2_category_classifier import classify_category
from step5_sarcasm_detector import batch_detect

MODEL_DIR = "output/lora"


def load_category_model(category: str):
    """加载指定品类的模型"""
    model_path = f"{MODEL_DIR}/{category}"
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    base_model = AutoModelForSequenceClassification.from_pretrained(
        "hfl/chinese-roberta-wwm-ext",
        num_labels=2
    )
    model = PeftModel.from_pretrained(base_model, model_path)
    model.eval()
    
    return model, tokenizer


def predict_sentiment(text: str, model, tokenizer) -> dict:
    """单条预测"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        prob = torch.softmax(outputs.logits, dim=-1)[0]
        pred = torch.argmax(prob).item()
    
    return {
        "text": text,
        "prediction": "好评" if pred == 1 else "差评",
        "confidence": prob[pred].item()
    }


def analyze_comments(product_name: str, comments: list[str]) -> dict:
    """主分析流程"""
    # Step 1: 判断品类
    category = classify_category(product_name, comments)
    print(f"商品品类: {category}")
    
    # Step 2: 加载对应模型
    model, tokenizer = load_category_model(category)
    
    # Step 3: 反讽检测
    sarcasm_results = batch_detect(comments)
    
    # Step 4: 情感分析
    results = []
    for comment in comments:
        result = predict_sentiment(comment, model, tokenizer)
        results.append(result)
    
    # 统计
    positive = sum(1 for r in results if r["prediction"] == "好评")
    negative = len(results) - positive
    
    return {
        "category": category,
        "total": len(results),
        "positive": positive,
        "negative": negative,
        "positive_rate": positive / len(results),
        "sarcasm_count": sum(1 for s in sarcasm_results if s.get("is_suspicious")),
        "details": results[:10]  # 返回前10条详情
    }
