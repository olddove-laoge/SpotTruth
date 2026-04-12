"""Agent API 服务 - 将新版 Agent 核心能力封装为 HTTP API

用于联调：
- 终端A: python agent_api.py (上游服务 :5000)
- 终端B: go run ./cmd/api-gateway (网关 :8080)
- 终端C: python run.py (Agent客户端)

API端点:
- GET  /healthz      健康检查
- GET  /readyz       就绪检查
- POST /api/analyze  分析评论（讽刺检测+情感分析）
- POST /api/classify 品类分类
- POST /api/summarize 生成总结报告

作者: 避雷真 Team
版本: 2.0.0
"""

import sys
import os
import json

# 确保能正确导入 agent 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from flask_cors import CORS
from agent import (
    UnifiedAnalyzer,
    KimiClient,
    CategoryClassifier,
    logger
)
from agent.models import Comment, SourceType, SentimentType

app = Flask(__name__)
CORS(app)

# ========== 初始化组件 ==========

try:
    logger.info("正在初始化 Agent API 服务...")
    llm = KimiClient()
    analyzer = UnifiedAnalyzer(llm)
    classifier = CategoryClassifier()
    logger.info("✅ Agent API 服务初始化完成")
except Exception as e:
    logger.error(f"初始化失败: {e}")
    raise


# ========== 健康检查端点 ==========

@app.route('/healthz', methods=['GET'])
def healthz():
    """健康检查 - 用于网关探测"""
    return jsonify({
        "status": "ok",
        "service": "agent-api",
        "version": "2.0.0",
        "components": {
            "llm": "initialized",
            "analyzer": "initialized",
            "classifier": "initialized"
        }
    }), 200


@app.route('/readyz', methods=['GET'])
def readyz():
    """就绪检查 - 用于网关流量切换"""
    try:
        # 简单验证组件可用
        _ = analyzer.category_classifier
        return jsonify({
            "status": "ready",
            "message": "Agent API 服务已就绪"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "not_ready",
            "error": str(e)
        }), 503


@app.route('/', methods=['GET'])
def index():
    """服务首页"""
    return jsonify({
        "service": "避雷真 Agent API",
        "version": "2.0.0",
        "endpoints": {
            "/healthz": "GET - 健康检查",
            "/readyz": "GET - 就绪检查",
            "/api/analyze": "POST - 分析评论（讽刺检测+情感分析）",
            "/api/classify": "POST - 品类分类",
            "/api/summarize": "POST - 生成总结报告",
            "/api/judge_sarcasm": "POST - LLM判断讽刺评论",
            "/api/parse_intent": "POST - 解析用户意图（对话式）",
            "/api/analyze_xiaohongshu": "POST - 分析小红书笔记",
            "/api/analyze_heimao": "POST - 分析黑猫投诉"
        }
    }), 200




# ========== 爬虫接口 ==========

import threading
from agent.data_service import DataService, CrawlerConfig
from agent import create_driver

# 爬虫锁（Selenium 不是线程安全的）
crawler_lock = threading.Lock()


@app.route('/crawler/taobao/search', methods=['POST'])
def crawler_taobao_search():
    """
    搜索淘宝商品
    
    请求体:
    {
        "brand": "德芙",
        "product": "巧克力",
        "max_results": 5
    }
    """
    data = request.get_json() or {}
    brand = data.get('brand', '')
    product = data.get('product', '')
    max_results = data.get('max_results', 5)
    
    logger.info(f"爬虫-搜索淘宝: {brand} {product}")
    
    driver = None
    try:
        with crawler_lock:
            driver = create_driver()
            config = CrawlerConfig(driver=driver)
            data_service = DataService(config)
            
            result = data_service.search_product(
                brand=brand, 
                product=product, 
                max_results=max_results
            )
            
            driver.quit()
        
        if result and result.success and result.data:
            products = [{
                "name": p.name,
                "price": getattr(p, 'price', '未知'),
                "sales": getattr(p, 'sales', ''),
                "shop_name": getattr(p, 'shop_name', '未知店铺'),
                "shop_tag": getattr(p, 'shop_tag', ''),
                "url": p.url,
                "image_url": getattr(p, 'image_url', '')
            } for p in result.data[:max_results]]

            return jsonify({"success": True, "data": products}), 200
        else:
            error_msg = result.error if result and not result.success else "未找到商品"
            return jsonify({"success": False, "data": [], "error": error_msg}), 200

    except Exception as e:
        logger.error(f"淘宝搜索失败: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/crawler/taobao/comments', methods=['POST'])
def crawler_taobao_comments():
    """
    获取淘宝评论
    
    请求体:
    {
        "url": "https://detail.tmall.com/...",
        "brand": "德芙",
        "product": "巧克力",
        "max_count": 50
    }
    """
    data = request.get_json() or {}
    url = data.get('url', '')
    brand = data.get('brand', '')
    product = data.get('product', '')
    max_count = data.get('max_count', 50)
    
    logger.info(f"爬虫-获取评论: {url[:50]}...")
    
    driver = None
    try:
        with crawler_lock:
            driver = create_driver()
            config = CrawlerConfig(driver=driver)
            data_service = DataService(config)
            
            result = data_service.get_comments(
                url=url,
                brand=brand,
                product=product,
                max_count=max_count
            )
            
            driver.quit()
        
        if result and result.success and result.data:
            comments = [{"text": c.text} for c in result.data]
            return jsonify({"success": True, "data": comments}), 200
        else:
            error_msg = result.error if result and not result.success else "未获取到评论"
            return jsonify({"success": False, "data": [], "error": error_msg}), 200

    except Exception as e:
        logger.error(f"获取评论失败: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/crawler/xiaohongshu/search', methods=['POST'])
def crawler_xiaohongshu_search():
    """
    搜索小红书笔记
    
    请求体:
    {
        "keyword": "德芙巧克力",
        "max_notes": 5
    }
    """
    data = request.get_json() or {}
    keyword = data.get('keyword', '')
    max_notes = data.get('max_notes', 5)
    
    logger.info(f"爬虫-搜索小红书: {keyword}")
    
    driver = None
    try:
        with crawler_lock:
            driver = create_driver()
            config = CrawlerConfig(driver=driver)
            data_service = DataService(config)
            
            result = data_service.search_xiaohongshu(
                keyword=keyword,
                max_notes=max_notes
            )
            
            driver.quit()
        
        if result and result.success:
            notes = [{"text": n.text} for n in (result.data or [])]
            logger.info(f"小红书搜索完成，返回 {len(notes)} 条笔记")
            return jsonify({"success": True, "data": notes}), 200
        else:
            error_msg = result.error if result else "未找到笔记"
            logger.warning(f"小红书搜索失败: {error_msg}")
            return jsonify({"success": False, "data": [], "error": error_msg}), 200

    except Exception as e:
        logger.error(f"小红书搜索失败: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/crawler/heimao/search', methods=['POST'])
def crawler_heimao_search():
    """
    搜索黑猫投诉
    
    请求体:
    {
        "brand": "德芙",
        "max_complaints": 30
    }
    """
    data = request.get_json() or {}
    brand = data.get('brand', '')
    max_complaints = data.get('max_complaints', 30)
    
    logger.info(f"爬虫-搜索黑猫: {brand}")
    
    driver = None
    try:
        with crawler_lock:
            driver = create_driver()
            config = CrawlerConfig(driver=driver)
            data_service = DataService(config)
            
            result = data_service.search_heimao(
                brand=brand,
                max_complaints=max_complaints
            )
            
            driver.quit()
        
        if result and result.success and result.data:
            complaints = [{"text": c.text} for c in result.data]
            return jsonify({"success": True, "data": complaints}), 200
        else:
            error_msg = result.error if result and not result.success else "未找到投诉"
            return jsonify({"success": False, "data": [], "error": error_msg}), 200
            
    except Exception as e:
        logger.error(f"黑猫搜索失败: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return jsonify({"success": False, "error": str(e)}), 500


# ========== 业务API端点 ==========


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    分析评论 - 完整的讽刺检测+情感分析流程

    请求体:
    {
        "comments": ["评论1", "评论2", ...],
        "product_name": "商品名称",
        "category": "品类（可选，自动判断）"
    }

    响应:
    {
        "product_name": "商品名称",
        "category": "判断后的品类",
        "statistics": {
            "total": 100,
            "positive_count": 80,
            "negative_count": 20,
            "sarcasm_count": 5,
            "positive_rate": 0.8,
            "negative_rate": 0.2
        },
        "results": [
            {
                "text": "评论内容",
                "sentiment": "positive/negative",
                "is_sarcasm": true/false,
                "confidence": 0.95,
                "llm_analysis": "LLM分析理由（如果是讽刺）"
            }
        ]
    }
    """
    try:
        data = request.get_json() or {}
        comments_text = data.get('comments', [])
        product_name = data.get('product_name', '未知商品')
        category = data.get('category', '')

        # 参数校验
        if not comments_text:
            return jsonify({"error": "comments不能为空"}), 400

        if not isinstance(comments_text, list):
            return jsonify({"error": "comments必须是字符串数组"}), 400

        logger.info(f"收到分析请求: {product_name}, {len(comments_text)}条评论")

        # 构建 Comment 对象
        comments = [
            Comment(text=str(c), source=SourceType.TAOBAO)
            for c in comments_text if c
        ]

        # 自动判断品类
        if not category:
            category = classifier.classify(product_name)
            logger.info(f"自动判断品类: {category}")

        # 执行统一分析（讽刺检测 + LLM判断 + 情感分析）
        results = analyzer.analyze_comments(comments, product_name, category)

        # 计算统计
        stats = analyzer.calculate_statistics(results)

        # 构建响应
        response_data = {
            "product_name": product_name,
            "category": category,
            "statistics": stats,
            "results": [
                {
                    "text": r.text,
                    "sentiment": r.sentiment.value,
                    "is_sarcasm": r.is_sarcasm,
                    "confidence": round(r.confidence, 4),
                    "sarcasm_confidence": round(r.sarcasm_confidence, 4) if r.is_sarcasm else 0,
                    "llm_analysis": r.llm_analysis if r.llm_analysis else None
                }
                for r in results
            ]
        }

        logger.info(f"分析完成: 好评率{stats['positive_rate']:.1%}, "
                   f"讽刺{stats['sarcasm_count']}条")

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"分析接口出错: {e}")
        return jsonify({
            "error": f"分析失败: {str(e)}"
        }), 500


@app.route('/api/classify', methods=['POST'])
def classify():
    """
    品类分类

    请求体:
    {
        "product_name": "iPhone 15"
    }

    响应:
    {
        "product_name": "iPhone 15",
        "category": "electronics"
    }
    """
    try:
        data = request.get_json() or {}
        product_name = data.get('product_name', '')

        if not product_name:
            return jsonify({"error": "product_name不能为空"}), 400

        category = classifier.classify(product_name)

        return jsonify({
            "product_name": product_name,
            "category": category,
            "keywords_match": category != "electronics"  # 是否匹配到关键词
        }), 200

    except Exception as e:
        logger.error(f"分类接口出错: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/summarize', methods=['POST'])
def summarize():
    """
    生成总结报告

    请求体:
    {
        "statistics": {
            "total": 100,
            "positive_rate": 0.8,
            "negative_rate": 0.2,
            "sarcasm_count": 5
        },
        "sample_comments": [
            {"text": "评论", "sentiment": "positive", "is_sarcasm": false}
        ]
    }

    响应:
    {
        "summary": "分析总结...",
        "advice": "购买建议..."
    }
    """
    try:
        data = request.get_json() or {}
        stats = data.get('statistics', {})
        sample_comments = data.get('sample_comments', [])

        # 准备分析数据
        analysis_data = {
            "statistics": stats,
            "sample_comments": sample_comments[:20]  # 最多20条
        }

        logger.info("正在生成总结报告...")

        # 生成总结
        summary = llm.generate_summary(analysis_data)

        # 生成建议
        advice = llm.generate_advice(summary, "")

        return jsonify({
            "summary": summary,
            "advice": advice
        }), 200

    except Exception as e:
        logger.error(f"总结接口出错: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/judge_sarcasm', methods=['POST'])
def judge_sarcasm():
    """
    LLM判断讽刺评论的真实情感

    请求体:
    {
        "text": "呵呵，真是太好了呢",
        "topic": "德芙巧克力"
    }

    响应:
    {
        "text": "呵呵，真是太好了呢",
        "topic": "德芙巧克力",
        "real_sentiment": "negative",
        "confidence": 0.9,
        "reasoning": "分析理由..."
    }
    """
    try:
        data = request.get_json() or {}
        text = data.get('text', '')
        topic = data.get('topic', '')

        if not text:
            return jsonify({"error": "text不能为空"}), 400

        result = llm.judge_sarcasm(text, topic)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"讽刺判断接口出错: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/parse_intent', methods=['POST'])
def parse_intent():
    """
    解析用户意图 - 支持对话式交互

    请求体:
    {
        "user_input": "帮我分析德芙巧克力",
        "conversation_history": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好！我是避雷真..."}
        ],
        "current_product": ""  // 当前正在分析的商品（可选）
    }

    响应:
    {
        "intent": "analyze",
        "brand": "德芙",
        "product": "巧克力",
        "need_xiaohongshu": false,
        "need_heimao": false,
        "clarification_needed": false,
        "clarification_question": "",
        "response": "好的，我来帮您分析德芙巧克力"  // 可直接回复用户的话
    }
    """
    try:
        data = request.get_json() or {}
        user_input = data.get('user_input', '')
        history = data.get('conversation_history', [])
        current_product = data.get('current_product', '')
        analyzed_platforms = data.get('analyzed_platforms', [])

        if not user_input:
            return jsonify({"error": "user_input不能为空"}), 400

        logger.info(f"解析意图: {user_input}, 已分析平台: {analyzed_platforms}")

        # 调用LLM解析意图
        intent_data = llm.parse_intent(user_input, history, current_product, analyzed_platforms)

        # 生成友好的响应语
        response_text = _generate_intent_response(intent_data, current_product)
        intent_data['response'] = response_text

        return jsonify(intent_data), 200

    except Exception as e:
        logger.error(f"意图解析接口出错: {e}")
        return jsonify({"error": str(e)}), 500


def _generate_intent_response(intent_data: dict, current_product: str) -> str:
    """根据意图生成友好的响应语"""
    intent = intent_data.get('intent', 'unknown')
    brand = intent_data.get('brand', '')
    product = intent_data.get('product', '')
    clarification = intent_data.get('clarification_question', '')

    if clarification:
        return clarification

    if intent == 'analyze':
        if brand and product:
            return f"好的，我来帮您分析 {brand} {product} 的口碑情况。"
        elif product:
            return f"好的，我来帮您分析 {product} 的口碑情况。"
        else:
            return "好的，我来帮您分析这个商品。"

    elif intent == 'search_xhs':
        keyword = f"{brand} {product}".strip() if (brand or product) else current_product
        return f"好的，我来搜索小红书关于 {keyword} 的笔记。"

    elif intent == 'search_heimao':
        keyword = brand if brand else current_product
        return f"好的，我来查询 {keyword} 在黑猫投诉平台的情况。"

    elif intent == 'help':
        return """我可以帮您：
• 分析商品口碑（淘宝评论、小红书、黑猫投诉）
• 识别虚假好评和阴阳怪气评价
• 提供购买建议

请直接告诉我您想了解什么商品，例如："分析德芙巧克力" """

    elif intent == 'unknown':
        return "我不太理解您的意思。您可以尝试说：\n• 分析 德芙 巧克力\n• 搜索小红书 德芙巧克力避雷\n• 搜索黑猫 德芙"

    else:
        return "收到，正在处理您的请求..."


@app.route('/api/analyze_xiaohongshu', methods=['POST'])
def analyze_xiaohongshu():
    """
    分析小红书笔记内容

    请求体:
    {
        "notes": [
            {"title": "标题", "content": "内容...", "likes": 100},
            ...
        ],
        "keyword": "搜索关键词"
    }

    响应:
    {
        "summary": "小红书用户主要反馈...",
        "key_points": ["负面点1", "避坑点2"],
        "sentiment": "mostly_negative"
    }
    """
    try:
        data = request.get_json() or {}
        notes = data.get('notes', [])
        keyword = data.get('keyword', '')

        if not notes:
            return jsonify({"error": "notes不能为空"}), 400

        logger.info(f"分析小红书笔记: {keyword}, {len(notes)}条")

        # 构建分析提示
        notes_text = "\n\n".join([
            f"笔记{i+1}:\n标题: {n.get('title', '')}\n内容: {n.get('content', '')[:300]}..."
            for i, n in enumerate(notes[:10])
        ])

        prompt = f"""分析以下关于"{keyword}"的小红书笔记，提取主要观点：

{notes_text}

请总结：
1. 主要负面观点
2. 避坑点
3. 用户抱怨最多的问题
4. 整体口碑倾向

以简洁的JSON格式输出：
{{
    "summary": "整体总结...",
    "key_points": ["点1", "点2", "点3"],
    "sentiment": "mostly_positive|mixed|mostly_negative"
}}"""

        response = llm.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.7
        )

        content = response.content.strip()

        # 提取JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # 如果解析失败，返回原始文本
            result = {
                "summary": content[:500],
                "key_points": [],
                "sentiment": "unknown"
            }

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"小红书分析接口出错: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/analyze_heimao', methods=['POST'])
def analyze_heimao():
    """
    分析黑猫投诉内容

    请求体:
    {
        "complaints": [
            {"title": "投诉标题", "content": "内容...", "status": "处理中"},
            ...
        ],
        "brand": "品牌名"
    }

    响应:
    {
        "summary": "主要投诉类型...",
        "complaint_types": ["质量问题", "售后服务"],
        "severity": "high|medium|low",
        "recommendation": "建议谨慎购买"
    }
    """
    try:
        data = request.get_json() or {}
        complaints = data.get('complaints', [])
        brand = data.get('brand', '')

        if not complaints:
            return jsonify({"error": "complaints不能为空"}), 400

        logger.info(f"分析黑猫投诉: {brand}, {len(complaints)}条")

        # 构建分析提示
        complaints_text = "\n\n".join([
            f"投诉{i+1}:\n标题: {c.get('title', '')}\n内容: {c.get('content', '')[:300]}..."
            for i, c in enumerate(complaints[:10])
        ])

        prompt = f"""分析以下关于"{brand}"的黑猫投诉，提取主要问题：

{complaints_text}

请总结：
1. 主要投诉类型
2. 涉及的主要问题
3. 严重程度和频率
4. 购买建议

以简洁的JSON格式输出：
{{
    "summary": "整体总结...",
    "complaint_types": ["类型1", "类型2"],
    "severity": "high|medium|low",
    "recommendation": "建议..."
}}"""

        response = llm.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.7
        )

        content = response.content.strip()

        # 提取JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = {
                "summary": content[:500],
                "complaint_types": [],
                "severity": "unknown",
                "recommendation": "建议查看更多用户评价"
            }

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"黑猫分析接口出错: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/compare_conclusion', methods=['POST'])
def compare_conclusion():
    """
    生成商品对比结论

    请求体:
    {
        "product_a_name": "商品A名称",
        "product_b_name": "商品B名称",
        "stats_a": {"total": 100, "positive_rate": 0.8, ...},
        "stats_b": {"total": 100, "positive_rate": 0.7, ...},
        "summary_a": "商品A的分析总结",
        "summary_b": "商品B的分析总结",
        "advice_a": "商品A的购买建议",
        "advice_b": "商品B的购买建议",
        "heimao_analysis_a": {...},
        "heimao_analysis_b": {...},
        "xhs_analysis_a": {...},
        "xhs_analysis_b": {...}
    }

    响应:
    {
        "conclusion": "对比结论文本..."
    }
    """
    try:
        data = request.get_json() or {}

        product_a_name = data.get('product_a_name', '')
        product_b_name = data.get('product_b_name', '')
        stats_a = data.get('stats_a', {})
        stats_b = data.get('stats_b', {})
        summary_a = data.get('summary_a', '')
        summary_b = data.get('summary_b', '')
        advice_a = data.get('advice_a', '')
        advice_b = data.get('advice_b', '')
        heimao_analysis_a = data.get('heimao_analysis_a')
        heimao_analysis_b = data.get('heimao_analysis_b')
        xhs_analysis_a = data.get('xhs_analysis_a')
        xhs_analysis_b = data.get('xhs_analysis_b')
        has_taobao_a = data.get('has_taobao_a', False)
        has_taobao_b = data.get('has_taobao_b', False)

        logger.info(f"生成对比结论: {product_a_name} vs {product_b_name}")

        conclusion = llm.generate_comparison_conclusion(
            product_a_name=product_a_name,
            product_b_name=product_b_name,
            stats_a=stats_a,
            stats_b=stats_b,
            summary_a=summary_a,
            summary_b=summary_b,
            advice_a=advice_a,
            advice_b=advice_b,
            heimao_analysis_a=heimao_analysis_a,
            heimao_analysis_b=heimao_analysis_b,
            xhs_analysis_a=xhs_analysis_a,
            xhs_analysis_b=xhs_analysis_b,
            has_taobao_a=has_taobao_a,
            has_taobao_b=has_taobao_b
        )

        return jsonify({"conclusion": conclusion}), 200

    except Exception as e:
        logger.error(f"对比结论接口出错: {e}")
        return jsonify({"error": str(e)}), 500


# ========== 错误处理 ==========

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "接口不存在", "path": request.path}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "服务器内部错误"}), 500



def main():
    """启动 Agent API 服务"""
    print("\n" + "=" * 60)
    print("🤖 避雷真 Agent API 服务")
    print("=" * 60)
    print("\n📋 使用方式:")
    print("   终端A: python agent_api.py")
    print("   终端B: go run ./cmd/api-gateway")
    print("   终端C: python run.py")
    print("\n🔗 API端点:")
    print("   健康检查: http://127.0.0.1:5000/healthz")
    print("   评论分析: POST http://127.0.0.1:5000/api/analyze")
    print("   品类分类: POST http://127.0.0.1:5000/api/classify")
    print("\n" + "=" * 60 + "\n")

    # 启动服务
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # 生产环境关闭debug
        threaded=True  # 启用多线程
    )



# ========== 启动入口 ==========
if __name__ == '__main__':
    main()


