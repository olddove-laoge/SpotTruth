# evaluate_new_data.py
"""
使用从未见过的新数据进行评估
- 中文→英文翻译
- 检验模型泛化能力
- 优化：强化反讽案例典型性，扩展场景覆盖，修正翻译错误
"""

import torch
import json
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel

# 路径配置
CACHE_DIR = r"C:\Users\lyh23\.cache\huggingface\hub\models--hfl--chinese-roberta-wwm-ext\snapshots\5c58d0b8ec1d9014354d691c538661bf00bfdb44"
MODEL_DIR = "D:/C_data/SpotTruth/new_idea/sarcasm_detection/output"


def load_model():
    """加载LoRA模型"""
    print("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(CACHE_DIR)
    base_model = AutoModelForSequenceClassification.from_pretrained(CACHE_DIR, num_labels=2)
    model = PeftModel.from_pretrained(base_model, MODEL_DIR)
    model.eval()
    return model, tokenizer


def predict(text, model, tokenizer):
    """预测单条文本"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)
        pred = torch.argmax(probs, dim=-1).item()
        confidence = probs[0][pred].item()
    return pred, confidence


# 优化扩展后的验证集
# 核心改进：
# 1. 强化反讽案例的典型性（避免模糊地带）
# 2. 修正翻译错误，符合英文反讽表达习惯
# 3. 扩展场景覆盖（职场、校园、社交、情感、公共事件等）
# 4. 区分不同强度的反讽（强反讽/弱反讽）
NEW_TEST_DATA = {
    "irony": [
        # 【强反讽】消费场景（核心反讽，无歧义）
        ("太好了，刚买三天就降价，血赚不亏", "Great, the price dropped three days after I bought it, what a huge profit"),
        ("服务态度绝了，等两小时没人理，太贴心了", "The service is amazing, waited two hours with no one attending, so thoughtful"),
        ("质量超棒，用一次就坏，真值", "The quality is superb, broke after one use, totally worth it"),
        ("包装精美到爆，里面东西碎成渣，太值了", "The packaging is stunning, but the item inside is smashed to pieces, so worth it"),
        ("物流快到离谱，迟到一整天，太有效率了", "The delivery is incredibly fast, arrived a whole day late, so efficient"),
        ("商家太良心，给差评就打电话辱骂，太感动了", "The seller is so ethical, called to insult me for a bad review, so touching"),
        ("性价比天花板，花一百块买个废品，血赚", "The cost-performance is top-tier, spent 100 yuan on garbage, huge profit"),
        ("客服太专业，问啥都不懂，解决问题超快", "Customer service is so professional, knows nothing about my question, solved it super fast"),

        # 【强反讽】职场场景（高频反讽场景）
        ("今天太幸运了，被老板点名加班到凌晨，太幸福了", "I'm so lucky today, the boss asked me to work overtime till midnight, so happy"),
        ("工资涨得真快，就涨50块，够买杯奶茶了，太慷慨了", "Salary increased so fast, only 50 yuan, enough for a milk tea, so generous"),
        ("工作轻松到飞起，每天干12小时，毫无压力", "The job is extremely easy, work 12 hours a day, no pressure at all"),
        ("团队氛围超好，勾心斗角到下班，太和谐了", "Team atmosphere is great, office politics till off work, so harmonious"),
        ("老板太体恤员工，周末团建爬山，太贴心了", "The boss cares so much about employees, team building hiking on weekends, so thoughtful"),

        # 【强反讽】生活/社交场景
        ("天气好到炸裂，零下10度冻成狗，太舒服了", "The weather is fantastic, freezing at -10°C, so comfortable"),
        ("电影精彩到窒息，看10分钟就睡死过去，太值票价了", "The movie is breathtaking, fell asleep after 10 minutes, totally worth the ticket"),
        ("考试简单到哭，题目全没见过，稳过了", "The exam is ridiculously easy, never seen any of the questions, definitely passing"),
        ("地铁宽敞到爆，挤得脚不沾地，太舒服了", "The subway is extremely spacious, squeezed off the ground, so comfortable"),
        ("朋友太够意思，借我钱就失联，太靠谱了", "My friend is so loyal, disappeared after borrowing money from me, so reliable"),

        # 【强反讽】网络场景
        ("视频清晰到瞎，马赛克比画面大，太高清了", "The video is crystal clear, mosaics bigger than the picture, so high-definition"),
        ("网速快到逆天，打开网页要10分钟，太流畅了", "Internet speed is incredible, takes 10 minutes to open a webpage, so smooth"),
        ("教程详细到爆，看完还是零基础，太实用了", "The tutorial is extremely detailed, still a beginner after watching, so practical"),
        ("文章写得太好，每个字都认识连起来看不懂，太有水平了", "The article is brilliantly written, know every word but not the whole meaning, so profound"),

        # 【弱反讽】轻度反讽（更贴近日常表达）
        ("今天真开心，又要加班了呢", "I'm so happy today, have to work overtime again~"),
        ("这菜真好吃，就是咸得能齁死人", "This dish is delicious, just salty enough to kill someone"),
        ("这衣服真好看，就是穿一次就起球", "This clothes is beautiful, just pills after one wear"),
        ("这家店真火，就是等一小时才上菜", "This restaurant is popular, just wait an hour for food"),
        ("这手机真好用，就是一天充三次电", "This phone is great, just needs charging three times a day"),

        # 【文化特色反讽】中文特有的反讽表达
        ("你可真行，把这事办得一团糟", "You're really something, messed this up completely"),
        ("可真是辛苦你了，啥也没干成", "You must be exhausted, accomplished absolutely nothing"),
        ("还得是你，关键时候掉链子", "As expected of you, let us down at the critical moment"),
        ("真有你的，又把锅甩给别人", "You're unbelievable, passing the buck to others again"),
        ("算你厉害，又迟到还找借口", "You're so awesome, late again and making excuses"),
    ],
    
    "normal": [
        # 【正面评论】无反讽，明确正向
        ("商品质量极佳，用料扎实，推荐购买", "The product quality is excellent, solid materials, recommend buying"),
        ("物流速度超快，次日达，包装完好无损", "Delivery is super fast, next-day arrival, packaging intact"),
        ("性价比超高，比预期好太多，值得回购", "High cost-performance, much better than expected, worth repurchasing"),
        ("客服态度热情，解答问题耐心，满分", "Customer service is enthusiastic, patient in answering questions, full marks"),
        ("和商品描述完全一致，物超所值，好评", "Exactly as described, value for money, good review"),
        ("电影剧情精彩，演员演技在线，值得一看", "The movie has a great plot, actors act well, worth watching"),
        ("餐厅口味正宗，分量足，价格合理", "The restaurant has authentic taste, large portions, reasonable price"),
        ("手机续航超棒，正常使用能用一整天", "Phone battery life is great, lasts a whole day with normal use"),
        ("同事很靠谱，帮忙解决了大问题，太感谢了", "Colleague is reliable, helped solve a big problem, thank you so much"),
        ("天气很舒服，不冷不热，适合出门", "The weather is pleasant, neither cold nor hot, perfect for going out"),

        # 【负面评论】无反讽，明确负向
        ("商品质量极差，用两天就坏了，不推荐", "Product quality is extremely poor, broke after two days, not recommended"),
        ("物流速度极慢，等了一周才到，体验差", "Delivery is extremely slow, arrived after a week, bad experience"),
        ("和商品描述严重不符，实物差太多，差评", "Seriously inconsistent with description, actual product is much worse, bad review"),
        ("客服态度恶劣，爱答不理，投诉到底", "Customer service is rude, unresponsive, will complain to the end"),
        ("性价比极低，价格贵质量差，千万别买", "Extremely low cost-performance, expensive and poor quality, never buy"),
        ("电影剧情拉胯，演员演技差，浪费时间", "The movie plot is terrible, actors act badly, waste of time"),
        ("餐厅口味难吃，分量少，价格还贵", "The restaurant food is terrible, small portions, expensive"),
        ("手机卡顿严重，发热厉害，不建议购买", "Phone lags badly, overheats seriously, not recommended"),
        ("同事不靠谱，甩锅第一名，千万别合作", "Colleague is unreliable, expert at passing the buck, never cooperate"),
        ("天气极差，又冷又下雨，不适合出门", "The weather is terrible, cold and rainy, not suitable for going out"),

        # 【中性评论】无情绪倾向，客观描述
        ("商品质量中等，符合预期，正常使用", "Product quality is average, meets expectations, usable normally"),
        ("物流速度一般，3天到达，包装正常", "Delivery speed is average, arrived in 3 days, normal packaging"),
        ("价格适中，质量中等，可买可不买", "Price is moderate, quality average, optional to buy"),
        ("客服回复及时，问题未解决，态度尚可", "Customer service replied promptly, problem unsolved, attitude acceptable"),
        ("电影剧情一般，特效还行，可看可不看", "Movie plot is average, special effects okay, optional to watch"),
        ("餐厅口味一般，分量适中，价格合理", "Restaurant taste is average, portions moderate, reasonable price"),
        ("手机性能中等，续航一般，性价比普通", "Phone performance is average, battery life normal, ordinary cost-performance"),
        ("同事工作能力一般，态度尚可，合作正常", "Colleague's ability is average, attitude okay, normal cooperation"),
        ("天气一般，有点风，出门需要带外套", "The weather is average, a bit windy, need to take a coat when going out"),
    ]
}


def main():
    # 加载模型
    model, tokenizer = load_model()
    
    print("\n" + "="*60)
    print("New Data Evaluation (Chinese -> English)")
    print("="*60)
    
    # 评估irony
    print("\n[Irony/Sarcasm Samples]")
    irony_correct = 0
    irony_total = 0
    
    for cn_text, en_text in NEW_TEST_DATA["irony"]:
        pred, conf = predict(en_text, model, tokenizer)
        status = "[OK]" if pred == 1 else "[X]"
        if pred == 1:
            irony_correct += 1
        irony_total += 1
        print(f"  {status} Pred: {'Irony' if pred==1 else 'Normal'} ({conf:.0%})")
        print(f"      CN: {cn_text}")
        print(f"      EN: {en_text[:60]}..." if len(en_text) > 60 else f"      EN: {en_text}")
    
    irony_acc = irony_correct / irony_total if irony_total > 0 else 0
    print(f"\n  Irony Accuracy: {irony_correct}/{irony_total} = {irony_acc:.1%}")
    
    # 评估normal
    print("\n[Normal Samples]")
    normal_correct = 0
    normal_total = 0
    
    for cn_text, en_text in NEW_TEST_DATA["normal"]:
        pred, conf = predict(en_text, model, tokenizer)
        status = "[OK]" if pred == 0 else "[X]"
        if pred == 0:
            normal_correct += 1
        normal_total += 1
        print(f"  {status} Pred: {'Irony' if pred==1 else 'Normal'} ({conf:.0%})")
        print(f"      CN: {cn_text}")
        print(f"      EN: {en_text[:60]}..." if len(en_text) > 60 else f"      EN: {en_text}")
    
    normal_acc = normal_correct / normal_total if normal_total > 0 else 0
    print(f"\n  Normal Accuracy: {normal_correct}/{normal_total} = {normal_acc:.1%}")
    
    # 总计
    total_correct = irony_correct + normal_correct
    total = irony_total + normal_total
    total_acc = total_correct / total if total > 0 else 0
    
    print("\n" + "="*60)
    print(f"Overall Accuracy: {total_correct}/{total} = {total_acc:.1%}")
    print("="*60)
    
    # 错误分析
    print("\n【Error Analysis】")
    print("False Negatives (Irony predicted as Normal):")
    fn_count = 0
    for cn_text, en_text in NEW_TEST_DATA["irony"]:
        pred, _ = predict(en_text, model, tokenizer)
        if pred == 0:
            fn_count += 1
            print(f"  - {cn_text}")
    if fn_count == 0:
        print("  - None")
    
    print("\nFalse Positives (Normal predicted as Irony):")
    fp_count = 0
    for cn_text, en_text in NEW_TEST_DATA["normal"]:
        pred, _ = predict(en_text, model, tokenizer)
        if pred == 1:
            fp_count += 1
            print(f"  - {cn_text}")
    if fp_count == 0:
        print("  - None")


if __name__ == "__main__":
    main()