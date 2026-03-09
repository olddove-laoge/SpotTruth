"""
测试electronics三分类模型 - LoRA训练前后对比
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel

MODEL_PATH = "D:/C_data/SpotTruth/new_idea/output/lora_3cls/electronics_3cls"
CACHE_DIR = r"C:\Users\lyh23\.cache\huggingface\hub\models--hfl--chinese-roberta-wwm-ext\snapshots\5c58d0b8ec1d9014354d691c538661bf00bfdb44"
LABELS = {0: "差评", 1: "中评", 2: "好评"}


def load_base_model():
    """加载基座模型（LoRA训练前）"""
    print("=" * 60)
    print("【LoRA训练前】基座模型: hfl/chinese-roberta-wwm-ext (三分类)")
    print("=" * 60)
    tokenizer = AutoTokenizer.from_pretrained(CACHE_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(CACHE_DIR, num_labels=3)
    model.eval()
    return model, tokenizer


def load_lora_model():
    """加载LoRA模型（训练后）"""
    print("\n" + "=" * 60)
    print("【LoRA训练后】基座模型 + electronics三分类LoRA适配器")
    print("=" * 60)
    tokenizer = AutoTokenizer.from_pretrained(CACHE_DIR)
    base_model = AutoModelForSequenceClassification.from_pretrained(CACHE_DIR, num_labels=3)
    model = PeftModel.from_pretrained(base_model, MODEL_PATH)
    model.eval()
    return model, tokenizer


def predict(text, model, tokenizer):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)
        pred = torch.argmax(probs, dim=-1).item()
    return LABELS[pred], probs[0][pred].item(), {
        "差评": round(probs[0][0].item(), 4),
        "中评": round(probs[0][1].item(), 4),
        "好评": round(probs[0][2].item(), 4)
    }


def main():
    test_texts = [
        ("手机很好用，拍照清晰，运行流畅，推荐购买", "好评"),
        ("屏幕清晰，电池续航给力，性价比高", "好评"),
        ("物流很快，手机整体不错", "好评"),
        ("无功无过吧。", "中评"),
        ("一般般，性价比一般，不推荐也不反对", "中评"),
        ("价格有点贵，不太值这个价钱", "中评"),
        ("质量太差了，用了几天就坏了，强烈不推荐", "差评"),
        ("客服态度很差，完全不想再买", "差评"),
        ("垃圾产品，买了后悔", "差评"),
    ]

    base_model, tokenizer = load_base_model()
    lora_model, _ = load_lora_model()

    print("\n" + "=" * 80)
    print(f"{'文本':<35} {'LoRA前':<10} {'LoRA后':<10}")
    print("=" * 80)

    for text, expected in test_texts:
        base_pred, base_conf, base_probs = predict(text, base_model, tokenizer)
        lora_pred, lora_conf, lora_probs = predict(text, lora_model, tokenizer)
        
        base_correct = "✓" if base_pred == expected else "X"
        lora_correct = "✓" if lora_pred == expected else "X"
        
        print(f"{text[:33]:<35} {base_pred}({base_conf:.0%}){base_correct} {lora_pred}({lora_conf:.0%}){lora_correct}")

    print("\n【详细概率对比】")
    print("-" * 80)
    for text, expected in test_texts:
        _, _, base_probs = predict(text, base_model, tokenizer)
        _, _, lora_probs = predict(text, lora_model, tokenizer)
        print(f"文本: {text}")
        print(f"  LoRA前: 差评={base_probs['差评']}, 中评={base_probs['中评']}, 好评={base_probs['好评']}")
        print(f"  LoRA后: 差评={lora_probs['差评']}, 中评={lora_probs['中评']}, 好评={lora_probs['好评']}")
        print()


if __name__ == "__main__":
    main()
