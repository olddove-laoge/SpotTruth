"""意图验证器 - 自动检查并修正执行参数

提供:
- 意图一致性验证（用户说的 vs 代码要做的）
- 自动参数修正（发现不一致时自动调整）
- 执行前/后质量检查
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from agent.infrastructure import logger


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    original_params: Dict
    corrected_params: Dict
    warnings: List[str]
    auto_fixed: bool


class IntentValidator:
    """意图验证器"""

    @staticmethod
    def validate_analysis_params(
        user_input: str,
        intent_data: Dict,
        current_product: str = ""
    ) -> ValidationResult:
        """验证分析参数，自动修正不一致

        返回:
            ValidationResult: 包含修正后的参数和警告信息
        """
        original = intent_data.copy()
        corrected = intent_data.copy()
        warnings = []
        auto_fixed = False

        # 1. 提取用户明确提到的平台
        user_platforms = IntentValidator._extract_platforms_from_input(user_input)

        # 2. 获取当前参数
        need_taobao = corrected.get('need_taobao', False)
        need_xhs = corrected.get('need_xiaohongshu', False)
        need_heimao = corrected.get('need_heimao', False)

        # 3. 验证平台一致性
        if user_platforms:
            # 用户明确指定了平台
            if 'xiaohongshu' in user_platforms and not need_xhs:
                warnings.append("用户提到小红书，但 need_xiaohongshu=false，自动修正")
                corrected['need_xiaohongshu'] = True
                need_xhs = True
                auto_fixed = True

            if 'heimao' in user_platforms and not need_heimao:
                warnings.append("用户提到黑猫/投诉，但 need_heimao=false，自动修正")
                corrected['need_heimao'] = True
                need_heimao = True
                auto_fixed = True

            if 'taobao' in user_platforms and not need_taobao:
                warnings.append("用户提到淘宝，但 need_taobao=false，自动修正")
                corrected['need_taobao'] = True
                need_taobao = True
                auto_fixed = True

            # 4. 如果用户明确指定了某些平台，未提及的平台应该设为false
            # 除非用户说"全面分析"、"所有平台"等
            explicit_all = any(kw in user_input for kw in ['全部', '所有', '全面', '综合'])

            if not explicit_all:
                if 'xiaohongshu' in user_platforms and need_taobao and 'taobao' not in user_platforms:
                    warnings.append("用户只提到小红书，但 need_taobao=true，自动修正为false")
                    corrected['need_taobao'] = False
                    auto_fixed = True

                if 'heimao' in user_platforms and need_taobao and 'taobao' not in user_platforms:
                    warnings.append("用户只提到黑猫，但 need_taobao=true，自动修正为false")
                    corrected['need_taobao'] = False
                    auto_fixed = True

        # 5. 确保至少有一个平台
        if not (corrected.get('need_taobao') or corrected.get('need_xiaohongshu') or corrected.get('need_heimao')):
            warnings.append("没有指定任何平台，默认添加淘宝")
            corrected['need_taobao'] = True
            auto_fixed = True

        # 6. 验证商品名
        brand = corrected.get('brand', '')
        product = corrected.get('product', '')

        if not brand and not product and not current_product:
            warnings.append("商品信息为空，可能需要用户澄清")

        # 7. 检查上下文引用
        if current_product and IntentValidator._is_reference_query(user_input):
            # 用户用"那xx呢"引用当前商品
            if not brand and not product:
                # 从current_product提取品牌和商品
                parts = current_product.split(maxsplit=1)
                if len(parts) >= 1:
                    corrected['brand'] = parts[0]
                if len(parts) >= 2:
                    corrected['product'] = parts[1]
                warnings.append(f"检测到上下文引用，自动使用当前商品: {current_product}")
                auto_fixed = True

        # 打印验证日志
        if warnings:
            logger.warning("=" * 60)
            logger.warning("🛡️ 意图验证警告:")
            for w in warnings:
                logger.warning(f"   ⚠️  {w}")
            if auto_fixed:
                logger.warning(f"   ✅ 已自动修正参数")
            logger.warning("=" * 60)

        is_valid = len(warnings) == 0 or auto_fixed

        return ValidationResult(
            is_valid=is_valid,
            original_params=original,
            corrected_params=corrected,
            warnings=warnings,
            auto_fixed=auto_fixed
        )

    @staticmethod
    def _extract_platforms_from_input(user_input: str) -> List[str]:
        """从用户输入提取提到的平台"""
        platforms = []
        input_lower = user_input.lower()

        # 小红书
        if any(kw in input_lower for kw in ['小红书', 'xhs', '笔记']):
            platforms.append('xiaohongshu')

        # 黑猫投诉
        if any(kw in input_lower for kw in ['黑猫', '投诉', 'tousu']):
            platforms.append('heimao')

        # 淘宝
        if any(kw in input_lower for kw in ['淘宝', '天猫', '评论', '评价']):
            platforms.append('taobao')

        return platforms

    @staticmethod
    def _is_reference_query(user_input: str) -> bool:
        """检测是否是引用当前商品的查询"""
        reference_patterns = [
            r'那\w+呢',      # 那xx呢
            r'\w+呢',        # xx呢（短句）
            r'.*怎么样',     # xx怎么样
            r'.*如何',       # xx如何
        ]
        for pattern in reference_patterns:
            if re.search(pattern, user_input):
                return True
        return False

    @staticmethod
    def validate_crawl_result(
        platform: str,
        expected_count: int,
        actual_count: int,
        error_msg: str = ""
    ) -> Tuple[bool, str]:
        """验证爬取结果质量

        返回:
            (是否成功, 状态信息)
        """
        if error_msg:
            logger.error(f"❌ [{platform}] 爬取失败: {error_msg}")
            return False, f"失败: {error_msg}"

        if actual_count == 0:
            logger.warning(f"⚠️  [{platform}] 未获取到数据")
            return False, "未获取到数据"

        if actual_count < expected_count * 0.5:
            logger.warning(f"⚠️  [{platform}] 获取数据较少: {actual_count}/{expected_count}")
            return True, f"部分成功: {actual_count}条（预期{expected_count}条）"

        logger.info(f"✅ [{platform}] 爬取成功: {actual_count}条")
        return True, f"成功: {actual_count}条"

    @staticmethod
    def validate_analysis_result(
        stats: Dict,
        platform: str
    ) -> List[str]:
        """验证分析结果合理性

        返回:
            警告列表（空列表表示正常）
        """
        warnings = []

        total = stats.get('total', 0)
        if total == 0:
            return ["没有可分析的数据"]

        positive_rate = stats.get('positive_rate', 0)
        negative_rate = stats.get('negative_rate', 0)
        sarcasm_count = stats.get('sarcasm_count', 0)

        # 检查极端分布
        if positive_rate == 1.0:
            warnings.append(f"[{platform}] 好评率100%，可能存在异常")
        if negative_rate == 1.0:
            warnings.append(f"[{platform}] 差评率100%，可能存在异常")

        # 检查讽刺率
        if total > 0:
            sarcasm_rate = sarcasm_count / total
            if sarcasm_rate > 0.3:
                warnings.append(f"[{platform}] 疑似虚假好评比例过高: {sarcasm_rate:.1%}")

        # 检查样本量
        if total < 10:
            warnings.append(f"[{platform}] 样本量较少({total}条)，结果可能不具代表性")

        return warnings


# 便捷函数
def validate_and_correct(
    user_input: str,
    intent_data: Dict,
    current_product: str = ""
) -> Dict:
    """验证并自动修正参数（便捷函数）

    返回修正后的intent_data
    """
    result = IntentValidator.validate_analysis_params(
        user_input=user_input,
        intent_data=intent_data,
        current_product=current_product
    )

    if result.warnings:
        print(f"\n🛡️  意图验证 ({len(result.warnings)}个警告):")
        for w in result.warnings:
            print(f"   ⚠️  {w}")
        if result.auto_fixed:
            print(f"   ✅ 已自动修正")
        print()

    return result.corrected_params
