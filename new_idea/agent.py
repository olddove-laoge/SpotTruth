# agent.py
"""避雷真Agent - 商品口碑分析Agent"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

from mcp_test.kimi_client import KimiClient
from step6_mcp_tools import MCPToolServer


class Agent:
    """避雷真Agent"""
    
    def __init__(self):
        self.kimi = KimiClient()
        self.mcp_server = None
        self.driver = None
        self.running = False
        
    def welcome(self):
        """开场白"""
        print("\n" + "="*60)
        print("🤖 避雷真 - 商品口碑分析Agent")
        print("="*60)
        print("您好！我是避雷真，一个专业的商品口碑分析助手。")
        print("")
        print("我可以帮您：")
        print("  📊 分析淘宝商品的好评率/差评率")
        print("  🔍 识别虚假好评和阴阳怪气评价")
        print("  📝 提供购买建议")
        print("")
        print("使用方法：")
        print("  • 输入商品链接（如 https://item.taobao.com/...）")
        print("  • 输入品牌名+商品名（如 蓝月亮 洗衣液）")
        print("")
        print("输入 'quit' 或 '退出' 结束程序")
        print("="*60 + "\n")
    
    def recognize_intent(self, user_input: str) -> dict:
        """识别用户意图
        
        Returns:
            {
                "type": "link" | "brand_product" | "unknown",
                "data": {...}
            }
        """
        prompt = f"""请分析用户的输入，判断用户想要做什么。

用户输入："{user_input}"

请从以下选项中选择：
A. 用户输入了一个淘宝/天猫商品链接，想要分析这个商品
B. 用户输入了品牌名和商品名，想要搜索并分析这个商品
C. 用户只是在闲聊或提问，不确定想做什么
D. 用户想要对比多个品牌的商品（多品牌对比）

请只回答A、B、C或D，不要回答其他内容。"""
        
        response = self.kimi.chat([
            {"role": "user", "content": prompt}
        ])
        
        content = response.get("content", "").strip()
        print(f"   [意图识别]: {content}")
        
        # 解析意图
        if "A" in content or "链接" in user_input:
            # 提取链接
            import re
            urls = re.findall(r'https?://[^\s]+', user_input)
            return {"type": "link", "url": urls[0] if urls else ""}
        elif "B" in content or (" " in user_input and len(user_input.split()) >= 2):
            # 尝试提取品牌和商品
            return {"type": "brand_product", "raw_input": user_input}
        elif "D" in content or "对比" in user_input:
            return {"type": "multi_brand", "raw_input": user_input}
        else:
            return {"type": "unknown", "raw_input": user_input}
    
    def extract_brand_product(self, user_input: str) -> dict:
        """从用户输入提取品牌和商品"""
        prompt = f"""请从用户输入中提取品牌名和商品名。

用户输入："{user_input}"

请提取：
- 品牌名（如 蓝月亮、优形）
- 商品名（如 洗衣液、鸡胸肉）

请用JSON格式回答：
{{
    "brand": "品牌名",
    "product": "商品名"
}}

如果无法提取，请返回：
{{
    "brand": "",
    "product": ""
}}"""
        
        response = self.kimi.chat([
            {"role": "user", "content": prompt}
        ])
        
        content = response.get("content", "").strip()
        
        # 尝试解析JSON
        try:
            # 找到JSON部分
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "brand": data.get("brand", ""),
                    "product": data.get("product", "")
                }
        except:
            pass
        
        # 简单解析
        words = user_input.split()
        if len(words) >= 2:
            return {"brand": words[0], "product": words[1]}
        
        return {"brand": "", "product": ""}
    
    def handle_link(self, url: str, product_name: str = "") -> str:
        """处理链接输入"""
        print(f"\n📎 检测到商品链接: {url}")
        print("   正在获取评论...")
        
        # 直接用链接获取评论
        comments = self.mcp_server.get_comments(url=url, max_count=100, driver=self.driver)
        
        if not comments:
            return "抱歉，无法获取该商品的评论，请检查链接是否正确。"
        
        print(f"   获取到 {len(comments)} 条评论")
        
        # 分析评论
        return self.analyze_comments_with_extra(comments, product_name)
    
    def handle_brand_product(self, brand: str, product: str) -> str:
        """处理品牌+商品输入"""
        print(f"\n🔍 搜索商品: {brand} {product}")
        
        # 搜索商品
        products = self.mcp_server.search_product(
            brand=brand, 
            product=product, 
            max_results=1,
            driver=self.driver
        )
        
        if not products:
            return f"抱歉，未找到'{brand} {product}'相关的商品。"
        
        product_info = products[0]
        product_name = product_info.get("name", "")
        print(f"   找到商品: {product_name}")
        print(f"   店铺: {product_info['shop']}")
        
        # 获取评论
        print("   正在获取评论...")
        comments = self.mcp_server.get_comments(
            url=product_info['url'], 
            max_count=100,
            driver=self.driver
        )
        
        if not comments:
            return "抱歉，无法获取该商品的评论。"
        
        print(f"   获取到 {len(comments)} 条评论")
        
        # 分析评论（含小红书/黑猫询问）
        return self.analyze_comments_with_extra(comments, product_name)
    
    def analyze_comments_with_extra(self, comments: list, product_name: str = "") -> str:
        """分析评论（含小红书/黑猫询问）"""
        
        # 1. 先进行淘宝评论分析
        taobao_result = self._do_taobao_analysis(comments, product_name)
        
        # 提取品牌名（用于小红书和黑猫搜索）
        brand = self._extract_brand(product_name)
        
        # 2. 询问是否需要小红书
        need_xiaohongshu = self._ask_need_extra("小红书")
        xiaohongshu_result = None
        if need_xiaohongshu:
            print("   🔍 正在调用小红书爬虫...")
            keyword = brand if brand else product_name
            notes = self.mcp_server.search_xiaohongshu(keyword=keyword, max_notes=10, driver=self.driver)
            if notes:
                print("   📝 正在分析小红书内容...")
                xiaohongshu_result = self._analyze_xiaohongshu(notes)
            else:
                xiaohongshu_result = "未找到相关笔记"
        
        # 3. 询问是否需要黑猫投诉
        need_heimao = self._ask_need_extra("黑猫投诉")
        heimao_result = None
        if need_heimao:
            print("   🔍 正在调用黑猫投诉爬虫...")
            complaints = self.mcp_server.search_heimao(brand=brand, max_complaints=10, driver=self.driver)
            if complaints:
                print("   📝 正在分析黑猫投诉内容...")
                heimao_result = self._analyze_heimao(complaints)
            else:
                heimao_result = "未找到相关投诉"
        
        # 4. 生成最终报告
        print("   📊 正在生成最终报告...")
        return self._generate_report(
            taobao_result, 
            xiaohongshu_result or "用户未选择查看", 
            heimao_result or "用户未选择查看", 
            product_name
        )
    
    def _extract_brand(self, product_name: str) -> str:
        """从商品名称提取品牌名"""
        if not product_name:
            return ""
        
        prompt = f"""从以下商品名称中提取品牌名。

商品名称：{product_name}

只输出品牌名，不要输出其他内容。如果无法识别，输出空字符串。"""
        
        response = self.kimi.chat([{"role": "user", "content": prompt}])
        brand = response.get("content", "").strip()
        
        # 清理品牌名
        brand = brand.replace("品牌：", "").replace("品牌名：", "").strip()
        
        return brand
    
    def _ask_need_extra(self, target: str) -> bool:
        """询问是否需要额外信息"""
        print(f"\n❓ 是否需要参考{target}信息？")
        print(f"   {target}可以提供更多维度的参考")
        print("   请回复：是/要/需要   或者   否/不要/跳过")
        
        user_input = input(f"   您的回复: ").strip()
        
        # Kimi判断
        prompt = f"""请判断用户是否想查看{target}信息。
用户回复："{user_input}"
请只回答"是"或"否"。"""
        
        response = self.kimi.chat([{"role": "user", "content": prompt}])
        content = response.get("content", "")
        
        return "是" in content
    
    def _analyze_xiaohongshu(self, notes: list) -> str:
        """分析小红书笔记"""
        note_texts = [n.get("text", "") for n in notes[:10]]
        
        prompt = f"""分析以下小红书笔记：
{chr(10).join([f"笔记{i+1}: {text[:150]}..." for i, text in enumerate(note_texts)])}

输出JSON：
{{"总体评价": "正面/负面/中性", "避坑建议": [], "总结": "..."}}"""
        
        response = self.kimi.chat([{"role": "user", "content": prompt}])
        return response.get("content", "")
    
    def _analyze_heimao(self, complaints: list) -> str:
        """分析黑猫投诉"""
        complaint_texts = [c.get("text", "") for c in complaints]
        
        prompt = f"""分析以下黑猫投诉：
{chr(10).join([f"{i+1}. {text}" for i, text in enumerate(complaint_texts)])}

输出JSON：
{{"投诉数量": {len(complaints)}, "主要问题": [], "总结": "..."}}"""
        
        response = self.kimi.chat([{"role": "user", "content": prompt}])
        return response.get("content", "")
    
    def _generate_report(self, taobao_result: dict, xiaohongshu_result: str, heimao_result: str, product_name: str) -> str:
        """生成最终报告"""
        prompt = f"""根据以下分析结果，生成最终报告。

商品名称：{product_name}

=== 淘宝评论分析 ===
好评率：{taobao_result.get('好评率', 'N/A')}
差评率：{taobao_result.get('差评率', 'N/A')}
总结：{taobao_result.get('总结', '')}

=== 小红书分析 ===
{xiaohongshu_result if xiaohongshu_result else "用户未选择查看"}

=== 黑猫投诉分析 ===
{heimao_result if heimao_result else "用户未选择查看"}

请给出JSON格式的最终报告：
{{
    "总结": "...",
    "购买建议": "建议购买/不建议购买/观望"
}}"""
        
        response = self.kimi.chat([{"role": "user", "content": prompt}])
        return response.get("content", "")
    
    def _do_taobao_analysis(self, comments: list, product_name: str = "") -> dict:
        """执行淘宝评论分析"""
        print("\n" + "="*60)
        print("📊 开始分析淘宝评论...")
        print("="*60)
        
        if not product_name:
            product_name = "商品"
        
        print("   🔍 正在判断商品品类...")
        category = self.mcp_server.classify_category(product_name)
        print(f"   商品品类: {category}")
        
        # 反讽检测
        comment_texts = [c.get("text", "") for c in comments]
        topics = [product_name] * len(comment_texts)
        
        print("   🤖 正在调用反讽检测模型...")
        sarcasm_results = self.mcp_server.detect_sarcasm(comment_texts, topics)
        
        sarcastic_comments = []
        normal_comments = []
        
        for i, result in enumerate(sarcasm_results):
            if result.get("is_sarcastic", False):
                sarcastic_comments.append({"text": comment_texts[i], "topic": product_name})
            else:
                normal_comments.append(comment_texts[i])
        
        print(f"   反讽评论: {len(sarcastic_comments)} 条")
        
        # 反讽评论 → Kimi判断
        sarcastic_positive = 0
        sarcastic_negative = 0
        
        if sarcastic_comments:
            print("   🤖 正在调用Kimi判断反讽评论真实情感...")
            for sc in sarcastic_comments:
                result = self.mcp_server.llm_judge_sarcasm(sc["text"], sc["topic"])
                if result.get("sentiment") == "positive":
                    sarcastic_positive += 1
                else:
                    sarcastic_negative += 1
        
        # 正常评论 → LoRA
        normal_positive = 0
        normal_negative = 0
        
        if normal_comments:
            print("   🤖 正在调用LoRA情感分析模型...")
            for i in range(0, len(normal_comments), 50):
                batch = normal_comments[i:i+50]
                results = self.mcp_server.sentiment_analysis(batch, category)
                for r in results:
                    if r.get("sentiment") == "positive":
                        normal_positive += 1
                    else:
                        normal_negative += 1
        
        total_positive = sarcastic_positive + normal_positive
        total_negative = sarcastic_negative + normal_negative
        total = total_positive + total_negative
        
        好评率 = round(total_positive / total * 100, 1) if total > 0 else 0
        差评率 = round(total_negative / total * 100, 1) if total > 0 else 0
        
        print(f"\n   ✅ 好评率: {好评率}%")
        print(f"   ❌ 差评率: {差评率}%")
        
        return {
            "好评率": f"{好评率}%",
            "差评率": f"{差评率}%",
            "总结": f"好评率{好评率}%，差评率{差评率}%"
        }
    
    def ask_continue(self) -> bool:
        """询问是否继续"""
        print("\n" + "-"*40)
        response = input("   是否继续分析其他商品？(是/否): ").strip()
        
        # Kimi判断
        prompt = f"""用户回复："{response}"
        
请判断用户是否想继续分析商品。
回答"是"或"否"。"""
        
        kimi_response = self.kimi.chat([{"role": "user", "content": prompt}])
        content = kimi_response.get("content", "")
        
        return "是" in content
    
    def run(self):
        """运行Agent"""
        self.welcome()
        self.running = True
        
        while self.running:
            try:
                user_input = input("\n👤 您: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["quit", "退出", "q", "exit"]:
                    print("\n👋 再见！感谢使用避雷真！\n")
                    break
                
                # 意图识别
                intent = self.recognize_intent(user_input)
                
                if intent["type"] == "link":
                    result = self.handle_link(intent["url"])
                    print(f"\n🤖 避雷真: {result}")
                    
                elif intent["type"] == "brand_product":
                    # 提取品牌和商品
                    bp = self.extract_brand_product(intent.get("raw_input", user_input))
                    if not bp["brand"] or not bp["product"]:
                        print("   抱歉，未能识别出品牌和商品，请重新输入（如：蓝月亮 洗衣液）")
                        continue
                    
                    result = self.handle_brand_product(bp["brand"], bp["product"])
                    print(f"\n🤖 避雷真: {result}")
                    
                elif intent["type"] == "multi_brand":
                    print("\n🤖 避雷真: 多品牌对比功能暂未开放，敬请期待！")
                    
                else:
                    # 普通对话 - 以避雷真的身份回答
                    print("\n🤖 避雷真: ", end="")
                    system_prompt = """你是"避雷真"，一个专业的商品口碑分析助手。

你的主要功能是：
1. 分析淘宝商品的好评率/差评率
2. 识别虚假好评和阴阳怪气评价（反讽检测）
3. 提供购买建议

如果用户问的不是商品分析相关的问题，你可以简单回答并引导用户使用商品分析功能。
例如：如果用户问你有什么功能，你应该回答避雷真的功能，而不是其他AI的功能。"""
                    
                    response = self.kimi.chat([
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input}
                    ])
                    print(response.get("content", "抱歉，我没理解您的意思。"))
            
            except KeyboardInterrupt:
                print("\n\n👋 再见！\n")
                break
            except Exception as e:
                print(f"\n❌ 出错: {e}")
                import traceback
                traceback.print_exc()


def main():
    # 初始化浏览器
    driver_path = r"E:\edgedriver_win64\msedgedriver.exe"
    profile_dir = r"C:\unified_bot_profile"
    
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)
    
    options = Options()
    options.use_chromium = True
    options.add_argument(f"user-data-dir={profile_dir}")
    
    print("正在启动浏览器...")
    driver = webdriver.Edge(service=Service(driver_path), options=options)
    
    try:
        # 登录淘宝
        print("\n[1/3] 打开淘宝，请登录...")
        driver.get("https://www.taobao.com")
        input("  登录完成后，按回车继续...")
        
        # 登录小红书（可选）
        print("\n[2/3] 打开小红书，请登录...")
        driver.get("https://www.xiaohongshu.com")
        input("  登录完成后，按回车继续...")
        
        # 登录黑猫投诉（可选）
        print("\n[3/3] 打开黑猫投诉，请登录...")
        driver.get("https://tousu.sina.com.cn")
        input("  登录完成后，按回车继续...")
        
        # 初始化MCP
        print("\n初始化Agent...")
        agent = Agent()
        agent.driver = driver
        agent.mcp_server = MCPToolServer()
        
        # 运行
        agent.run()
        
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
