"""
RoBERTa-base + LoRA 好中差评分类器推理脚本
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel

# ============== 配置 ==============
MODEL_PATH = "./output/sentiment_lora/final_model"

# 标签映射
LABELS = {0: "差评", 1: "中评", 2: "好评"}

# ============== 加载模型 ==============
def load_model():
    """加载训练好的模型"""
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    
    base_model = AutoModelForSequenceClassification.from_pretrained(
        "hfl/chinese-roberta-wwm-ext",
        num_labels=3
    )
    
    # 加载LoRA权重
    model = PeftModel.from_pretrained(base_model, MODEL_PATH)
    
    # 或者合并后加载（推理更快）
    # model = base_model
    # model.load_adapter(MODEL_PATH, "default")
    # model = model.merge_and_unload()
    
    return model, tokenizer

# ============== 推理函数 ==============
def predict(text, model, tokenizer):
    """预测单条文本"""
    inputs = tokenizer(
        text, 
        return_tensors="pt", 
        truncation=True, 
        max_length=128
    )
    
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)
        pred = torch.argmax(probs, dim=-1).item()
    
    return {
        "text": text,
        "prediction": LABELS[pred],
        "confidence": probs[0][pred].item(),
        "probabilities": {
            "差评": round(probs[0][0].item(), 4),
            "中评": round(probs[0][1].item(), 4),
            "好评": round(probs[0][2].item(), 4)
        }
    }

# ============== 批量预测 ==============
def predict_batch(texts, model, tokenizer):
    """批量预测"""
    results = []
    for text in texts:
        result = predict(text, model, tokenizer)
        results.append(result)
    return results

# ============== 主函数 ==============
if __name__ == "__main__":
    # 加载模型
    print("加载模型...")
    model, tokenizer = load_model()
    model.eval()
    print("模型加载完成")
    
    # 测试文本
    test_texts = [
        "手机非常好用，拍照清晰，推荐购买",
        "一般般，没什么亮点",
        "质量太差了，屏幕有划痕，不推荐",
        "好评骗一下更多的人，笑死了"
    ]
    
    # 预测
    print("\n" + "="*50)
    for text in test_texts:
        result = predict(text, model, tokenizer)
        print(f"文本: {result['text']}")
        print(f"预测: {result['prediction']} (置信度: {result['confidence']:.2%})")
        print(f"概率: 差评={result['probabilities']['差评']}, "
              f"中评={result['probabilities']['中评']}, "
              f"好评={result['probabilities']['好评']}")
        print("-"*50)
