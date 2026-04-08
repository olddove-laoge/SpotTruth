"""工作流层 - 业务流程编排"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from agent.models import (
    AnalysisResult, Comment, ProductInfo, AnalysisStatus,
    SentimentResult, SentimentType
)
from agent.infrastructure import logger, events
from agent.llm_client import LLMClient
from agent.analyzers import UnifiedAnalyzer, CategoryClassifier
from agent.data_service import DataService


@dataclass
class WorkflowContext:
    """工作流上下文"""
    brand: str = ""
    product: str = ""
    need_xiaohongshu: bool = False
    need_heimao: bool = False
    result: Optional[AnalysisResult] = None


class Workflow(ABC):
    """工作流基类"""

    def __init__(
        self,
        data_service: DataService,
        analyzer: UnifiedAnalyzer,
        llm: LLMClient
    ):
        self.data = data_service
        self.analyzer = analyzer
        self.llm = llm

    @abstractmethod
    def execute(self, context: WorkflowContext) -> AnalysisResult:
        """执行工作流"""
        pass


class ProductAnalysisWorkflow(Workflow):
    """商品分析工作流 - 完整的淘宝+可选小红书+可选黑猫分析"""

    def execute(self, context: WorkflowContext) -> AnalysisResult:
        """执行分析流程"""
        product_name = f"{context.brand} {context.product}"
        logger.info(f"开始分析商品: {product_name}")

        # 检查是否已有该商品的分析结果（从context传入）
        if context.result and context.result.product_name == product_name:
            logger.info(f"发现已有 {product_name} 的分析结果，将复用已有数据")
            result = context.result
            # 只补充缺失的数据源
            if context.need_xiaohongshu and not result.xiaohongshu_notes:
                self._fetch_xiaohongshu(context, result)
                self._generate_report(result)  # 重新生成报告包含新数据
            if context.need_heimao and not result.heimao_complaints:
                self._fetch_heimao(context, result)
                self._generate_report(result)
            return result

        # 初始化新结果
        result = AnalysisResult(
            product_name=product_name,
            brand=context.brand,
            status=AnalysisStatus.IN_PROGRESS
        )

        # 触发事件
        events.emit("analysis_started", {"product": product_name})

        try:
            # Step 1: 搜索商品
            self._search_product(context, result)

            # Step 2: 获取淘宝评论
            self._fetch_taobao_comments(context, result)

            # Step 3: 分析评论（讽刺检测+情感分析）
            if result.taobao_comments:
                self._analyze_comments(result)

            # Step 4: 可选 - 小红书
            if context.need_xiaohongshu:
                self._fetch_xiaohongshu(context, result)

            # Step 5: 可选 - 黑猫投诉
            if context.need_heimao:
                self._fetch_heimao(context, result)

            # Step 6: 生成报告
            self._generate_report(result)

            result.status = AnalysisStatus.COMPLETED
            events.emit("analysis_completed", {"product": product_name, "result": result})

        except Exception as e:
            logger.error(f"分析流程出错: {e}")
            result.status = AnalysisStatus.FAILED
            events.emit("analysis_failed", {"product": product_name, "error": str(e)})

        return result

    def _search_product(self, context: WorkflowContext, result: AnalysisResult):
        """搜索商品"""
        logger.info(f"[1/6] 搜索商品: {context.brand} {context.product}")
        search_result = self.data.search_product(
            brand=context.brand,
            product=context.product,
            max_results=5
        )

        if search_result.success and search_result.data:
            result.product_info = search_result.data[0]
            logger.info(f"  ✅ 找到商品: {result.product_info.name}")
        else:
            logger.warning(f"  ⚠️ 未找到商品: {search_result.error}")

    def _fetch_taobao_comments(self, context: WorkflowContext, result: AnalysisResult):
        """获取淘宝评论"""
        logger.info(f"[2/6] 获取淘宝评论...")

        # 优先使用商品链接
        url = result.product_info.url if result.product_info else ""

        comments_result = self.data.get_comments(
            url=url,
            brand=context.brand,
            product=context.product,
            max_count=100
        )

        if comments_result.success and comments_result.data:
            result.taobao_comments = comments_result.data
            logger.info(f"  ✅ 获取到 {len(result.taobao_comments)} 条评论")
        else:
            logger.warning(f"  ⚠️ 获取评论失败: {comments_result.error}")

    def _analyze_comments(self, result: AnalysisResult):
        """分析评论"""
        logger.info(f"[3/6] 分析评论（讽刺检测+情感分析）...")

        # 自动判断品类
        if not result.category:
            result.category = self.analyzer.category_classifier.classify(result.product_name)
            logger.info(f"  自动判断品类: {result.category}")

        # 统一分析
        sentiment_results = self.analyzer.analyze_comments(
            comments=result.taobao_comments,
            product_name=result.product_name,
            category=result.category
        )

        result.sentiment_results = sentiment_results

        # 计算统计
        stats = self.analyzer.calculate_statistics(sentiment_results)
        result.statistics = stats

        logger.info(f"  ✅ 分析完成: 好评率{stats['positive_rate']:.0%}, "
                   f"讽刺{stats['sarcasm_count']}条")

    def _fetch_xiaohongshu(self, context: WorkflowContext, result: AnalysisResult):
        """获取小红书笔记"""
        logger.info(f"[4/6] 搜索小红书...")
        keyword = f"{context.brand} {context.product}"

        xhs_result = self.data.search_xiaohongshu(
            keyword=keyword,
            max_notes=30
        )

        if xhs_result.success and xhs_result.data:
            result.xiaohongshu_notes = xhs_result.data
            logger.info(f"  ✅ 获取到 {len(result.xiaohongshu_notes)} 条笔记")
        else:
            logger.warning(f"  ⚠️ 搜索小红书失败: {xhs_result.error}")

    def _fetch_heimao(self, context: WorkflowContext, result: AnalysisResult):
        """获取黑猫投诉"""
        logger.info(f"[5/6] 搜索黑猫投诉...")

        heimao_result = self.data.search_heimao(
            brand=context.brand,
            max_complaints=50
        )

        if heimao_result.success and heimao_result.data:
            result.heimao_complaints = heimao_result.data
            logger.info(f"  ✅ 获取到 {len(result.heimao_complaints)} 条投诉")
        else:
            logger.warning(f"  ⚠️ 搜索黑猫失败: {heimao_result.error}")

    def _generate_report(self, result: AnalysisResult):
        """生成分析报告"""
        logger.info(f"[6/6] 生成分析报告...")

        if not result.sentiment_results:
            result.summary = "暂无评论数据，无法生成报告。"
            result.advice = "建议查看商品详情后再决定。"
            return

        # 准备数据
        analysis_data = {
            "statistics": result.statistics if result.statistics else {},
            "sample_comments": [
                {
                    "text": r.text,
                    "sentiment": r.sentiment.value,
                    "is_sarcasm": r.is_sarcasm
                }
                for r in result.sentiment_results[:20]
            ]
        }

        # LLM生成总结
        result.summary = self.llm.generate_summary(analysis_data)

        # LLM生成建议
        xhs_text = f"\n小红书反馈: {len(result.xiaohongshu_notes)}条笔记" if result.xiaohongshu_notes else ""
        heimao_text = f"\n黑猫投诉: {len(result.heimao_complaints)}条投诉" if result.heimao_complaints else ""
        context = f"{xhs_text}{heimao_text}"

        result.advice = self.llm.generate_advice(result.summary, context)

        logger.info("  ✅ 报告生成完成")


class SingleSourceWorkflow(Workflow):
    """单一数据源工作流 - 只搜索小红书或黑猫"""

    def __init__(
        self,
        data_service: DataService,
        analyzer: UnifiedAnalyzer,
        llm: LLMClient,
        source: str  # "xiaohongshu" | "heimao"
    ):
        super().__init__(data_service, analyzer, llm)
        self.source = source

    def execute(self, context: WorkflowContext) -> AnalysisResult:
        """执行单一数据源搜索"""
        product_name = f"{context.brand} {context.product}"

        result = AnalysisResult(
            product_name=product_name,
            brand=context.brand,
            status=AnalysisStatus.IN_PROGRESS
        )

        try:
            if self.source == "xiaohongshu":
                self._fetch_xiaohongshu(context, result)
                result.summary = self._analyze_xhs_notes(result)

            elif self.source == "heimao":
                self._fetch_heimao(context, result)
                result.summary = self._analyze_heimao_complaints(result)

            result.status = AnalysisStatus.COMPLETED

        except Exception as e:
            logger.error(f"单数据源搜索失败: {e}")
            result.status = AnalysisStatus.FAILED

        return result

    def _fetch_xiaohongshu(self, context: WorkflowContext, result: AnalysisResult):
        """获取小红书"""
        keyword = f"{context.brand} {context.product}"
        xhs_result = self.data.search_xiaohongshu(keyword=keyword, max_notes=30)

        if xhs_result.success:
            result.xiaohongshu_notes = xhs_result.data

    def _fetch_heimao(self, context: WorkflowContext, result: AnalysisResult):
        """获取黑猫"""
        heimao_result = self.data.search_heimao(brand=context.brand, max_complaints=50)

        if heimao_result.success:
            result.heimao_complaints = heimao_result.data

    def _analyze_xhs_notes(self, result: AnalysisResult) -> str:
        """分析小红书笔记"""
        if not result.xiaohongshu_notes:
            return "未找到相关小红书笔记。"

        # 使用LLM分析
        notes_text = "\n".join([n.text[:200] for n in result.xiaohongshu_notes[:10]])

        prompt = f"""分析以下小红书笔记，提取主要观点：

{notes_text}

请总结：
1. 主要负面观点
2. 避坑点
3. 用户抱怨最多的问题

以简洁的bullet point格式输出。"""

        return self.llm.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.7
        ).content

    def _analyze_heimao_complaints(self, result: AnalysisResult) -> str:
        """分析黑猫投诉"""
        if not result.heimao_complaints:
            return "未找到相关黑猫投诉。"

        complaints_text = "\n".join([c.text[:200] for c in result.heimao_complaints[:10]])

        prompt = f"""分析以下黑猫投诉，提取主要问题：

{complaints_text}

请总结：
1. 主要投诉类型
2. 涉及的主要问题
3. 严重程度和频率

以简洁的bullet point格式输出。"""

        return self.llm.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.7
        ).content


class ComparisonWorkflow(Workflow):
    """对比工作流 - 对比多个商品"""

    def execute(self, context: WorkflowContext) -> AnalysisResult:
        """执行对比分析"""
        # 对每个商品执行完整分析
        # 然后生成对比报告
        # TODO: 实现多商品对比逻辑
        raise NotImplementedError("对比工作流待实现")


class WorkflowFactory:
    """工作流工厂"""

    def __init__(
        self,
        data_service: DataService,
        analyzer: UnifiedAnalyzer,
        llm: LLMClient
    ):
        self.data = data_service
        self.analyzer = analyzer
        self.llm = llm

    def create(self, intent: str) -> Workflow:
        """根据意图创建工作流"""
        workflows = {
            "analyze": ProductAnalysisWorkflow,
            "search_xhs": lambda d, a, l: SingleSourceWorkflow(d, a, l, "xiaohongshu"),
            "search_heimao": lambda d, a, l: SingleSourceWorkflow(d, a, l, "heimao"),
            "compare": ComparisonWorkflow,
        }

        workflow_class = workflows.get(intent, ProductAnalysisWorkflow)
        return workflow_class(self.data, self.analyzer, self.llm)
