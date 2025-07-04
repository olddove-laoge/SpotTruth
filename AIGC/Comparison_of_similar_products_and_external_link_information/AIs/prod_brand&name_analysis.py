# Please install OpenAI SDK first: `pip3 install openai`

from openai import OpenAI
import os
from datetime import datetime

def analyze_product_name(content, api_key="sk-959db6c460bb4ace9a066bd4c065981e", base_url="https://api.deepseek.com"):
    """
    压缩淘宝商品标题，只保留品牌名和产品品类
    
    参数:
        content (str): 要处理的商品标题文本
        api_key (str): DeepSeek API密钥，默认为测试密钥
        base_url (str): API基础URL，默认为DeepSeek
        
    返回:
        str: 压缩后的商品标题(品牌名 + 产品品类)
        
    异常:
        Exception: 如果API调用失败会抛出异常
    """
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": 
                 """
                **角色：** 你是一个专业的商品名称压缩器。
                **任务：** 压缩用户提供的淘宝商品标题，生成一个仅包含 **核心品牌名** 和 **核心产品品类** 的简洁标题。
                **输入：** 用户将提供一个完整的淘宝商品标题（通常冗长，包含促销词、规格、型号、无关描述等冗余信息）。
                **处理要求：**
                1.  **识别核心信息：** 仔细分析输入的标题，精准识别出商品的 **官方品牌名称（Brand）** 和 **最基础、通用的产品类别/品类（Category）**。
                2.  **剔除所有冗余信息：** 必须严格移除以下所有非核心元素：
                    *   促销词汇（如：2023新款、热卖爆款、限时折扣、正品保障、包邮）
                    *   型号/规格（如：iPhone 15 Pro Max 1TB 蓝色、 XL码、 i7-13700H）
                    *   形容词/修饰语（如：超薄、超大容量、高清、耐磨、透气、网红、明星同款）
                    *   店铺名称或促销活动信息（如：XX专卖店、618大促、双11狂欢）
                    *   与核心品牌和品类无关的任何其他描述性词语或短语。
                3.  **输出格式：**
                    *   **唯一输出：** 压缩后的标题字符串，**仅包含**识别出的 **品牌名 + 空格 + 品类名**。
                    *   **简洁直接：** 只保留最核心的两个元素（品牌 + 品类），不做任何额外添加。
                    *   **禁止前缀/后缀：** **绝对不要**添加任何如“压缩后的标题：”、“结果是：”等引导性文字或标点符号（如冒号、引号）。只输出纯文本的压缩结果。
                **目标：** 生成的结果应该像一个最基础的搜索关键词或产品核心身份标识，易于搜索和快速理解商品本质。

                **示例（仅用于理解任务，不要输出示例本身）：**
                *   输入： `【2023热卖】Apple/苹果 iPhone 15 Pro Max (A3108) 5G手机 全网通 超视网膜XDR显示屏 256GB 深空黑色 官方旗舰店`
                *   期望输出： `Apple iPhone` (或 `苹果 手机`，选择最核心/通用的品牌名和品类组合)
                *   输入： `Nike官方旗舰店 男子 AIR JORDAN 1 MID 运动鞋 篮球鞋 透气缓震 经典复古 白红黑`
                *   期望输出： `Nike 运动鞋` (或 `Nike 篮球鞋`，选择最通用的品类)
                *   输入： `美的(Midea) 大1.5匹 新一级能效 变频冷暖 智能自清洁 壁挂式空调 KFR-35GW/N8XHC1`
                *   期望输出： `美的 空调`

                **现在，请严格遵循以上要求处理用户输入的商品标题。只输出压缩后的核心品牌名+空格+品类名，不要任何其他文字。**
                 """
                },
                {"role": "user", "content": content},
            ],
            stream=False
        )
        
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"商品名称分析失败: {str(e)}")

# 保留原有直接执行功能以便向后兼容
if __name__ == "__main__":
    with open(r'AIGC\Comment_crawling_and_analysis\product_name.txt', 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    try:
        result = analyze_product_name(content)
        # 将结果写入文件
        output_path = r'AIGC\Comparison_of_similar_products_and_external_link_information\simple_prod_name_with_brand.txt'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
            
            # 自动调用爬虫脚本(同时运行)

    except Exception as e:
        print(f"错误: {str(e)}")

    import subprocess
    processes = []
    try:
        # 同时启动两个爬虫
        tousu_script = r"AIGC\Comparison_of_similar_products_and_external_link_information\tousu_crawler.py"
        xhs_script = r"AIGC\Comparison_of_similar_products_and_external_link_information\xiaohongshu_scraper.py"
        
        # 启动投诉爬虫并等待完成
        p1 = subprocess.Popen(["python", tousu_script])
        p1.wait()
        # 投诉爬虫完成后立即启动分析
        tousu_analysis = r"AIGC\Comparison_of_similar_products_and_external_link_information\AIs\tousu_analysis.py"
        subprocess.Popen(["python", tousu_analysis])
        
        # 启动小红书爬虫并等待完成
        p2 = subprocess.Popen(["python", xhs_script])
        p2.wait()
        # 小红书爬虫完成后立即启动分析
        xhs_analysis = r"AIGC\Comparison_of_similar_products_and_external_link_information\AIs\xhs_comment_analysis.py"
        subprocess.Popen(["python", xhs_analysis])
        
        print("爬虫脚本执行完成，分析脚本已启动")
        
        # 创建分析完成标记文件
        marker_dir = "AIGC/analysis_markers"
        os.makedirs(marker_dir, exist_ok=True)
        marker_file = os.path.join(marker_dir, "brand_analysis_complete.flag")
        
        try:
            with open(marker_file, "w") as f:
                f.write(f"completed_at:{datetime.now().isoformat()}\n")
            print(f"创建品牌分析完成标记: {marker_file}")
        except Exception as e:
            print(f"创建标记文件失败: {str(e)}")
            raise
            
    except Exception as e:
        print(f"爬虫脚本执行失败: {str(e)}")
        # 确保所有子进程都被终止
        for p in processes:
            if p.poll() is None:  # 检查进程是否仍在运行
                p.terminate()