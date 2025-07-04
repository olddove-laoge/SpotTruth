# 模型调用示例代码
import os
import jieba
import re
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.layers import Layer
from gensim.models import Word2Vec
from transformers import BertTokenizer, TFBertModel
from tensorflow.keras.preprocessing.sequence import pad_sequences

from tensorflow.keras.saving import register_keras_serializable

# 自定义层定义（独立工作版本）
@register_keras_serializable(package='Custom')
class BertIntegrationLayer(Layer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dtype = tf.int32
        self.bert_model = None
    
    def build(self, input_shape):
        # 延迟加载BERT模型
        if self.bert_model is None:
            self.bert_model = TFBertModel.from_pretrained('bert-base-chinese', from_pt=True)
        self._trainable_weights = []
    
    def call(self, inputs):
        input_ids = tf.cast(inputs[0], self._dtype)
        attention_mask = tf.cast(inputs[1], self._dtype)
        outputs = self.bert_model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        return outputs.last_hidden_state
    
    def compute_output_shape(self, input_shape):
        return (input_shape[0][0], input_shape[0][1], 768)

# 1. 加载模型
# 先加载BERT模型用于自定义层
try:
    bert_model = TFBertModel.from_pretrained('bert-base-chinese', from_pt=True)
except Exception as e:
    print(f"BERT模型加载失败: {e}")
    exit()

# 使用custom_objects加载分类模型
model = load_model(
    r'AIGC\Comment_crawling_and_analysis\review_classifier.keras',
    custom_objects={'BertIntegrationLayer': BertIntegrationLayer}
)
w2v_model = Word2Vec.load(r'AIGC\Comment_crawling_and_analysis\word2vec_model.bin')
bert_tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')

# 2. 预处理函数
def preprocess_text(text):
    # 文本清洗
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 分词
    tokens = [w for w in jieba.lcut(text) if w.strip()]
    
    # 构建Word2Vec词汇表
    vocab = w2v_model.wv.index_to_key
    word_index = {word: idx+1 for idx, word in enumerate(vocab)}
    
    # 转换为Word2Vec序列
    w2v_seq = [word_index.get(word, 0) for word in tokens]
    w2v_padded = pad_sequences([w2v_seq], maxlen=128, padding='post', dtype='int32')
    
    # 准备BERT输入
    bert_input = bert_tokenizer.encode_plus(
        text,
        padding='max_length',
        truncation=True,
        max_length=128,
        return_tensors='np'
    )
    
    return w2v_padded, bert_input['input_ids'], bert_input['attention_mask']

# 分句函数
def split_sentences(text):
    """改进的中文分句函数"""
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

# 3. 示例预测
def predict_sentiment(text, sentence_level=True):
    if sentence_level:
        # 分句处理
        sentences = split_sentences(text)
        if not sentences:
            return {'sentiment': '中性', 'confidence': 0, 'raw_score': 0.5}
        
        # 分析每个分句
        sentence_scores = []
        for sent in sentences:
            w2v_input, bert_ids, bert_mask = preprocess_text(sent)
            score = model.predict([w2v_input, bert_ids, bert_mask])[0][0]
            sentence_scores.append(float(score))
        
        # 增加整体句子分析
        w2v_input_full, bert_ids_full, bert_mask_full = preprocess_text(text)
        full_text_score = model.predict([w2v_input_full, bert_ids_full, bert_mask_full])[0][0]
        
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
        # 整体处理（原逻辑）
        w2v_input, bert_ids, bert_mask = preprocess_text(text)
        raw_score = model.predict([w2v_input, bert_ids, bert_mask])[0][0]
    
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

# 4. 使用示例
if __name__ == '__main__':
    test_texts = [
        "给个好评骗一下更多的人😁，特别美味，色香味俱全，值了。真棒👍🏻非常满意。,",
        "限时特价买的，限时一结束就降20元，营销有点问题，不过质量还可以，给手机充电很快",
        "到货很快，就是箱子烂了，不过没少东西。客服回复很快"
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
        
        # 检测并处理情感关键词
        positive_words = ['好','优秀','棒','满意','赞','推荐','喜欢','超赞','态度好','速度快','质量好']
        sarcasm_words = ['骗','假装','阴阳','讽刺','反话','假的','快跑','别信']
        neutral_phrases = ['不确定','不知道']
        negative_words = ['差','不好','糟糕','不行','不推荐','烂','垃圾','坏','坏的','不满意','差劲','不满','不好用','不舒服','不爽','难用','难受','难看']
        
        # 检测关键词
        has_positive = any(word in test_text for word in positive_words)
        has_sarcasm = any(word in test_text for word in sarcasm_words)
        has_negative = any(word in test_text for word in negative_words) and \
                      not any(phrase in test_text for phrase in neutral_phrases)
        
        # 优先处理正面评价
        if has_positive and not has_negative:
            print("※ 注意: 检测到正面评价内容 ※")
            result['raw_score'] = min(1.0, result['raw_score'] * 1.2)  # 增强正面分数
            result['sentiment'] = '正面'
            result['confidence'] = result['raw_score']
        elif has_sarcasm:
            print("※ 警告: 检测到可能包含讽刺内容 ※")
            result['raw_score'] = max(0, min(1, 1 - result['raw_score']))
            result['sentiment'] = '负面' if result['raw_score'] <= 0.5 else '正面'
            result['confidence'] = result['raw_score'] if result['sentiment'] == '正面' else 1 - result['raw_score']
        elif has_negative:
            print("※ 注意: 检测到负面评价内容 ※")
            result['raw_score'] = max(0, result['raw_score'] * 0.8)  # 降低负面惩罚力度
            result['sentiment'] = '负面' if result['raw_score'] <= 0.5 else '正面'
            result['confidence'] = result['raw_score'] if result['sentiment'] == '正面' else 1 - result['raw_score']
