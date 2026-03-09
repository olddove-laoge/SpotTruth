# evaluate_prompt.py
"""
TOSPrompt模型评估
使用不同商品评论作为话题进行测试
"""

import torch
import json
from transformers import AutoTokenizer, AutoModelForMaskedLM

# 路径配置
MODEL_DIR = "D:/C_data/SpotTruth/new_idea/sarcasm_detection/output_prompt"
CACHE_DIR = r"C:\Users\lyh23\.cache\huggingface\hub\models--hfl--chinese-roberta-wwm-ext\snapshots\5c58d0b8ec1d9014354d691c538661bf00bfdb44"


def load_model():
    """加载模型"""
    print("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForMaskedLM.from_pretrained(MODEL_DIR)
    model.eval()
    return model, tokenizer


def predict(text, topic, model, tokenizer):
    """预测单条"""
    # 构造提示模板
    prompt = f"{text} 是对 {topic} 的讽刺吗？[MASK]"
    
    # tokenize
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=64)
    
    # 找到[MASK]位置
    input_ids = inputs['input_ids']
    mask_token_id = tokenizer.mask_token_id
    mask_positions = (input_ids == mask_token_id).nonzero(as_tuple=True)
    mask_pos = mask_positions[1][0].item()
    
    # 预测
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        
        # 获取mask位置的logit
        mask_logits = logits[0, mask_pos, :]
        
        # 获取"是"和"否"的概率
        yes_id = tokenizer.encode("是", add_special_tokens=False)[0]
        no_id = tokenizer.encode("否", add_special_tokens=False)[0]
        
        probs = torch.softmax(mask_logits, dim=-1)
        prob_yes = probs[yes_id].item()
        prob_no = probs[no_id].item()
        
        # 判断
        is_irony = prob_yes > prob_no
        confidence = prob_yes if is_irony else prob_no
    
    return is_irony, confidence, prob_yes, prob_no


# 拓展后的测试数据：更强的讽刺意味 + 更多场景
TEST_DATA = {
    "商品评论": [
        # 高强度讽刺评论（反语更夸张、对比更强烈）
        {
            "topic": "手机",
            "text": "这手机续航绝了，充一次电用半小时，真是太值了",
            "expected": "讽刺"
        },
        {
            "topic": "电脑",
            "text": "这电脑性能无敌，打开个文档都卡成幻灯片，太给力了",
            "expected": "讽刺"
        },
        {
            "topic": "耳机",
            "text": "这耳机降噪效果拉满，戴着能听见隔壁楼吵架，太牛了",
            "expected": "讽刺"
        },
        {
            "topic": "相机",
            "text": "这相机防抖超棒，拍出来的照片比心电图还抖，太专业了",
            "expected": "讽刺"
        },
        {
            "topic": "键盘",
            "text": "这键盘响应超快，按下去三秒才出字，太丝滑了",
            "expected": "讽刺"
        },
        {
            "topic": "充电宝",
            "text": "这充电宝容量超大，充手机1%就没电了，太实用了",
            "expected": "讽刺"
        },
        {
            "topic": "鼠标",
            "text": "这鼠标精准度爆表，点一下能跑偏三米，太精准了",
            "expected": "讽刺"
        },
        
        # 正常好评
        {
            "topic": "手机",
            "text": "手机很好用，运行流畅，续航能撑一整天",
            "expected": "正常"
        },
        {
            "topic": "电脑",
            "text": "电脑配置不错，性价比高，多任务处理不卡顿",
            "expected": "正常"
        },
        {
            "topic": "耳机",
            "text": "耳机音质清晰，降噪效果好，佩戴也很舒适",
            "expected": "正常"
        },
        
        # 正常差评（无讽刺，直接表达不满）
        {
            "topic": "手机",
            "text": "手机质量太差，几天就坏了，售后还不负责",
            "expected": "正常"
        },
        {
            "topic": "耳机",
            "text": "耳机音质不好，有杂音，不推荐购买",
            "expected": "正常"
        },
        {
            "topic": "充电宝",
            "text": "充电宝容量虚标严重，实际使用和描述差太多",
            "expected": "正常"
        },
    ],
    
    "生活场景": [
        # 高强度讽刺
        {
            "topic": "天气",
            "text": "今天天气太完美了，下着暴雨还刮大风，出门直接淋成落汤鸡，太舒服了",
            "expected": "讽刺"
        },
        {
            "topic": "工作",
            "text": "这份工作简直是神仙工作，工资3000干3个人的活，每天加班到凌晨，太幸福了",
            "expected": "讽刺"
        },
        {
            "topic": "交通",
            "text": "这地铁效率超高，等了一小时才来，上车挤成照片，太便捷了",
            "expected": "讽刺"
        },
        {
            "topic": "外卖",
            "text": "这外卖配送速度绝了，点完两小时才到，饭菜都馊了，太准时了",
            "expected": "讽刺"
        },
        
        # 正常表述
        {
            "topic": "天气",
            "text": "今天天气很好，阳光明媚，温度也很适宜",
            "expected": "正常"
        },
        {
            "topic": "工作",
            "text": "工作压力很大，需要经常加班，希望能涨工资",
            "expected": "正常"
        },
        {
            "topic": "交通",
            "text": "地铁高峰期人很多，通勤时间比较长",
            "expected": "正常"
        },
        {
            "topic": "外卖",
            "text": "外卖配送有点慢，饭菜都凉了，体验不好",
            "expected": "正常"
        },
    ],
    
    "服务场景": [
        # 高强度讽刺
        {
            "topic": "快递",
            "text": "这快递物流快到离谱，下单半个月还在仓库，太有效率了",
            "expected": "讽刺"
        },
        {
            "topic": "客服",
            "text": "这客服态度好到爆炸，问啥都不知道，还怼人，太专业了",
            "expected": "讽刺"
        },
        {
            "topic": "餐厅",
            "text": "这餐厅服务超贴心，等了两小时才上菜，菜还凉了，太满意了",
            "expected": "讽刺"
        },
        {
            "topic": "酒店",
            "text": "这酒店环境超棒，房间又小又脏，还有蟑螂，太舒适了",
            "expected": "讽刺"
        },
        
        # 正常表述
        {
            "topic": "快递",
            "text": "物流很快，第二天就到了，快递员态度也很好",
            "expected": "正常"
        },
        {
            "topic": "客服",
            "text": "客服很有耐心，回答详细，问题很快就解决了",
            "expected": "正常"
        },
        {
            "topic": "餐厅",
            "text": "餐厅上菜有点慢，但味道还不错，服务也还行",
            "expected": "正常"
        },
        {
            "topic": "酒店",
            "text": "酒店房间有点小，卫生一般，性价比不高",
            "expected": "正常"
        },
    ],
    
    # 新增场景：餐饮场景
    "餐饮场景": [
        # 高强度讽刺
        {
            "topic": "奶茶",
            "text": "这奶茶味道绝了，齁甜还没茶味，一杯28太值了",
            "expected": "讽刺"
        },
        {
            "topic": "火锅",
            "text": "这火锅太正宗了，锅底没味道，食材还不新鲜，太好吃了",
            "expected": "讽刺"
        },
        {
            "topic": "快餐",
            "text": "这快餐性价比超高，30块钱就一点菜，还凉飕飕的，太划算了",
            "expected": "讽刺"
        },
        
        # 正常表述
        {
            "topic": "奶茶",
            "text": "奶茶甜度适中，茶味浓郁，口感很好",
            "expected": "正常"
        },
        {
            "topic": "火锅",
            "text": "火锅锅底味道正宗，食材新鲜，价格合理",
            "expected": "正常"
        },
        {
            "topic": "快餐",
            "text": "快餐分量太少，价格偏贵，味道也一般",
            "expected": "正常"
        },
    ],
    
    # 新增场景：旅游场景
    "旅游场景": [
        # 高强度讽刺
        {
            "topic": "景区",
            "text": "这景区美如画，全是人挤人，门票还死贵，太值得来了",
            "expected": "讽刺"
        },
        {
            "topic": "民宿",
            "text": "这民宿环境超棒，又潮又吵，还不如网吧，太舒服了",
            "expected": "讽刺"
        },
        {
            "topic": "导游",
            "text": "这导游讲解超专业，全程只知道推销，太负责任了",
            "expected": "讽刺"
        },
        
        # 正常表述
        {
            "topic": "景区",
            "text": "景区风景很好，人不多，门票价格也合理",
            "expected": "正常"
        },
        {
            "topic": "民宿",
            "text": "民宿环境干净，位置便利，老板也很热情",
            "expected": "正常"
        },
        {
            "topic": "导游",
            "text": "导游讲解不详细，还强制购物，体验很差",
            "expected": "正常"
        },
    ]
}


def main():
    # 加载模型
    model, tokenizer = load_model()
    
    print("\n" + "="*60)
    print("TOSPrompt Model Evaluation")
    print("="*60)
    
    # 统计
    all_correct = 0
    all_total = 0
    
    # 用于计算精确率、召回率
    # TP: 预测讽刺，实际也是讽刺
    # FP: 预测讽刺，实际正常
    # FN: 预测正常，实际讽刺
    # TN: 预测正常，实际正常
    tp = fp = fn = tn = 0
    
    for category, samples in TEST_DATA.items():
        print(f"\n{'='*40}")
        print(f"[{category}]")
        print("="*40)
        
        correct = 0
        total = 0
        cat_tp = cat_fp = cat_fn = cat_tn = 0
        
        for item in samples:
            topic = item['topic']
            text = item['text']
            expected = item['expected']
            
            is_irony, confidence, prob_yes, prob_no = predict(text, topic, model, tokenizer)
            
            result = "讽刺" if is_irony else "正常"
            status = "[OK]" if result == expected else "[X]"
            
            if result == expected:
                correct += 1
                all_correct += 1
                
                # 统计TP/TN
                if expected == "讽刺":
                    tp += 1
                    cat_tp += 1
                else:
                    tn += 1
                    cat_tn += 1
            else:
                # 统计FP/FN
                if result == "讽刺" and expected == "正常":
                    fp += 1
                    cat_fp += 1
                elif result == "正常" and expected == "讽刺":
                    fn += 1
                    cat_fn += 1
            
            total += 1
            all_total += 1
            
            print(f"\n{status} 话题: {topic}")
            print(f"    评论: {text}")
            print(f"    预期: {expected}, 预测: {result}")
            print(f"    是: {prob_yes:.2%}, 否: {prob_no:.2%}")
        
        # 类别指标
        acc = correct / total * 100 if total > 0 else 0
        cat_precision = cat_tp / (cat_tp + cat_fp) * 100 if (cat_tp + cat_fp) > 0 else 0
        cat_recall = cat_tp / (cat_tp + cat_fn) * 100 if (cat_tp + cat_fn) > 0 else 0
        cat_f1 = 2 * cat_precision * cat_recall / (cat_precision + cat_recall) if (cat_precision + cat_recall) > 0 else 0
        
        print(f"\n  准确率: {acc:.1f}% | 精确率: {cat_precision:.1f}% | 召回率: {cat_recall:.1f}% | F1: {cat_f1:.1f}%")
    
    # 总计
    print("\n" + "="*60)
    overall_acc = all_correct / all_total * 100 if all_total > 0 else 0
    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"Overall Accuracy: {all_correct}/{all_total} = {overall_acc:.1f}%")
    print(f"Precision (讽刺): {precision:.1f}%")
    print(f"Recall (讽刺): {recall:.1f}%")
    print(f"F1 Score: {f1:.1f}%")
    print("="*60)


if __name__ == "__main__":
    main()