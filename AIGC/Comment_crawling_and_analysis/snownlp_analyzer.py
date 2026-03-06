# 基于snowNLP的情感分析器
import re
import numpy as np
from snownlp import SnowNLP

def split_sentences(text):
    """中文分句函数（与现有实现一致）"""
    # 先按常见标点分句
    sentences = re.split(r'([，,。！？；\.\!\?;])', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # 合并标点符号回前一句
    merged = []
    for i in range(0, len(sentences)-1, 2):
        merged.append(sentences[i] + sentences[i+1])
    if len(sentences) % 2 == 1:
        merged.append(sentences[-1])
    
    # 对长句进一步拆分
    final_sentences = []
    for sent in merged:
        # 如果有转折词则拆分
        if any(word in sent for word in ['但','但是','然而','不过','却']):
            parts = re.split(r'(但|但是|然而|不过|却)', sent)
            parts = [p.strip() for p in parts if p.strip()]
            for i in range(0, len(parts)-1, 2):
                final_sentences.append(parts[i] + parts[i+1])
            if len(parts) % 2 == 1:
                final_sentences.append(parts[-1])
        else:
            final_sentences.append(sent)
    
    return final_sentences

def predict_sentiment(text, sentence_level=True):
    """基于snowNLP的情感分析（接口与现有实现一致）"""
    if sentence_level:
        # 分句处理
        sentences = split_sentences(text)
        if not sentences:
            return {'sentiment': '中性', 'confidence': 0, 'raw_score': 0.5}
        
        # 关键词定义
        sarcasm_words = ['骗', '假装', '阴阳', '讽刺', '反话','假的','快跑','别信']
        neutral_phrases = [ '不确定', '不知道']  # 中性表述
        negative_words = ['差', '不好', '糟糕', '不行', '不推荐','烂','垃圾','坏','坏的','不满意','差劲','不满','不好用','不舒服','不爽','难用','难受','难看']
        positive_words = ['好', '棒', '优秀', '完美', '推荐','满意','好用','舒服','爽','喜欢','超值','值得','不错','很好','非常好','太棒了','太赞了','没得说']

        # 分析每个分句
        sentence_scores = []
        for sent in sentences:
            s = SnowNLP(sent)
            raw_score = s.sentiments
            
            # 计算关键词出现次数（优先处理负面词）
            negative_count = min(3, sum(1 for word in negative_words if word in sent))
            positive_count = 0 if negative_count > 0 else min(3, sum(1 for word in positive_words if word in sent))
            
            # 应用情感调整（不会同时应用正负调整）
            if negative_count > 0:
                raw_score = max(0.0, raw_score - 0.22 * negative_count)
            elif positive_count > 0:
                raw_score = min(1.0, raw_score + 0.2 * positive_count)
            
            # 检查中性词
            if any(phrase in sent for phrase in neutral_phrases):
                raw_score = 0.5  # 直接设置为中性分数
            
            sentence_scores.append(raw_score)
        
        # 增加整体句子分析
        full_text_score = SnowNLP(text).sentiments
        
        # 整体级别的关键词检测（优先处理负面词）
        has_negative = any(word in text for word in negative_words) and \
                      not any(phrase in text for phrase in neutral_phrases)
        has_positive = not has_negative and any(word in text for word in positive_words)
        
        if has_negative:
            full_text_score = max(0, full_text_score * 0.8)
        elif has_positive:
            full_text_score = min(1, full_text_score * 1.1)

        # 最后处理讽刺词影响
        has_sarcasm = any(word in text for word in sarcasm_words)
        if has_sarcasm:
            # 处理分句得分
            sentence_scores = [
                max(0, min(1, 1 - score)) if score > 0.5 else score
                for score in sentence_scores
            ]
            
            # 处理整体得分
            if full_text_score > 0.5:
                full_text_score = max(0, min(1, 1 - full_text_score))
            elif full_text_score > 0.35:
                full_text_score = max(0, full_text_score - 0.2)
            
            sentence_scores.append(raw_score)
        
        # 增加整体句子分析
        full_text_score = SnowNLP(text).sentiments
        
        # 整体级别的关键词检测（作为补充）
        has_sarcasm = any(word in text for word in sarcasm_words)
        has_negative = any(word in text for word in negative_words) and \
                      not any(phrase in text for phrase in neutral_phrases)
        has_positive = any(word in text for word in positive_words)
        
        # 整体级别的分数调整
        if has_sarcasm:
            if full_text_score > 0.5:
                full_text_score = max(0, min(1, 1 - full_text_score))
            elif full_text_score > 0.35:
                full_text_score = max(0, full_text_score - 0.2)
        elif has_negative:
            full_text_score = max(0, full_text_score * 0.8)
        elif has_positive:
            full_text_score = min(1, full_text_score * 1.1)

        # 优化后的情感计算算法
        # 1. 动态权重计算（更平缓的曲线）
        weights = []
        for score in sentence_scores:
            # 调整后的S型曲线，斜率更平缓
            weight = 1 + 0.6 / (1 + np.exp(8*(score-0.45)))
            weights.append(weight)
        
        # 2. 位置权重（后面的句子稍高）
        weights = [w * (1 + 0.02*i) for i, w in enumerate(weights)]
        
        # 3. 计算加权分数（保留平滑处理）
        weighted_scores = [0.15 + 0.7 * score for score in sentence_scores]
        sentence_score = np.average(weighted_scores, weights=weights)
        
        # 4. 结合整体分析（0.7分句 + 0.3整体）
        raw_score = sentence_score * 0.7 + full_text_score * 0.3
        
        # 4. 负面内容检测（调整后的条件）
        strong_negative = any(s < 0.2 for s in sentence_scores)
        moderate_negative = any(s < 0.3 for s in sentence_scores)
        
        if strong_negative:
            # 强烈负面内容：适度降低分数
            raw_score = raw_score * 0.8
        elif moderate_negative:
            # 一般负面内容：轻微调整
            raw_score = raw_score * 0.95
    else:
        # 整体处理
        s = SnowNLP(text)
        raw_score = s.sentiments
    
    # 优化后的最终判断逻辑
    if raw_score > 0.6:
        sentiment = '正面'
        confidence = raw_score
    elif raw_score < 0.35:
        if any(s < 0.25 for s in (sentence_scores if sentence_level else [raw_score])):
            sentiment = '负面'
            confidence = 1 - raw_score
        else:
            sentiment = '中性'
            confidence = 1 - abs(raw_score - 0.5)
    else:
        sentiment = '中性'
        confidence = 1 - abs(raw_score - 0.5)
    
    result = {
        'sentiment': sentiment,
        'confidence': float(confidence),
        'raw_score': float(raw_score),
        'sentence_scores': sentence_scores if sentence_level else None,
        'sentences': split_sentences(text) if sentence_level else None
    }
    
    if sentence_level:
        result['full_text_score'] = float(full_text_score)
    
    return result

# 使用示例
if __name__ == '__main__':
    test_texts = [
        "充电宝非常好用，给我的红米K50至尊版充电可以55W，和宣传的一样，非常满意。,",  # 中性表述测试
        "给个好评骗一下更多的人😁，特别美味，色香味俱全，值了。真棒👍🏻",  # 强烈负面
        "服务太好了，使用充电宝遇到点问题，和客服说一下，立马就给我解决了。充电宝充的也很快,负面",  # 中性
        "服务售后各种小问题上来就是推脱，必须强硬才给解决。好好说问题只能敷衍"  # 讽刺内容
    ]
    
    for test_text in test_texts:
        result = predict_sentiment(test_text)
        print(f"\n=== 分析结果 ===")
        print(f"输入文本: {test_text}")
        print("\n分句分析:")
        for i, (sent, score) in enumerate(zip(result['sentences'], result['sentence_scores'])):
            print(f" {i+1}. {sent} (分句得分: {score:.4f})")
        if 'full_text_score' in result:
            print(f"\n整体分析得分: {result['full_text_score']:.4f}")
        print(f"综合得分: {result['raw_score']:.4f} ({result['sentiment']})")
        print(f"置信度: {result['confidence']:.2%}")
        
