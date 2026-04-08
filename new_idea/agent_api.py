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

# 确保能正确导入 agent 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from agent import (
    UnifiedAnalyzer,
    KimiClient,
    CategoryClassifier,
    logger
)
from agent.models import Comment, SourceType, SentimentType

app = Flask(__name__)

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
            "/api/judge_sarcasm": "POST - LLM判断讽刺评论"
        }
    }), 200


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


# ========== 错误处理 ==========

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "接口不存在", "path": request.path}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "服务器内部错误"}), 500


# ========== 启动入口 ==========

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


if __name__ == '__main__':
    main()
