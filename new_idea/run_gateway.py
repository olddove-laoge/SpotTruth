#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""避雷真 - 对话式网关模式 (LLM驱动 + 本地爬虫)

工作流程:
  1. 用户输入自然语言
  2. 调用网关 /api/parse_intent 解析意图
  3. 根据意图执行:
     - analyze: 本地爬虫获取数据 → 网关分析 → 生成报告
     - search_xhs: 本地爬虫获取小红书 → 网关分析
     - search_heimao: 本地爬虫获取黑猫 → 网关分析
     - help: 显示帮助
     - clarification_needed: 询问用户澄清

使用方法:
  1. 确保已配置 KIMI_API_KEY (用于agent_api.py)
  2. 终端A: python agent_api.py
  3. 终端B: cd go_backend && go run ./cmd/api-gateway
  4. 终端C: python run_gateway.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from agent import GatewayClient, GatewayError


@dataclass
class ConversationSession:
    """对话会话状态"""
    history: List[Dict[str, str]] = field(default_factory=list)
    current_product: str = ""
    last_analysis_result: Optional[Dict] = None

    def get_last_analyzed_platforms(self) -> List[str]:
        """获取上次分析的平台列表"""
        if self.last_analysis_result:
            return self.last_analysis_result.get('analyzed_platforms', [])
        return []

    def get_current_product_info(self) -> Optional[Dict]:
        """获取当前商品信息"""
        if not self.last_analysis_result:
            return None
        return {
            "product_name": self.last_analysis_result.get('product_name', ''),
            "platforms": self.last_analysis_result.get('analyzed_platforms', []),
            "has_taobao": self.last_analysis_result.get('has_taobao', False),
            "has_xiaohongshu": self.last_analysis_result.get('has_xiaohongshu', False),
            "has_heimao": self.last_analysis_result.get('has_heimao', False)
        }


class ConversationalGatewayAgent:
    """对话式网关Agent - LLM驱动 + 本地爬虫"""

    def __init__(self):
        self.gateway = GatewayClient()
        self.session = ConversationSession()
        self.has_crawler = False
        self.data_service = None

    def run(self):
        """运行主循环"""
        print("""
[避雷真 - 对话式网关模式]
===============================================================
你可以像聊天一样和我交流:
  • "帮我分析一下德芙巧克力怎么样"
  • "搜索一下小红书上的避雷笔记"
  • "这个商品在黑猫投诉上有没有问题"
  • "给我一些购买建议"

我会自动理解你的意图，帮你分析商品口碑。

命令:
  /test  - 测试网关连接
  /quit  - 退出程序
===============================================================
""")

        # 初始化检查
        if not self._initialize():
            return

        # 显示欢迎语
        print("\n🤖 你好！我是避雷真，一个商品口碑分析助手。")
        print("   请告诉我你想了解什么商品？\n")

        while True:
            try:
                user_input = input("👤 ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["/quit", "/exit", "quit", "退出", "q"]:
                    print("\n👋 再见！希望我的分析对你有帮助~")
                    break

                if user_input.lower() == "/test":
                    self._test_gateway()
                    continue

                # 处理用户输入
                self._process_user_input(user_input)

            except KeyboardInterrupt:
                print("\n\n👋 再见！")
                break
            except Exception as e:
                print(f"\n❌ 出错了: {e}")

    def _initialize(self) -> bool:
        """初始化检查"""
        # 检查网关连接
        print("\n🔗 正在连接网关...")
        if not self._test_gateway():
            print("\n❌ 无法连接到网关，请检查:")
            print("   1. Go网关是否已启动")
            print("   2. Agent API是否已启动")
            return False

        # 检查本地爬虫
        try:
            from agent.data_service import DataService, CrawlerConfig
            from agent import create_driver
            self.has_crawler = True
            print("✅ 本地爬虫模块已加载")
        except ImportError as e:
            print(f"⚠️ 本地爬虫不可用: {e}")
            print("   将使用模拟数据模式")

        return True

    def _test_gateway(self) -> bool:
        """测试网关连接"""
        try:
            health = self.gateway.health_check()
            ready = self.gateway.ready_check()
            print(f"✅ 网关连接成功")
            return True
        except GatewayError as e:
            print(f"❌ 连接失败: {e}")
            return False

    def _process_user_input(self, user_input: str):
        """处理用户输入"""
        # 1. 调用网关解析意图
        try:
            intent_data = self.gateway.parse_intent(
                user_input=user_input,
                conversation_history=self.session.history[-6:],  # 最近6轮
                current_product=self.session.current_product
            )
        except GatewayError as e:
            print(f"\n🤖 抱歉，我暂时无法处理你的请求: {e}")
            return

        # 2. 显示LLM的响应语
        response = intent_data.get('response', '收到，我来处理')
        print(f"\n🤖 {response}")

        # 3. 保存对话历史
        self.session.history.append({"role": "user", "content": user_input})
        self.session.history.append({"role": "assistant", "content": response})

        # 4. 根据意图执行操作
        intent = intent_data.get('intent', 'unknown')

        if intent_data.get('clarification_needed'):
            # 需要用户澄清，等待下一轮输入
            return

        if intent == 'analyze':
            self._handle_analyze_intent(intent_data)
        elif intent == 'compare':
            self._handle_compare_intent(intent_data)
        elif intent == 'search_xhs':
            self._handle_xiaohongshu_intent(intent_data)
        elif intent == 'search_heimao':
            self._handle_heimao_intent(intent_data)
        elif intent == 'help':
            # 帮助信息已经在response中
            pass
        elif intent == 'unknown':
            # 未知意图，提示已在response中
            pass
        else:
            print(f"🤖 这个操作我还不太熟悉，试试让我分析商品吧~")

    def _handle_analyze_intent(self, intent_data: Dict):
        """处理分析意图"""
        brand = intent_data.get('brand', '')
        product = intent_data.get('product', '')
        need_xhs = intent_data.get('need_xiaohongshu', False)
        need_heimao = intent_data.get('need_heimao', False)

        if not product:
            print("🤖 请告诉我你想分析什么商品，比如：德芙巧克力")
            return

        product_name = f"{brand} {product}".strip()
        self.session.current_product = product_name

        print(f"\n🔍 开始分析: {product_name}")

        # 1. 获取数据（本地爬虫）
        # 分析意图默认需要淘宝数据，除非用户明确指定了其他平台
        need_taobao = not (need_xhs or need_heimao) or True  # 默认True，除非明确跳过
        if self.has_crawler:
            taobao_comments, xhs_notes, heimao_complaints = self._crawl_data(
                brand=brand, product=product, need_xhs=need_xhs, need_heimao=need_heimao, need_taobao=need_taobao
            )
        else:
            print("⚠️ 使用模拟数据")
            taobao_comments = self._get_mock_comments()
            xhs_notes = []
            heimao_complaints = []

        if not taobao_comments:
            print("🤖 抱歉，没能获取到评论数据。可能是网络问题或商品不存在。")
            return

        print(f"📊 获取到 {len(taobao_comments)} 条淘宝评论")

        # 2. 品类分类
        try:
            category = self.gateway.classify_product(product_name)
            print(f"🏷️ 商品分类: {category}")
        except GatewayError as e:
            print(f"⚠️ 分类失败，使用默认值: {e}")
            category = "electronics"

        # 3. 情感分析
        print("🧠 正在进行情感分析...")
        try:
            analysis_result = self.gateway.analyze_comments(
                comments=taobao_comments,
                product_name=product_name,
                category=category
            )
        except GatewayError as e:
            print(f"❌ 分析失败: {e}")
            return

        stats = analysis_result.get('statistics', {})
        results = analysis_result.get('results', [])

        # 4. 生成总结
        print("📝 正在生成分析报告...")
        try:
            summary_result = self.gateway.summarize(
                statistics=stats,
                sample_comments=[
                    {"text": r["text"], "sentiment": r["sentiment"], "is_sarcasm": r["is_sarcasm"]}
                    for r in results
                ]
            )
            summary = summary_result.get('summary', '')
            advice = summary_result.get('advice', '')
        except GatewayError as e:
            print(f"⚠️ 生成总结失败: {e}")
            summary = ""
            advice = ""

        # 5. 分析小红书（如果需要）
        xhs_analysis = None
        if xhs_notes and need_xhs:
            print("📱 正在分析小红书笔记...")
            try:
                xhs_analysis = self.gateway.analyze_xiaohongshu(
                    notes=[{"title": "", "content": n, "likes": 0} for n in xhs_notes],
                    keyword=product_name
                )
            except GatewayError as e:
                print(f"⚠️ 小红书分析失败: {e}")

        # 6. 分析黑猫投诉（如果需要）
        heimao_analysis = None
        if heimao_complaints and need_heimao:
            print("⚠️ 正在分析黑猫投诉...")
            try:
                heimao_analysis = self.gateway.analyze_heimao(
                    complaints=[{"title": "", "content": c, "status": ""} for c in heimao_complaints],
                    brand=brand or product_name
                )
            except GatewayError as e:
                print(f"⚠️ 黑猫分析失败: {e}")

        # 7. 记录分析的平台信息（用于对比功能）
        analyzed_platforms = ['taobao']
        if xhs_notes and need_xhs:
            analyzed_platforms.append('xiaohongshu')
        if heimao_complaints and need_heimao:
            analyzed_platforms.append('heimao')

        # 8. 保存结果并展示
        self.session.last_analysis_result = {
            "product_name": product_name,
            "statistics": stats,
            "summary": summary,
            "advice": advice,
            "analyzed_platforms": analyzed_platforms,
            "has_taobao": True,
            "has_xiaohongshu": bool(xhs_notes and need_xhs),
            "has_heimao": bool(heimao_complaints and need_heimao)
        }

        self._print_full_report(
            product_name, category, stats, results,
            summary, advice, xhs_analysis, heimao_analysis
        )

    def _handle_xiaohongshu_intent(self, intent_data: Dict):
        """处理小红书搜索意图"""
        brand = intent_data.get('brand', '')
        product = intent_data.get('product', '')
        keyword = f"{brand} {product}".strip()

        if not keyword:
            keyword = self.session.current_product

        if not keyword:
            print("🤖 请告诉我你想搜索什么商品的小红书笔记")
            return

        print(f"\n📱 搜索小红书: {keyword}")

        if self.has_crawler:
            notes = self._crawl_xiaohongshu(keyword)
        else:
            print("⚠️ 爬虫不可用")
            notes = []

        if not notes:
            print("🤖 没找到相关的小红书笔记")
            return

        print(f"📊 获取到 {len(notes)} 条笔记")

        # 分析笔记
        try:
            analysis = self.gateway.analyze_xiaohongshu(
                notes=[{"title": "", "content": n, "likes": 0} for n in notes],
                keyword=keyword
            )

            print("\n" + "=" * 60)
            print(f"📱 小红书分析: {keyword}")
            print("-" * 60)
            print(f"\n{analysis.get('summary', '')}")

            key_points = analysis.get('key_points', [])
            if key_points:
                print("\n🔍 关键发现:")
                for point in key_points:
                    print(f"   • {point}")

            print("=" * 60)

        except GatewayError as e:
            print(f"❌ 分析失败: {e}")

    def _handle_heimao_intent(self, intent_data: Dict):
        """处理黑猫投诉搜索意图"""
        brand = intent_data.get('brand', '')

        if not brand:
            brand = self.session.current_product.split()[0] if self.session.current_product else ""

        if not brand:
            print("🤖 请告诉我你想查询什么品牌的投诉信息")
            return

        print(f"\n⚠️ 查询黑猫投诉: {brand}")

        if self.has_crawler:
            complaints = self._crawl_heimao(brand)
        else:
            print("⚠️ 爬虫不可用")
            complaints = []

        if not complaints:
            print("🤖 没找到相关的投诉信息")
            return

        print(f"📊 获取到 {len(complaints)} 条投诉")

        # 分析投诉
        try:
            analysis = self.gateway.analyze_heimao(
                complaints=[{"title": "", "content": c, "status": ""} for c in complaints],
                brand=brand
            )

            print("\n" + "=" * 60)
            print(f"⚠️ 黑猫投诉分析: {brand}")
            print("-" * 60)
            print(f"\n{analysis.get('summary', '')}")

            complaint_types = analysis.get('complaint_types', [])
            if complaint_types:
                print("\n📋 主要投诉类型:")
                for t in complaint_types:
                    print(f"   • {t}")

            severity = analysis.get('severity', 'unknown')
            if severity == 'high':
                print("\n🚨 风险等级: 高 - 建议谨慎购买")
            elif severity == 'medium':
                print("\n⚠️ 风险等级: 中 - 建议查看更多评价")
            else:
                print("\n✅ 风险等级: 低")

            recommendation = analysis.get('recommendation', '')
            if recommendation:
                print(f"\n💡 建议: {recommendation}")

            print("=" * 60)

        except GatewayError as e:
            print(f"❌ 分析失败: {e}")

    def _handle_compare_intent(self, intent_data: Dict):
        """处理对比意图"""
        products = intent_data.get('products', [])

        # 确保 products 是列表且元素是字典（处理LLM可能返回JSON字符串的情况）
        import json
        if isinstance(products, str):
            try:
                products = json.loads(products)
            except:
                products = []

        # 确保每个元素都是字典
        valid_products = []
        for p in products:
            if isinstance(p, dict):
                valid_products.append(p)
            elif isinstance(p, str):
                try:
                    parsed = json.loads(p)
                    if isinstance(parsed, dict):
                        valid_products.append(parsed)
                except:
                    pass
        products = valid_products

        # 如果没有明确的两个商品，尝试从上下文中获取
        if len(products) < 2:
            # 获取当前商品
            current_info = self.session.get_current_product_info()
            if not current_info:
                print("🤖 请先告诉我您想对比的第一个商品")
                return

            current_product_name = current_info['product_name']
            current_brand = current_info['brand']

            # 解析第二个商品
            new_product = intent_data.get('product', '')
            new_brand = intent_data.get('brand', '')

            if not new_product:
                print("🤖 请告诉我您想对比的商品名称")
                return

            # 构建对比列表
            products = [
                {'brand': current_brand, 'product': current_product_name.replace(current_brand, '').strip()},
                {'brand': new_brand, 'product': new_product}
            ]

        # 获取要对比的平台（优先使用用户指定的，其次继承上次分析的）
        need_xhs = intent_data.get('need_xiaohongshu', False)
        need_heimao = intent_data.get('need_heimao', False)

        # 构建平台列表
        platforms = []
        if need_xhs:
            platforms.append('xiaohongshu')
        if need_heimao:
            platforms.append('heimao')

        # 如果用户没有指定任何平台，才默认使用淘宝+继承上次分析的平台
        if not platforms:
            platforms = self.session.get_last_analyzed_platforms()
            if not platforms:
                platforms = ['taobao']  # 默认至少对比淘宝
            need_xhs = 'xiaohongshu' in platforms
            need_heimao = 'heimao' in platforms
        # 如果用户指定了平台，就不需要淘宝了
        # 但如果平台列表为空，还是加上淘宝作为保底
        elif not platforms:
            platforms = ['taobao']

        print(f"\n🔍 开始对比分析")
        prod_a_brand = products[0].get('brand', '') if isinstance(products[0], dict) else str(products[0])
        prod_a_product = products[0].get('product', '') if isinstance(products[0], dict) else ''
        prod_b_brand = products[1].get('brand', '') if isinstance(products[1], dict) else str(products[1])
        prod_b_product = products[1].get('product', '') if isinstance(products[1], dict) else ''
        print(f"   商品A: {prod_a_brand} {prod_a_product}")
        print(f"   商品B: {prod_b_brand} {prod_b_product}")
        print(f"   对比维度: {', '.join(platforms)}")

        # 分别分析两个商品
        results = []
        for i, prod in enumerate(products, 1):
            prod_brand = prod.get('brand', '') if isinstance(prod, dict) else str(prod)
            prod_name = prod.get('product', '') if isinstance(prod, dict) else ''
            print(f"\n{'='*60}")
            print(f"📦 分析商品 {i}: {prod_brand} {prod_name}")
            print(f"{'='*60}")

            # 复用分析逻辑
            # 如果只对比小红书/黑猫，不需要爬取淘宝
            need_taobao = not (need_xhs or need_heimao)
            result = self._analyze_single_product(
                brand=prod.get('brand', '') if isinstance(prod, dict) else '',
                product=prod.get('product', '') if isinstance(prod, dict) else '',
                need_xhs=need_xhs,
                need_heimao=need_heimao,
                need_taobao=need_taobao
            )

            if result:
                results.append(result)

        # 生成对比报告
        if len(results) == 2:
            self._print_comparison_report(results[0], results[1])
        else:
            print("\n❌ 对比失败，无法获取足够的数据")

    def _analyze_single_product(self, brand: str, product: str, need_xhs: bool, need_heimao: bool, need_taobao: bool = True) -> Optional[Dict]:
        """分析单个商品，返回结构化结果"""
        product_name = f"{brand} {product}".strip()

        # 1. 获取数据（按需爬取各平台）
        if self.has_crawler:
            taobao_comments, xhs_notes, heimao_complaints = self._crawl_data(
                brand=brand, product=product, need_xhs=need_xhs, need_heimao=need_heimao, need_taobao=need_taobao
            )
        else:
            print("⚠️ 使用模拟数据")
            taobao_comments = self._get_mock_comments()
            xhs_notes = []
            heimao_complaints = []

        # 显示各平台数据量
        if taobao_comments:
            print(f"✅ 获取到 {len(taobao_comments)} 条淘宝评论")
        if xhs_notes:
            print(f"✅ 获取到 {len(xhs_notes)} 条小红书笔记")
        if heimao_complaints:
            print(f"✅ 获取到 {len(heimao_complaints)} 条黑猫投诉")

        # 检查是否有任何数据
        if not taobao_comments and not xhs_notes and not heimao_complaints:
            print(f"❌ 未获取到 {product_name} 的任何数据")
            return None

        # 2. 品类分类
        try:
            category = self.gateway.classify_product(product_name)
            print(f"🏷️ 商品分类: {category}")
        except GatewayError as e:
            print(f"⚠️ 分类失败: {e}")
            category = "electronics"

        # 3. 情感分析（只用淘宝评论，小红书/黑猫不做情感分析）
        stats = {"total": 0, "positive_rate": 0, "negative_rate": 0, "sarcasm_count": 0}
        results = []

        if taobao_comments:
            print("🧠 正在进行淘宝评论情感分析...")
            try:
                analysis_result = self.gateway.analyze_comments(
                    comments=taobao_comments,
                    product_name=product_name,
                    category=category
                )
                stats = analysis_result.get('statistics', {})
                results = analysis_result.get('results', [])
                print(f"   ✅ 分析完成: {stats.get('total', 0)}条评论")
            except GatewayError as e:
                print(f"❌ 淘宝评论分析失败: {e}")
        else:
            print("ℹ️ 无淘宝评论，跳过情感分析")

        # 4. 生成总结（有淘宝数据才生成，否则用小红书/黑猫的报告）
        summary = ""
        advice = ""

        if taobao_comments and results:
            print("📝 正在生成淘宝评论分析报告...")
            try:
                summary_result = self.gateway.summarize(
                    statistics=stats,
                    sample_comments=[
                        {"text": r["text"], "sentiment": r["sentiment"], "is_sarcasm": r["is_sarcasm"]}
                        for r in results[:15]
                    ]
                )
                summary = summary_result.get('summary', '')
                advice = summary_result.get('advice', '')
            except GatewayError as e:
                print(f"⚠️ 生成总结失败: {e}")

        # 5. 分析小红书
        xhs_analysis = None
        if xhs_notes and need_xhs:
            print("📱 正在分析小红书笔记...")
            try:
                xhs_analysis = self.gateway.analyze_xiaohongshu(
                    notes=[{"title": "", "content": n, "likes": 0} for n in xhs_notes],
                    keyword=product_name
                )
            except GatewayError as e:
                print(f"⚠️ 小红书分析失败: {e}")

        # 6. 分析黑猫
        heimao_analysis = None
        if heimao_complaints and need_heimao:
            print("⚠️ 正在分析黑猫投诉...")
            try:
                heimao_analysis = self.gateway.analyze_heimao(
                    complaints=[{"title": "", "content": c, "status": ""} for c in heimao_complaints],
                    brand=brand or product_name
                )
            except GatewayError as e:
                print(f"⚠️ 黑猫分析失败: {e}")

        return {
            "product_name": product_name,
            "brand": brand,
            "category": category,
            "statistics": stats,
            "summary": summary,
            "advice": advice,
            "xhs_analysis": xhs_analysis,
            "heimao_analysis": heimao_analysis,
            "taobao_count": len(taobao_comments),
            "xhs_count": len(xhs_notes),
            "heimao_count": len(heimao_complaints)
        }

    def _print_comparison_report(self, result_a: Dict, result_b: Dict):
        """打印对比报告"""
        print("\n" + "=" * 70)
        print(f"📊 对比报告: {result_a['product_name']} vs {result_b['product_name']}")
        print("=" * 70)

        stats_a = result_a.get('statistics', {})
        stats_b = result_b.get('statistics', {})

        # 基础统计对比（只有淘宝数据才显示这些指标）
        print(f"\n{'指标':<20} {result_a['product_name']:<25} {result_b['product_name']:<25}")
        print("-" * 70)

        has_taobao_a = stats_a.get('total', 0) > 0
        has_taobao_b = stats_b.get('total', 0) > 0

        if has_taobao_a or has_taobao_b:
            print(f"{'📊 淘宝评论数':<20} {stats_a.get('total', 0):<25} {stats_b.get('total', 0):<25}")
            if has_taobao_a:
                print(f"{'   好评率':<20} {stats_a.get('positive_rate', 0):.1%}")
                print(f"{'   差评率':<20} {stats_a.get('negative_rate', 0):.1%}")
                sarcasm_a = stats_a.get('sarcasm_count', 0)
                if sarcasm_a > 0:
                    print(f"{'   虚假好评':<20} {sarcasm_a}条")
            if has_taobao_b:
                print(f"{'   好评率':<45} {stats_b.get('positive_rate', 0):.1%}")
                print(f"{'   差评率':<45} {stats_b.get('negative_rate', 0):.1%}")
                sarcasm_b = stats_b.get('sarcasm_count', 0)
                if sarcasm_b > 0:
                    print(f"{'   虚假好评':<45} {sarcasm_b}条")

        # 小红书对比
        if result_a.get('xhs_count', 0) > 0 or result_b.get('xhs_count', 0) > 0:
            print(f"{'📱 小红书笔记':<20} {result_a['xhs_count']}条{'':<22} {result_b['xhs_count']}条")

        # 黑猫投诉对比
        if result_a.get('heimao_count', 0) > 0 or result_b.get('heimao_count', 0) > 0:
            print(f"{'⚠️ 黑猫投诉':<20} {result_a['heimao_count']}条{'':<22} {result_b['heimao_count']}条")

        # 口碑总结对比
        print(f"\n{'='*70}")
        print("📋 口碑总结对比:")
        print(f"{'='*70}")

        # 显示淘宝评论分析（如果有）
        if has_taobao_a or has_taobao_b:
            print("\n📊 淘宝评论分析:")
            print(f"\n【{result_a['product_name']}】")
            print(f"   {result_a.get('summary', '暂无总结')[:200]}...")
            print(f"\n【{result_b['product_name']}】")
            print(f"   {result_b.get('summary', '暂无总结')[:200]}...")

        # 显示小红书分析（如果有）
        if result_a.get('xhs_analysis') or result_b.get('xhs_analysis'):
            print("\n📱 小红书分析:")
            if result_a.get('xhs_analysis'):
                print(f"\n【{result_a['product_name']}】")
                xhs_summary_a = result_a['xhs_analysis'].get('summary', '')
                print(f"   {xhs_summary_a[:200]}..." if xhs_summary_a else "   暂无分析")
            if result_b.get('xhs_analysis'):
                print(f"\n【{result_b['product_name']}】")
                xhs_summary_b = result_b['xhs_analysis'].get('summary', '')
                print(f"   {xhs_summary_b[:200]}..." if xhs_summary_b else "   暂无分析")

        # 显示黑猫投诉分析（如果有）
        if result_a.get('heimao_analysis') or result_b.get('heimao_analysis'):
            print("\n⚠️ 黑猫投诉分析:")
            if result_a.get('heimao_analysis'):
                print(f"\n【{result_a['product_name']}】")
                heimao_summary_a = result_a['heimao_analysis'].get('summary', '')
                print(f"   {heimao_summary_a[:200]}..." if heimao_summary_a else "   暂无分析")
                # 显示投诉类型
                complaint_types_a = result_a['heimao_analysis'].get('complaint_types', [])
                if complaint_types_a:
                    print(f"   主要投诉类型: {', '.join(complaint_types_a[:3])}")
                # 显示风险等级
                severity_a = result_a['heimao_analysis'].get('severity', '')
                if severity_a:
                    severity_map = {'high': '高', 'medium': '中', 'low': '低'}
                    print(f"   风险等级: {severity_map.get(severity_a, severity_a)}")
            if result_b.get('heimao_analysis'):
                print(f"\n【{result_b['product_name']}】")
                heimao_summary_b = result_b['heimao_analysis'].get('summary', '')
                print(f"   {heimao_summary_b[:200]}..." if heimao_summary_b else "   暂无分析")
                # 显示投诉类型
                complaint_types_b = result_b['heimao_analysis'].get('complaint_types', [])
                if complaint_types_b:
                    print(f"   主要投诉类型: {', '.join(complaint_types_b[:3])}")
                # 显示风险等级
                severity_b = result_b['heimao_analysis'].get('severity', '')
                if severity_b:
                    severity_map = {'high': '高', 'medium': '中', 'low': '低'}
                    print(f"   风险等级: {severity_map.get(severity_b, severity_b)}")

        # 购买建议对比（只有淘宝数据才有）
        if has_taobao_a or has_taobao_b:
            if result_a.get('advice') or result_b.get('advice'):
                print(f"\n{'='*70}")
                print("💡 购买建议对比:")
                print(f"{'='*70}")
                print(f"\n【{result_a['product_name']}】{result_a.get('advice', '暂无建议')[:150]}...")
                print(f"\n【{result_b['product_name']}】{result_b.get('advice', '暂无建议')[:150]}...")

        # 使用LLM生成对比结论
        print(f"\n{'='*70}")
        print("🔍 对比结论:")
        print(f"{'='*70}")

        try:
            comparison_conclusion = self.gateway.generate_comparison_conclusion(
                product_a_name=result_a['product_name'],
                product_b_name=result_b['product_name'],
                stats_a=stats_a,
                stats_b=stats_b,
                summary_a=result_a.get('summary', ''),
                summary_b=result_b.get('summary', ''),
                advice_a=result_a.get('advice', ''),
                advice_b=result_b.get('advice', ''),
                heimao_analysis_a=result_a.get('heimao_analysis'),
                heimao_analysis_b=result_b.get('heimao_analysis'),
                xhs_analysis_a=result_a.get('xhs_analysis'),
                xhs_analysis_b=result_b.get('xhs_analysis'),
                has_taobao_a=has_taobao_a,
                has_taobao_b=has_taobao_b
            )
            print(comparison_conclusion)
        except Exception as e:
            print(f"   ❌ 生成对比结论失败: {e}")
            print("   📊 建议查看上述详细分析后自行判断")

        print("=" * 70)

    def _crawl_data(self, brand: str, product: str, need_xhs: bool, need_heimao: bool, need_taobao: bool = True):
        """爬取数据 - 按需爬取各平台"""
        from agent.data_service import DataService, CrawlerConfig
        from agent import create_driver

        taobao_comments = []
        xhs_notes = []
        heimao_complaints = []

        try:
            print("\n🌐 正在启动浏览器...")
            driver = create_driver()
            config = CrawlerConfig(driver=driver)
            data_service = DataService(config)

            # 1. 淘宝数据（如果需要）
            if need_taobao:
                print("🔍 搜索淘宝商品...")
                search_result = data_service.search_product(brand=brand, product=product, max_results=5)
                if search_result.success and search_result.data:
                    product_info = search_result.data[0]
                    print(f"✅ 找到商品: {product_info.name}")

                    print("💬 获取淘宝评论...")
                    comments_result = data_service.get_comments(
                        url=product_info.url,
                        brand=brand,
                        product=product,
                        max_count=50
                    )
                    if comments_result.success and comments_result.data:
                        taobao_comments = [c.text for c in comments_result.data]
                        print(f"✅ 获取 {len(taobao_comments)} 条淘宝评论")
                else:
                    print("⚠️ 未找到淘宝商品")

            # 2. 小红书数据（如果需要）
            if need_xhs:
                print("📱 获取小红书笔记...")
                keyword = f"{brand} {product}".strip()
                xhs_result = data_service.search_xiaohongshu(
                    keyword=keyword,
                    max_notes=5
                )
                if xhs_result.success and xhs_result.data:
                    xhs_notes = [n.text for n in xhs_result.data]
                    print(f"✅ 获取 {len(xhs_notes)} 条小红书笔记")

            # 3. 黑猫投诉（如果需要）
            if need_heimao:
                print("⚠️ 获取黑猫投诉...")
                heimao_result = data_service.search_heimao(
                    brand=brand,
                    max_complaints=30
                )
                if heimao_result.success and heimao_result.data:
                    heimao_complaints = [c.text for c in heimao_result.data]
                    print(f"✅ 获取 {len(heimao_complaints)} 条黑猫投诉")

            driver.quit()

        except Exception as e:
            print(f"❌ 爬虫出错: {e}")

        return taobao_comments, xhs_notes, heimao_complaints

    def _crawl_xiaohongshu(self, keyword: str) -> List[str]:
        """爬取小红书"""
        from agent.data_service import DataService, CrawlerConfig
        from agent import create_driver

        try:
            driver = create_driver()
            config = CrawlerConfig(driver=driver)
            data_service = DataService(config)

            result = data_service.search_xiaohongshu(keyword=keyword, max_notes=5)
            notes = [n.text for n in result.data] if result.success and result.data else []

            driver.quit()
            return notes
        except Exception as e:
            print(f"❌ 小红书爬虫出错: {e}")
            return []

    def _crawl_heimao(self, brand: str) -> List[str]:
        """爬取黑猫投诉"""
        from agent.data_service import DataService, CrawlerConfig
        from agent import create_driver

        try:
            driver = create_driver()
            config = CrawlerConfig(driver=driver)
            data_service = DataService(config)

            result = data_service.search_heimao(brand=brand, max_complaints=30)
            complaints = [c.text for c in result.data] if result.success and result.data else []

            driver.quit()
            return complaints
        except Exception as e:
            print(f"❌ 黑猫爬虫出错: {e}")
            return []

    def _get_mock_comments(self) -> List[str]:
        """获取模拟评论"""
        return [
            "这个商品真的很好用，强烈推荐购买！",
            "质量一般般，没有想象中那么好",
            "性价比很高，物流也很快",
            "呵呵，真是太棒了呢，完全不值这个价",
            "包装破损了，但是东西还能用",
            "第二次购买了，一如既往的好",
            "不知道怎么说，感觉被骗了",
            "很好很满意，下次还会买"
        ]

    def _print_full_report(
        self,
        product_name: str,
        category: str,
        stats: Dict,
        results: List[Dict],
        summary: str,
        advice: str,
        xhs_analysis: Optional[Dict],
        heimao_analysis: Optional[Dict]
    ):
        """打印完整报告"""
        print("\n" + "=" * 60)
        print(f"📦 {product_name} ({category})")
        print("-" * 60)

        # 统计
        print(f"\n📊 统计结果:")
        print(f"   总评论: {stats.get('total', 0)} 条")
        print(f"   好评率: {stats.get('positive_rate', 0):.0%}")
        print(f"   差评率: {stats.get('negative_rate', 0):.0%}")

        sarcasm = stats.get('sarcasm_count', 0)
        if sarcasm > 0:
            print(f"   ⚠️ 疑似虚假好评: {sarcasm} 条")

        # 评论详情
        print(f"\n📝 评论分析:")
        for i, r in enumerate(results[:5], 1):
            sentiment = "👍" if r["sentiment"] == "positive" else "👎"
            sarcasm_tag = "🎭讽刺" if r["is_sarcasm"] else ""
            print(f"   {i}. {sentiment} {sarcasm_tag}")
            print(f"      {r['text'][:50]}...")
            if r.get("llm_analysis"):
                print(f"      💡 {r['llm_analysis'][:60]}...")

        if len(results) > 5:
            print(f"   ... 还有 {len(results) - 5} 条评论")

        # 小红书
        if xhs_analysis:
            print(f"\n📱 小红书反馈:")
            print(f"   {xhs_analysis.get('summary', '')[:150]}...")

        # 黑猫投诉
        if heimao_analysis:
            print(f"\n⚠️ 投诉情况:")
            print(f"   {heimao_analysis.get('summary', '')[:150]}...")

        # 总结和建议
        if summary:
            print(f"\n📋 分析总结:")
            print(f"   {summary}")

        if advice:
            print(f"\n💡 购买建议:")
            print(f"   {advice}")

        print("=" * 60)


def main():
    """主入口"""
    agent = ConversationalGatewayAgent()
    agent.run()


if __name__ == "__main__":
    main()
