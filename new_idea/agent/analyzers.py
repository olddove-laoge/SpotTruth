"""AI分析器 - 讽刺检测、情感分析、品类分类"""

import os
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForMaskedLM
from peft import PeftModel

from config import analysis as analysis_config, paths as paths_config, CATEGORY_KEYWORDS
from agent.infrastructure import logger, timed_tool, ToolError, with_retry
from agent.models import SentimentType, SentimentResult, SarcasmResult, Comment, SourceType


class CategoryClassifier:
    """商品品类分类器 - 基于关键词规则"""

    def __init__(self):
        self.keywords = CATEGORY_KEYWORDS

    def classify(self, product_name: str) -> str:
        """判断商品品类"""
        product_lower = product_name.lower()
        for category, keywords in self.keywords.items():
            if any(kw in product_name or kw in product_lower for kw in keywords):
                return category
        return "electronics"  # 默认品类


class SarcasmDetector:
    """讽刺检测器 - 基于TOSPrompt"""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.yes_token_id = None
        self.no_token_id = None
        self._load_model()

    def _load_model(self):
        """加载TOSPrompt模型"""
        if not os.path.exists(paths_config.sarcasm_dir):
            logger.warning(f"讽刺检测模型目录不存在: {paths_config.sarcasm_dir}")
            return

        try:
            self.model = AutoModelForMaskedLM.from_pretrained(paths_config.sarcasm_dir)
            self.tokenizer = AutoTokenizer.from_pretrained(paths_config.sarcasm_dir)
            self.yes_token_id = self.tokenizer.encode("是", add_special_tokens=False)[0]
            self.no_token_id = self.tokenizer.encode("否", add_special_tokens=False)[0]
            self.model.eval()
            logger.info("✅ 讽刺检测模型加载成功")
        except Exception as e:
            logger.error(f"讽刺检测模型加载失败: {e}")
            self.model = None

    def is_available(self) -> bool:
        """检查模型是否可用"""
        return self.model is not None and self.tokenizer is not None

    def detect(self, text: str, topic: str = "") -> SarcasmResult:
        """检测单条评论是否为讽刺"""
        if not self.is_available():
            logger.warning(f"🎭 [讽刺检测] 模型不可用，跳过检测: {text[:30]}...")
            return SarcasmResult(text=text, is_sarcasm=False, confidence=0.0, topic=topic)

        prompt = f"{text} 是对 {topic} 的讽刺吗？[MASK]"
        logger.info(f"🎭 [讽刺检测] 输入文本: {text}")
        logger.info(f"🎭 [讽刺检测] 构造Prompt: {prompt}")

        try:
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=128,
                padding=True
            )

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits

                # 找到[MASK]位置
                mask_token_id = self.tokenizer.mask_token_id
                mask_positions = (inputs.input_ids == mask_token_id).nonzero(as_tuple=True)

                if len(mask_positions[1]) == 0:
                    logger.error(f"🎭 [讽刺检测] 未找到[MASK]位置")
                    return SarcasmResult(text=text, is_sarcasm=False, confidence=0.0, topic=topic)

                mask_idx = mask_positions[1][0].item()
                mask_logits = logits[0, mask_idx, :]

                yes_logit = mask_logits[self.yes_token_id].item()
                no_logit = mask_logits[self.no_token_id].item()

                logger.info(f"🎭 [讽刺检测] 原始Logits -> '是': {yes_logit:.4f}, '否': {no_logit:.4f}")

                # Softmax计算概率
                exp_yes = np.exp(yes_logit)
                exp_no = np.exp(no_logit)
                total = exp_yes + exp_no
                yes_prob = exp_yes / total
                no_prob = exp_no / total

                logger.info(f"🎭 [讽刺检测] 计算概率 -> '是': {yes_prob:.4f}, '否': {no_prob:.4f}")

                is_sarcasm = yes_prob > no_prob
                confidence = yes_prob if is_sarcasm else no_prob

                result_emoji = "✅ 是" if is_sarcasm else "❌ 否"
                logger.info(f"🎭 [讽刺检测] 最终结果 -> 是否讽刺: {result_emoji}, 置信度: {confidence:.4f}")

                return SarcasmResult(
                    text=text,
                    is_sarcasm=is_sarcasm,
                    confidence=float(confidence),
                    topic=topic
                )

        except Exception as e:
            logger.error(f"🎭 [讽刺检测] 检测失败: {e}")
            return SarcasmResult(text=text, is_sarcasm=False, confidence=0.0, topic=topic)

    def batch_detect(self, texts: List[str], topic: str = "") -> List[SarcasmResult]:
        """批量检测"""
        return [self.detect(text, topic) for text in texts]


class SentimentAnalyzer:
    """情感分析器 - 基于LoRA模型"""

    def __init__(self):
        self.tokenizer = None
        self.models: Dict[str, Any] = {}
        self._model_status: Dict[str, str] = {}
        self._load_models()

    def _load_models(self):
        """加载所有品类模型配置（延迟加载实际权重）"""
        for category in CATEGORY_KEYWORDS.keys():
            model_path = os.path.join(paths_config.lora_dir, category)
            if os.path.exists(model_path):
                self.models[category] = {
                    "path": model_path,
                    "model": None,
                    "tokenizer": None,
                    "loaded": False
                }
                self._model_status[category] = "unloaded"
            else:
                self._model_status[category] = "not_found"
                logger.warning(f"品类模型目录不存在: {model_path}")

    def _get_model(self, category: str) -> Tuple[Optional[Any], Optional[Any]]:
        """获取模型（延迟加载）"""
        category = category.lower()

        if category not in self.models:
            if "electronics" in self.models:
                logger.info(f"品类{category}未找到，使用默认electronics模型")
                category = "electronics"
            else:
                return None, None

        if self.models[category].get("loaded"):
            return self.models[category]["model"], self.models[category]["tokenizer"]

        # 尝试加载模型
        try:
            model_path = self.models[category]["path"]
            base_model = AutoModelForSequenceClassification.from_pretrained(
                paths_config.cache_dir,
                num_labels=2
            )
            model = PeftModel.from_pretrained(base_model, model_path)
            model = model.merge_and_unload()
            tokenizer = AutoTokenizer.from_pretrained(paths_config.cache_dir)

            self.models[category]["model"] = model
            self.models[category]["tokenizer"] = tokenizer
            self.models[category]["loaded"] = True
            self._model_status[category] = "loaded"

            logger.info(f"✅ {category}模型加载成功")
            return model, tokenizer

        except Exception as e:
            logger.error(f"加载{category}模型失败: {e}")
            self._model_status[category] = f"error: {e}"
            return None, None

    def analyze(self, text: str, category: str = "electronics") -> SentimentResult:
        """分析单条评论情感"""
        model, tokenizer = self._get_model(category)

        if model is None or tokenizer is None:
            # 模型不可用，返回中性结果
            return SentimentResult(
                text=text,
                sentiment=SentimentType.NEUTRAL,
                confidence=0.0
            )

        try:
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)

            with torch.no_grad():
                outputs = model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)
                pred = torch.argmax(probs, dim=-1).item()
                confidence = probs[0][pred].item()

            sentiment = SentimentType.POSITIVE if pred == 1 else SentimentType.NEGATIVE

            return SentimentResult(
                text=text,
                sentiment=sentiment,
                confidence=float(confidence)
            )

        except Exception as e:
            logger.error(f"情感分析失败: {e}")
            return SentimentResult(
                text=text,
                sentiment=SentimentType.NEUTRAL,
                confidence=0.0
            )

    def batch_analyze(self, texts: List[str], category: str = "electronics") -> List[SentimentResult]:
        """批量分析"""
        return [self.analyze(text, category) for text in texts]


class UnifiedAnalyzer:
    """统一分析器 - 整合讽刺检测、LLM判断、情感分析"""

    def __init__(self, llm_client):
        self.sarcasm_detector = SarcasmDetector()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.category_classifier = CategoryClassifier()
        self.llm = llm_client
        self.threshold = analysis_config.sarcasm_threshold

    def analyze_comments(
        self,
        comments: List[Comment],
        product_name: str,
        category: str = ""
    ) -> List[SentimentResult]:
        """
        统一分析评论流程：
        1. 所有评论进行讽刺检测
        2. 讽刺评论 -> LLM判断真实情感
        3. 正常评论 -> LoRA情感分析
        4. 合并结果
        """
        if not comments:
            return []

        # 如果没有提供品类，自动判断
        if not category:
            category = self.category_classifier.classify(product_name)
            logger.info(f"自动判断品类: {category}")

        texts = [c.text for c in comments]

        # 1. 讽刺检测
        logger.info(f"🎭 [批量检测] 开始处理 {len(texts)} 条评论...")
        logger.info(f"🎭 [批量检测] 检测阈值: {self.threshold}")
        sarcasm_results = self.sarcasm_detector.batch_detect(texts, product_name)

        # 分类评论
        normal_indices = []
        sarcasm_indices = []

        for i, result in enumerate(sarcasm_results):
            is_sarcastic = result.is_sarcasm and result.confidence > self.threshold
            status = "🎭 讽刺" if is_sarcastic else "✅ 正常"
            logger.info(f"🎭 [结果{i+1}/{len(texts)}] {status} | 置信度:{result.confidence:.4f} | 文本:{result.text[:40]}...")
            if is_sarcastic:
                sarcasm_indices.append(i)
            else:
                normal_indices.append(i)

        logger.info(f"🎭 [批量检测完成] 总计: {len(sarcasm_indices)}条讽刺，{len(normal_indices)}条正常")

        # 2. 处理讽刺评论 - LLM判断
        llm_results: Dict[int, Dict] = {}
        for idx in sarcasm_indices:
            llm_result = self.llm.judge_sarcasm(texts[idx], product_name)
            llm_results[idx] = llm_result

        # 3. 处理正常评论 - LoRA情感分析
        lora_results: Dict[int, SentimentResult] = {}
        if normal_indices:
            normal_texts = [texts[i] for i in normal_indices]
            analyzed = self.sentiment_analyzer.batch_analyze(normal_texts, category)
            for idx, result in zip(normal_indices, analyzed):
                lora_results[idx] = result

        # 4. 合并结果
        final_results = []
        for i, comment in enumerate(comments):
            if i in llm_results:
                # 讽刺评论 - 使用LLM判断结果
                llm_result = llm_results[i]
                real_sentiment = llm_result.get("real_sentiment", "negative")
                sentiment = SentimentType.POSITIVE if real_sentiment == "positive" else SentimentType.NEGATIVE

                final_results.append(SentimentResult(
                    text=comment.text,
                    sentiment=sentiment,
                    confidence=llm_result.get("confidence", 0.7),
                    is_sarcasm=True,
                    sarcasm_confidence=sarcasm_results[i].confidence,
                    llm_analysis=llm_result.get("reasoning", "")
                ))

            elif i in lora_results:
                # 正常评论 - 使用LoRA结果
                lora_result = lora_results[i]
                final_results.append(SentimentResult(
                    text=comment.text,
                    sentiment=lora_result.sentiment,
                    confidence=lora_result.confidence,
                    is_sarcasm=False,
                    sarcasm_confidence=sarcasm_results[i].confidence if i < len(sarcasm_results) else 0.0
                ))
            else:
                # 异常情况
                final_results.append(SentimentResult(
                    text=comment.text,
                    sentiment=SentimentType.NEUTRAL,
                    confidence=0.0
                ))

        return final_results

    def calculate_statistics(self, results: List[SentimentResult]) -> Dict[str, Any]:
        """计算统计结果"""
        from agent.models import SentimentStatistics

        total = len(results)
        if total == 0:
            return SentimentStatistics().to_dict()

        positive_count = sum(1 for r in results if r.sentiment == SentimentType.POSITIVE)
        negative_count = sum(1 for r in results if r.sentiment == SentimentType.NEGATIVE)
        sarcasm_count = sum(1 for r in results if r.is_sarcasm)

        return {
            "total": total,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "sarcasm_count": sarcasm_count,
            "positive_rate": round(positive_count / total, 2),
            "negative_rate": round(negative_count / total, 2)
        }
