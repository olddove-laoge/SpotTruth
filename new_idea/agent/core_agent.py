"""核心Agent - 对话管理和意图路由"""

import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

from config import paths as paths_config, session as session_config
from agent.infrastructure import logger, events
from agent.models import Session, AnalysisResult, UserIntent
from agent.llm_client import LLMClient, KimiClient
from agent.analyzers import UnifiedAnalyzer
from agent.data_service import DataService, CrawlerConfig
from agent.workflows import WorkflowFactory, WorkflowContext


@dataclass
class AgentConfig:
    """Agent配置"""
    driver_path: str = paths_config.driver_path
    profile_dir: str = paths_config.profile_dir
    auto_save: bool = True
    welcome_message: str = """
🤖 避雷真 - 商品口碑分析Agent
═══════════════════════════════════════════════════════════════

您好！我是避雷真，一个专业的商品口碑分析助手。

我可以帮您：
  📊 分析淘宝商品的好评率/差评率
  🔍 识别虚假好评和阴阳怪气评价
  📝 搜索小红书避雷笔记
  ⚠️  查询黑猫投诉记录
  💡 提供购买建议

使用方法：
  • 输入"分析 [品牌] [商品]"（如：分析 德芙 巧克力）
  • 输入"搜索小红书 [关键词]"
  • 输入"搜索黑猫 [品牌]"

输入 'quit' 或 '退出' 结束程序
═══════════════════════════════════════════════════════════════
"""


class BileizhenAgent:
    """避雷真Agent - 重构版"""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.session = Session()

        # 初始化组件
        self.llm: Optional[LLMClient] = None
        self.data_service: Optional[DataService] = None
        self.analyzer: Optional[UnifiedAnalyzer] = None
        self.workflow_factory: Optional[WorkflowFactory] = None

        # WebDriver
        self.driver = None

        # 注册事件监听
        self._register_event_handlers()

    def _register_event_handlers(self):
        """注册事件处理器"""
        events.on("analysis_started", self._on_analysis_started)
        events.on("analysis_completed", self._on_analysis_completed)
        events.on("analysis_failed", self._on_analysis_failed)

    def _on_analysis_started(self, data):
        """分析开始事件"""
        logger.info(f"🚀 开始分析: {data.get('product', '')}")

    def _on_analysis_completed(self, data):
        """分析完成事件"""
        result: AnalysisResult = data.get('result')
        if result:
            self.session.save_analysis(result)
            if self.config.auto_save:
                self._save_session()
        logger.info(f"✅ 分析完成: {data.get('product', '')}")

    def _on_analysis_failed(self, data):
        """分析失败事件"""
        logger.error(f"❌ 分析失败: {data.get('product', '')} - {data.get('error', '')}")

    def initialize(self, driver=None):
        """初始化Agent组件"""
        logger.info("初始化Agent...")

        # 1. LLM客户端
        self.llm = KimiClient()

        # 2. 分析器
        self.analyzer = UnifiedAnalyzer(self.llm)

        # 3. 数据服务
        crawler_config = CrawlerConfig(
            driver=driver,
            driver_path=self.config.driver_path
        )
        self.data_service = DataService(crawler_config)

        # 4. 工作流工厂
        self.workflow_factory = WorkflowFactory(
            self.data_service,
            self.analyzer,
            self.llm
        )

        self.driver = driver
        logger.info("✅ Agent初始化完成")

    def run(self):
        """运行主循环"""
        print(self.config.welcome_message)

        # 加载历史会话
        self._load_session()

        while True:
            try:
                user_input = input("\n👤 您: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["quit", "exit", "退出", "q"]:
                    self._shutdown()
                    break

                if user_input.lower() in ["clear", "清除"]:
                    self._clear_session()
                    continue

                if user_input.lower() in ["history", "历史"]:
                    self._show_history()
                    continue

                # 处理用户输入
                response = self._process_input(user_input)
                print(f"\n🤖 避雷真:\n{response}")

            except KeyboardInterrupt:
                self._shutdown()
                break
            except Exception as e:
                logger.error(f"处理输入时出错: {e}")
                print(f"\n🤖 避雷真:\n抱歉，处理您的请求时出错: {e}")

    def _resolve_references(self, user_input: str) -> str:
        """解析上下文代词，替换为当前商品名"""
        if not self.session.current_analysis:
            return user_input

        current_product = self.session.current_analysis.product_name
        if not current_product:
            return user_input

        # 需要替换的代词模式
        reference_patterns = [
            "这个商品", "这个", "它", "该产品", "这款",
            "黑猫怎么样", "黑猫投诉怎么样",
            "小红书怎么样", "笔记怎么样",
            "淘宝怎么样", "评论怎么样",
        ]

        input_lower = user_input.lower()

        # 检查是否包含代词
        for pattern in reference_patterns:
            if pattern in input_lower or pattern in user_input:
                # 根据输入类型决定如何替换
                if "黑猫" in input_lower:
                    return f"{current_product}的黑猫投诉"
                elif "小红书" in input_lower or "笔记" in input_lower:
                    return f"{current_product}的小红书笔记"
                elif "淘宝" in input_lower or "评论" in input_lower:
                    return f"{current_product}的淘宝评论"
                else:
                    # 通用替换
                    return f"{current_product}"

        return user_input

    def _is_asking_for_summary(self, user_input: str) -> bool:
        """检查用户是否在询问总结或建议"""
        summary_keywords = [
            "建议", "总结", "综上所述", "怎么样", "值得买吗",
            "推荐购买吗", "好不好", "评价如何", "结论",
            "你的看法", "你怎么看", "分析结果"
        ]
        input_lower = user_input.lower()
        return any(kw in input_lower for kw in summary_keywords)

    def _process_input(self, user_input: str) -> str:
        """处理用户输入"""
        # 0. 检查是否是询问当前分析结果
        if self._is_asking_for_summary(user_input):
            if self.session.current_analysis:
                logger.info("用户询问总结，直接返回当前分析结果")
                response = self._format_response(self.session.current_analysis)
                self.session.add_to_history("assistant", response)
                return response

        # 1. 解析上下文代词
        user_input = self._resolve_references(user_input)

        # 2. 添加到对话历史
        self.session.add_to_history("user", user_input)

        # 3. 解析意图（传入当前商品名）
        current_product = ""
        if self.session.current_analysis:
            current_product = self.session.current_analysis.product_name

        intent_data = self.llm.parse_intent(
            user_input,
            self.session.conversation_history,
            current_product=current_product
        )

        logger.info(f"解析意图: {intent_data.get('intent', 'unknown')}, 商品: {intent_data.get('brand', '')} {intent_data.get('product', '')}")

        # 3. 处理意图
        intent = intent_data.get("intent", "unknown")

        # 需要澄清
        if intent_data.get("clarification_needed"):
            response = intent_data.get("clarification_question", "请告诉我更多信息。")
            self.session.add_to_history("assistant", response)
            return response

        # 帮助
        if intent == "help":
            response = self.config.welcome_message
            self.session.add_to_history("assistant", response)
            return response

        # 未知意图
        if intent == "unknown":
            response = "我不太理解您的意思。请尝试说：\n- 分析 德芙 巧克力\n- 搜索小红书 德芙巧克力避雷\n- 搜索黑猫 德芙"
            self.session.add_to_history("assistant", response)
            return response

        # 4. 构建工作流上下文
        # 检查是否已有当前商品的分析结果
        existing_result = None
        brand = intent_data.get("brand", "")
        product = intent_data.get("product", "")
        current_product_name = f"{brand} {product}".strip()

        if self.session.current_analysis and self.session.current_analysis.product_name == current_product_name:
            existing_result = self.session.current_analysis
            logger.info(f"将复用已有分析结果: {current_product_name}")

        context = WorkflowContext(
            brand=brand,
            product=product,
            need_xiaohongshu=intent_data.get("need_xiaohongshu", False),
            need_heimao=intent_data.get("need_heimao", False),
            result=existing_result
        )

        # 5. 执行工作流
        try:
            workflow = self.workflow_factory.create(intent)
            result = workflow.execute(context)

            # 6. 格式化响应
            response = self._format_response(result)

        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            response = f"分析过程中出现错误: {e}\n请稍后重试或换个方式提问。"

        # 7. 保存对话
        self.session.add_to_history("assistant", response)

        return response

    def _format_response(self, result: AnalysisResult) -> str:
        """格式化分析结果"""
        lines = []

        # 标题
        lines.append(f"\n📦 {result.product_name}")
        lines.append("─" * 50)

        # 基础信息
        if result.product_info:
            lines.append(f"\n💰 价格: {result.product_info.price}")
            lines.append(f"🏪 店铺: {result.product_info.shop_name}")

        # 统计结果
        if result.statistics and result.statistics.get("total", 0) > 0:
            stats = result.statistics
            lines.append(f"\n📊 评论分析:")
            lines.append(f"   总评论: {stats['total']}条")
            lines.append(f"   好评率: {stats['positive_rate']:.0%}")
            lines.append(f"   差评率: {stats['negative_rate']:.0%}")
            if stats.get('sarcasm_count', 0) > 0:
                lines.append(f"   ⚠️ 疑似虚假好评: {stats['sarcasm_count']}条")

        # 小红书数据
        if result.xiaohongshu_notes:
            lines.append(f"\n📱 小红书笔记: {len(result.xiaohongshu_notes)}条")

        # 黑猫数据
        if result.heimao_complaints:
            lines.append(f"\n⚠️ 黑猫投诉: {len(result.heimao_complaints)}条")

        # 总结和建议
        if result.summary:
            lines.append(f"\n📝 分析总结:")
            lines.append(result.summary)

        if result.advice:
            lines.append(f"\n💡 购买建议:")
            lines.append(result.advice)

        return "\n".join(lines)

    def _save_session(self):
        """保存会话到文件"""
        try:
            session_file = paths_config.data_dir / session_config.session_file
            data = {
                "session_id": self.session.session_id,
                "current_analysis": self.session.current_analysis.to_dict() if self.session.current_analysis else None,
                "history_count": len(self.session.analysis_history),
                "last_updated": datetime.now().isoformat()
            }
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存会话失败: {e}")

    def _load_session(self):
        """加载历史会话"""
        try:
            session_file = paths_config.data_dir / session_config.session_file
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"已加载历史会话: {data.get('session_id')}")
        except Exception as e:
            logger.warning(f"加载会话失败: {e}")

    def _clear_session(self):
        """清除会话"""
        self.session = Session()
        print("   🧹 已清除当前会话")

    def _show_history(self):
        """显示分析历史"""
        if not self.session.analysis_history:
            print("   📭 暂无分析历史")
            return

        print(f"\n📚 分析历史 (共{len(self.session.analysis_history)}条):")
        for i, analysis in enumerate(self.session.analysis_history[-5:], 1):
            status = "✅" if analysis.status.value == "completed" else "❌"
            print(f"   {i}. {status} {analysis.product_name}")

    def _shutdown(self):
        """关闭Agent"""
        logger.info("关闭Agent...")
        if self.config.auto_save:
            self._save_session()
        print("\n👋 再见！")


class AgentBuilder:
    """Agent构建器 - 流式构建"""

    def __init__(self):
        self.config = AgentConfig()
        self.driver = None

    def with_driver(self, driver):
        """设置WebDriver"""
        self.driver = driver
        return self

    def with_profile(self, profile_dir: str):
        """设置浏览器配置目录"""
        self.config.profile_dir = profile_dir
        return self

    def with_driver_path(self, path: str):
        """设置驱动路径"""
        self.config.driver_path = path
        return self

    def with_auto_save(self, auto_save: bool):
        """设置自动保存"""
        self.config.auto_save = auto_save
        return self

    def build(self) -> BileizhenAgent:
        """构建Agent"""
        agent = BileizhenAgent(self.config)
        agent.initialize(self.driver)
        return agent


def create_driver(driver_path: str = None, profile_dir: str = None):
    """创建WebDriver"""
    driver_path = driver_path or paths_config.driver_path
    profile_dir = profile_dir or paths_config.profile_dir

    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)

    options = Options()
    options.use_chromium = True
    options.add_argument(f"user-data-dir={profile_dir}")

    # 其他优化选项
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    service = Service(driver_path)
    return webdriver.Edge(service=service, options=options)


def main():
    """主入口"""
    # 创建并配置Agent
    driver = create_driver()

    try:
        # 登录流程
        print("请先登录以下平台：")
        input("1. 按回车打开淘宝并登录...")
        driver.get("https://www.taobao.com")
        input("2. 登录完成后按回车继续...")

        input("3. 按回车打开小红书并登录...")
        driver.get("https://www.xiaohongshu.com")
        input("4. 登录完成后按回车继续...")

        input("5. 按回车打开黑猫投诉...")
        driver.get("https://tousu.sina.com.cn")
        input("6. 登录完成后按回车启动Agent...")

        # 构建并运行Agent
        agent = AgentBuilder() \
            .with_driver(driver) \
            .with_auto_save(True) \
            .build()

        agent.run()

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
