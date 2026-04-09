from flask import Flask, render_template, request, redirect, url_for, jsonify
import subprocess
import os
import time
import re
import uuid
import requests

app = Flask(__name__, 
           static_url_path='/static',
           static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static'))

DEFAULT_GATEWAY_BASE_URL = os.environ.get('SPOTTRUTH_GATEWAY_URL', 'http://127.0.0.1:8080')

CATEGORY_KEYWORDS = {
    "book": ["书", "图书", "小说", "教材", "绘本", "书籍"],
    "tablet": ["平板", "ipad", "平板电脑", "surface"],
    "electronics": ["手机", "iphone", "安卓", "电脑", "笔记本", "耳机", "电子"],
    "fruit": ["水果", "苹果", "橙子", "芒果", "草莓", "荔枝"],
    "shampoo": ["洗发水", "护发素", "洗头膏", "洗发液"],
    "dairy": ["牛奶", "酸奶", "奶酪", "奶粉", "乳制品"],
    "clothing": ["衣服", "T恤", "衬衫", "裙子", "裤子", "外套", "服装"],
    "water_heater": ["热水器", "电热水器", "燃气热水器"],
    "hotel": ["酒店", "民宿", "宾馆", "客栈", "公寓"],
}


def classify_product_category(product_name):
    """轻量品类分类工具，用于联调链路验证。"""
    if not product_name:
        return "electronics"

    normalized = product_name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw.lower() in normalized for kw in keywords):
            return category

    return "electronics"


def normalize_gateway_base_url(base_url):
    """统一网关地址格式，避免双斜杠拼接。"""
    return (base_url or DEFAULT_GATEWAY_BASE_URL).strip().rstrip('/')


def build_gateway_request_headers() -> dict:
    """构造请求网关时的追踪与鉴权头。"""
    headers = {
        "X-Request-ID": str(uuid.uuid4()),
    }

    token = os.environ.get('SPOTTRUTH_GATEWAY_TOKEN', '').strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers

def convert_urls_to_links(text):
    """将文本中的URL转换为HTML链接"""
    if not text:
        return ""
    
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return url_pattern.sub(
        lambda match: f'<a href="{match.group(0)}" target="_blank">{match.group(0)}</a>',
        text
    )

def load_file_content(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return convert_urls_to_links(content)
    except Exception as e:
        print(f"读取文件失败: {filepath}, 错误: {str(e)}")
        return "内容加载失败"

# 删除自定义静态文件路由，使用Flask默认静态文件服务

@app.route('/analyze', methods=['POST'])
def analyze():
    product_url = request.form['product_url']
    
    try:
        # 调用taobao_new.py脚本
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(base_dir, 'AIGC', 'Comment_crawling_and_analysis', 'taobao_new.py')
        
        if not os.path.exists(script_path):
            return f"脚本文件不存在: {script_path}", 500
            
        # 使用Popen启动进程并分离
        try:
            process = subprocess.Popen(
                ['python', script_path, '--manual_input', 'False', '--preset_url', product_url],
                cwd=base_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True  # 分离进程
            )
            
            # 非阻塞读取部分输出
            stdout, stderr = process.communicate(timeout=5)
            
            if process.returncode is not None and process.returncode != 0:
                error_msg = f"脚本执行失败(状态码{process.returncode}):\n"
                error_msg += f"标准输出:\n{stdout}\n" if stdout else ""
                error_msg += f"错误输出:\n{stderr}\n" if stderr else ""
                return error_msg, 500
                
        except subprocess.TimeoutExpired:
            # 进程仍在运行，继续后台执行
            pass
        except Exception as e:
            return f"启动爬虫失败: {str(e)}", 500
            
        # 同步执行分析程序调用
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        marker_file = os.path.join(base_dir, 'AIGC', 'analysis_markers', 'brand_analysis_complete.flag')
        
        # 确认的分析程序绝对路径
        analysis_scripts = [
            os.path.join(base_dir, 'AIGC', 'Comment_crawling_and_analysis', 'batch_processor.py'),
            os.path.join(base_dir, 'AIGC', 'Comment_crawling_and_analysis', 'batch_processor_200lines.py'),
            os.path.join(base_dir, 'AIGC', 'Comment_crawling_and_analysis', 'keywords.py'),
            os.path.join(base_dir, 'AIGC', 'Comment_crawling_and_analysis', 'keywords_200lines.py')
        ]
        
        # 验证所有分析程序是否存在
        missing_scripts = [s for s in analysis_scripts if not os.path.exists(s)]
        if missing_scripts:
            print(f'错误: 以下分析程序不存在: {missing_scripts}')
            return redirect(url_for('index'))
        
        # 等待标记文件出现(最长5分钟)
        print('等待分析标记文件出现...')
        wait_time = 300
        start_time = time.time()
        
        while time.time() - start_time < wait_time:
            if os.path.exists(marker_file):
                print('检测到标记文件，开始执行分析程序')
                try:
                    # 依次执行每个分析程序
                    for script in analysis_scripts:
                        print(f'正在执行: {script}')
                        result = subprocess.run(
                            ['python', script],
                            cwd=base_dir,
                            capture_output=True,
                            text=True
                        )
                        if result.returncode != 0:
                            print(f'分析程序执行失败: {script}')
                            print(f'错误输出: {result.stderr}')
                        else:
                            print(f'成功执行: {script}')
                    
                    print('所有分析程序执行完成')
                    
                    # 先删除标记文件
                    if os.path.exists(marker_file):
                        try:
                            os.remove(marker_file)
                            print('已删除标记文件')
                        except Exception as e:
                            print(f'删除标记文件失败: {str(e)}')
                    
                    # 执行可视化程序及后续程序
                    show_defect_path = os.path.join(
                        base_dir, 
                        'AIGC', 
                        'Comment_crawling_and_analysis', 
                        'show_defect.py'
                    )
                    if os.path.exists(show_defect_path):
                        print('开始执行可视化程序...')
                        try:
                            result = subprocess.run(
                                ['python', show_defect_path],
                                cwd=base_dir,
                                capture_output=True,
                                text=True
                            )
                            if result.returncode == 0:
                                print('可视化程序执行成功')
                                
                                # 执行rela_prod_links_scraper.py
                                scraper_path = os.path.join(
                                    base_dir,
                                    'AIGC',
                                    'Comparison_of_similar_products_and_external_link_information',
                                    'rela_prod_links_scraper.py'
                                )
                                if os.path.exists(scraper_path):
                                    print('开始执行商品链接爬取程序...')
                                    try:
                                        result = subprocess.run(
                                            ['python', scraper_path],
                                            cwd=base_dir,
                                            capture_output=True,
                                            text=True
                                        )
                                        if result.returncode == 0:
                                            print('商品链接爬取程序执行成功')
                                            
                                            # 执行multi_page_scraper.py
                                            multi_scraper_path = os.path.join(
                                                base_dir,
                                                'AIGC',
                                                'Comment_crawling_and_analysis',
                                                'multi_page_scraper.py'
                                            )
                                            if os.path.exists(multi_scraper_path):
                                                print('开始执行多页评论爬取程序...')
                                                try:
                                                    result = subprocess.run(
                                                        ['python', multi_scraper_path],
                                                        cwd=base_dir,
                                                        capture_output=True,
                                                        text=True
                                                    )
                                                    if result.returncode == 0:
                                                        print('多页评论爬取程序执行成功')
                                                        
                                                        # 执行relative_keywords.py
                                                        keywords_path = os.path.join(
                                                            base_dir,
                                                            'AIGC',
                                                            'Comment_crawling_and_analysis',
                                                            'relative_keywords.py'
                                                        )
                                                        if os.path.exists(keywords_path):
                                                            print('开始执行相关商品关键词分析...')
                                                            try:
                                                                result = subprocess.run(
                                                                    ['python', keywords_path],
                                                                    cwd=base_dir,
                                                                    capture_output=True,
                                                                    text=True
                                                                )
                                                                if result.returncode == 0:
                                                                    print('相关商品关键词分析执行成功')
                                                                else:
                                                                    print(f'相关商品关键词分析执行失败: {result.stderr}')
                                                            except Exception as e:
                                                                print(f'执行相关商品关键词分析出错: {str(e)}')
                                                        else:
                                                            print(f'相关商品关键词分析程序不存在: {keywords_path}')
                                                        
                                                        # 执行relative_prod_analysis.py
                                                        analysis_path = os.path.join(
                                                            base_dir,
                                                            'AIGC',
                                                            'Comment_crawling_and_analysis',
                                                            'relative_prod_analysis.py'
                                                        )
                                                        if os.path.exists(analysis_path):
                                                            print('开始执行相关商品评论分析...')
                                                            try:
                                                                result = subprocess.run(
                                                                    ['python', analysis_path],
                                                                    cwd=base_dir,
                                                                    capture_output=True,
                                                                    text=True
                                                                )
                                                                if result.returncode == 0:
                                                                    print('相关商品评论分析执行成功')
                                                                else:
                                                                    print(f'相关商品评论分析执行失败: {result.stderr}')
                                                            except Exception as e:
                                                                print(f'执行相关商品评论分析出错: {str(e)}')
                                                        else:
                                                            print(f'相关商品评论分析程序不存在: {analysis_path}')
                                                        
                                                        # 执行comment_comprison.py
                                                        comparison_path = os.path.join(
                                                            base_dir,
                                                            'AIGC',
                                                            'Comparison_of_similar_products_and_external_link_information',
                                                            'AIs',
                                                            'comment_comprison.py'
                                                        )
                                                        if os.path.exists(comparison_path):
                                                            print('开始执行商品评论比较分析...')
                                                            try:
                                                                result = subprocess.run(
                                                                    ['python', comparison_path],
                                                                    cwd=base_dir,
                                                                    capture_output=True,
                                                                    text=True
                                                                )
                                                                if result.returncode == 0:
                                                                    print('商品评论比较分析执行成功')
                                                                else:
                                                                    print(f'商品评论比较分析执行失败: {result.stderr}')
                                                            except Exception as e:
                                                                print(f'执行商品评论比较分析出错: {str(e)}')
                                                        else:
                                                            print(f'商品评论比较分析程序不存在: {comparison_path}')
                                                        
                                                    else:
                                                        print(f'多页评论爬取程序执行失败: {result.stderr}')
                                                except Exception as e:
                                                    print(f'执行多页评论爬取程序出错: {str(e)}')
                                            else:
                                                print(f'多页评论爬取程序不存在: {multi_scraper_path}')
                                                
                                        else:
                                            print(f'商品链接爬取程序执行失败: {result.stderr}')
                                    except Exception as e:
                                        print(f'执行商品链接爬取程序出错: {str(e)}')
                                else:
                                    print(f'商品链接爬取程序不存在: {scraper_path}')
                                    
                            else:
                                print(f'可视化程序执行失败: {result.stderr}')
                        except Exception as e:
                            print(f'执行可视化程序出错: {str(e)}')
                    else:
                        print(f'可视化程序不存在: {show_defect_path}')
                    
                    # 创建分析完成标记文件
                    marker_dir = os.path.dirname(ANALYSIS_COMPLETE_MARKER)
                    os.makedirs(marker_dir, exist_ok=True)
                    with open(ANALYSIS_COMPLETE_MARKER, 'w') as f:
                        f.write('analysis_complete')
                    
                    break
                except Exception as e:
                    print(f'执行分析程序时出错: {str(e)}')
                    break
            time.sleep(10)
            
        return redirect(url_for('index'))
    except Exception as e:
        return f"系统错误: {str(e)}", 500

# 分析完成标记文件路径
ANALYSIS_COMPLETE_MARKER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                      'AIGC', 'analysis_markers', 'analysis_complete.flag')

@app.route('/run_multi_login', methods=['POST'])
def run_multi_login():
    """执行多平台登录脚本"""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(base_dir, 'AIGC', 'multi_platform_login.py')
        
        if not os.path.exists(script_path):
            return "多平台登录脚本不存在", 404
            
        result = subprocess.run(
            ['python', script_path],
            cwd=base_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return "平台登录管理已完成", 200
        else:
            return f"执行失败: {result.stderr}", 500
            
    except Exception as e:
        return f"系统错误: {str(e)}", 500

@app.route('/get_product_name')
def get_product_name():
    """获取产品名称"""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        product_name_path = os.path.join(base_dir, 'AIGC', 'Comment_crawling_and_analysis', 'product_name.txt')
        
        if os.path.exists(product_name_path):
            with open(product_name_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        return "未命名商品"
    except Exception as e:
        print(f"获取产品名称失败: {str(e)}")
        return "未命名商品"


@app.route('/api/gateway/health', methods=['GET'])
def gateway_health():
    """检查Go网关健康状态。"""
    base_url = normalize_gateway_base_url(request.args.get('gateway_url', DEFAULT_GATEWAY_BASE_URL))
    health_url = f"{base_url}/healthz"

    try:
        response = requests.get(health_url, timeout=5)
        payload = {}
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text[:300]}

        return jsonify({
            "ok": response.ok,
            "status_code": response.status_code,
            "gateway_url": base_url,
            "health_url": health_url,
            "payload": payload,
        }), (200 if response.ok else 502)
    except requests.RequestException as e:
        return jsonify({
            "ok": False,
            "gateway_url": base_url,
            "health_url": health_url,
            "error": str(e),
        }), 502


@app.route('/api/python/tool-test', methods=['POST'])
def python_tool_test():
    """测试Python工具能力（通过网关转发到上游/api/classify）。"""
    data = request.get_json(silent=True) or {}
    product_name = (data.get('product_name') or '').strip()
    base_url = normalize_gateway_base_url(data.get('gateway_url', DEFAULT_GATEWAY_BASE_URL))

    if not product_name:
        return jsonify({"ok": False, "error": "product_name 不能为空"}), 400

    classify_url = f"{base_url}/api/classify"
    try:
        response = requests.post(
            classify_url,
            json={"product_name": product_name},
            headers=build_gateway_request_headers(),
            timeout=8,
        )
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text[:300]}

        category = payload.get('category') if isinstance(payload, dict) else None
        return jsonify({
            "ok": response.ok,
            "tool": "classify_category",
            "input": product_name,
            "category": category,
            "gateway_url": base_url,
            "classify_url": classify_url,
            "request_id": response.headers.get('X-Request-ID', ''),
            "payload": payload,
        }), (200 if response.ok else 502)
    except requests.RequestException as e:
        return jsonify({
            "ok": False,
            "tool": "classify_category",
            "input": product_name,
            "gateway_url": base_url,
            "classify_url": classify_url,
            "error": str(e),
        }), 502


@app.route('/api/integration/test', methods=['POST'])
def integration_test():
    """串联测试：Go网关健康检查 + 网关转发工具调用。"""
    data = request.get_json(silent=True) or {}
    product_name = (data.get('product_name') or '').strip()
    base_url = normalize_gateway_base_url(data.get('gateway_url', DEFAULT_GATEWAY_BASE_URL))

    if not product_name:
        return jsonify({"ok": False, "error": "product_name 不能为空"}), 400

    health_url = f"{base_url}/healthz"
    gateway_result = {
        "ok": False,
        "gateway_url": base_url,
        "health_url": health_url,
    }
    try:
        response = requests.get(health_url, timeout=5)
        gateway_result["ok"] = response.ok
        gateway_result["status_code"] = response.status_code
        try:
            gateway_result["payload"] = response.json()
        except ValueError:
            gateway_result["payload"] = {"raw": response.text[:300]}
    except requests.RequestException as e:
        gateway_result["error"] = str(e)

    python_tool_result = {
        "ok": False,
        "tool": "classify_category",
        "input": product_name,
    }
    classify_url = f"{base_url}/api/classify"
    if gateway_result.get("ok", False):
        try:
            response = requests.post(
                classify_url,
                json={"product_name": product_name},
                headers=build_gateway_request_headers(),
                timeout=8,
            )
            python_tool_result["ok"] = response.ok
            python_tool_result["status_code"] = response.status_code
            python_tool_result["request_id"] = response.headers.get('X-Request-ID', '')
            try:
                payload = response.json()
            except ValueError:
                payload = {"raw": response.text[:300]}
            python_tool_result["payload"] = payload
            if isinstance(payload, dict):
                python_tool_result["category"] = payload.get("category")
        except requests.RequestException as e:
            python_tool_result["error"] = str(e)
    else:
        python_tool_result["error"] = "网关健康检查失败，已跳过工具调用"

    python_tool_result["classify_url"] = classify_url

    all_ok = gateway_result.get("ok", False) and python_tool_result.get("ok", False)
    return jsonify({
        "ok": all_ok,
        "message": "联合链路可用" if all_ok else "联合链路存在异常，请检查网关或工具服务",
        "gateway": gateway_result,
        "python_tool": python_tool_result,
    }), (200 if all_ok else 502)


@app.route('/api/classify', methods=['POST'])
def classify_via_upstream():
    """上游分类接口：供网关代理转发使用。"""
    data = request.get_json(silent=True) or {}
    product_name = (data.get('product_name') or '').strip()

    if not product_name:
        return jsonify({"error": "product_name不能为空"}), 400

    category = classify_product_category(product_name)
    return jsonify({
        "product_name": product_name,
        "category": category,
        "keywords_match": category != "electronics"
    }), 200

@app.route('/')
def index():
    # 检查是否有分析完成标记
    if os.path.exists(ANALYSIS_COMPLETE_MARKER):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        try:
            # 1. 商品评价情感分布及差评关键词
            images = [
                '关键词统计.png',
                '情感分布.png', 
                '柱状图_关键词统计.png',
                '词云_关键词统计.png',
                '饼图_关键词统计.png'
            ]
            keywords_content = load_file_content(
                os.path.join(base_dir, 'AIGC', 'Comment_crawling_and_analysis', 'keywords.csv')
            )
            
            # 2. 小红书避雷笔记
            xhs_top5 = '\n'.join(
                load_file_content(
                    os.path.join(base_dir, 'AIGC', 'Comparison_of_similar_products_and_external_link_information', 'xhs_search_results.txt')
                ).split('\n')[:5]
            )
            xhs_analysis = load_file_content(
                os.path.join(base_dir, 'AIGC', 'Comparison_of_similar_products_and_external_link_information', 'xhs_analysis_result.txt')
            )
            
            # 3. 黑猫投诉平台分析结果
            tousu_content = load_file_content(
                os.path.join(base_dir, 'AIGC', 'Comparison_of_similar_products_and_external_link_information', 'tousu_analysis.txt')
            )
            
            # 4. 同类商品比较
            rela_prods = load_file_content(
                os.path.join(base_dir, 'AIGC', 'Comparison_of_similar_products_and_external_link_information', 'rela_prods_links.txt')
            )
            analysis_report = load_file_content(
                os.path.join(base_dir, 'AIGC', 'Comparison_of_similar_products_and_external_link_information', 'analysis_report.md')
            )
            
            # 删除标记文件，以便下次分析
            os.remove(ANALYSIS_COMPLETE_MARKER)
            
            return render_template('results.html',
                images=images,
                keywords_content=keywords_content,
                xhs_top5=xhs_top5,
                xhs_analysis=xhs_analysis,
                tousu_content=tousu_content,
                rela_prods=rela_prods,
                analysis_report=analysis_report,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            return f"加载分析结果失败: {str(e)}", 500
    else:
        # 显示初始输入页面
        return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
