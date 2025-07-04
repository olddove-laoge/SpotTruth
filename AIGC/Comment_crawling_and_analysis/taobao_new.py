from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pickle
import os
import time
import random
class TaobaoScraperNew:
    def _process_comment(self, comment, processed: set) -> tuple:
        """处理单个评论元素，返回(内容, 是否新增)"""
        try:
            content = comment.find_element(By.XPATH, ".//*[contains(@class, 'content')]").text.strip()
            
            # 仅过滤空内容，保留所有评价（包括默认评价）
            if not content.strip():
                return None, False
                
            # 完全基于评论内容去重
            content_hash = hash(content.strip().lower())
            if content_hash in processed:
                return None, False
                
            processed.add(content_hash)
            return content, True
            
        except Exception as e:
            print(f" 处理评论时出错: {str(e)}")
            return None, False

    def _collect_comments(self, processed: set, max_comments: int) -> tuple:
        """收集当前页面评论，返回(新增评论列表, 是否收集足够)"""
        current_comments = self.driver.find_elements(By.XPATH, "//*[contains(@class, '0b4e753')]")
        new_comments = []
        
        for comment in current_comments:
            content, is_new = self._process_comment(comment, processed)
            if is_new:
                new_comments.append(content)
                if len(processed) >= max_comments:
                    return new_comments, True
                    
        return new_comments, False
    def __init__(self, 
                 driver_path: str,
                 user_data_dir: str = r"C:\taobao_bot_profile",
                 cookie_file: str = "taobao_cookies.pkl"):
        self.driver = None
        self.driver_path = driver_path
        self.user_data_dir = user_data_dir
        self.cookie_file = cookie_file

    def __enter__(self):
        self.initialize_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def initialize_driver(self):
        options = webdriver.EdgeOptions()
        options.use_chromium = True
        
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)
        options.add_argument(f"user-data-dir={self.user_data_dir}")
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        self.driver = webdriver.Edge(
            service=Service(self.driver_path),
            options=options
        )

    def check_login_status(self) -> bool:
        try:
            self.driver.get("https://www.taobao.com")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.LINK_TEXT, "我的淘宝"))
            )
            return True
        except Exception as e:
            print(f" 登录状态检查失败: {str(e)}")
            return False

    def manual_login(self):
        print("请按以下步骤操作：")
        print("1. 访问 https://login.taobao.com")
        print("2.使用手机淘宝扫码完成登录")
        print("3登录成功后保持页面不动")
        
        self.driver.get("https://login.taobao.com")
        input(" 完成登录后按回车继续...")
        
        if not self.check_login_status():
            raise RuntimeError(" 手动登录验证失败")
        
        with open(self.cookie_file, 'wb') as f:
            pickle.dump(self.driver.get_cookies(), f)
        print(" 登录凭证已存储")

    def load_cookies(self) -> bool:
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'rb') as f:
                    cookies = pickle.load(f)
                    self.driver.delete_all_cookies()
                    for cookie in cookies:
                        self.driver.add_cookie(cookie)
                self.driver.refresh()
                print(" 历史Cookie加载完成")
                return True
            except Exception as e:
                print(f" Cookie加载异常: {str(e)}")
                return False
        return False

    def ensure_login(self):
        if not self.check_login_status():
            print(" 检测到登录状态失效，尝试恢复...")
            if not self.load_cookies() or not self.check_login_status():
                self.manual_login()

    def smart_scroll(self) -> bool:
        scroll_container = self.driver.execute_script("""
            return document.querySelector("body > div[class*='7efaeec'] > div[class*='e320bf32'] > div > div[class*='00182ac']") 
            || document.documentElement
        """)
        
        try:
            pre_count = len(self.driver.find_elements(By.XPATH, "//*[contains(@class, '0b4e753')]"))
            
            self.driver.execute_script("""
                arguments[0].scrollTop += arguments[0].clientHeight * 20;
            """, scroll_container)
            
            time.sleep(random.uniform(0.1, 0.3))  
            
            post_count = len(self.driver.find_elements(By.XPATH, "//*[contains(@class, '0b4e753')]"))
            print(f" 滚动检测: {pre_count} → {post_count} 条评论")
            return post_count > pre_count
        except Exception as e:
            print(f" 滚动异常: {str(e)}")
            return False

    def scrape_reviews(self, 
                     output_file: str, 
                     max_comments: int = 1000,
                     manual_input: bool = True,
                     preset_url: str = ""):
        """爬取商品评论
        
        Args:
            output_file: 输出文件路径
            max_comments: 最大评论数
            manual_input: 是否手动输入链接
            preset_url: 预设商品链接
        """
        if manual_input:
            product_url = input(" 请输入商品详情页链接: ").strip()
        else:
            if not preset_url:
                raise ValueError("预设链接不能为空")
            product_url = preset_url
            print(f" 使用预设链接: {product_url}")
            
        self.driver.get(product_url)
        time.sleep(2)
        
        # 获取商品名称并保存
        try:
            product_name = self.driver.execute_script(
                "return document.querySelector('#tbpc-detail-item-title > h1')?.textContent?.trim()"
            )
            if product_name:
                # 确保输出目录存在
                output_dir = os.path.dirname(output_file)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                # 在评论文件同目录下保存商品名称
                product_name_file = os.path.join(output_dir, 'product_name.txt')
                
                try:
                    with open(product_name_file, 'w', encoding='utf-8') as f:
                        f.write(product_name)
                    print(f" 商品名称已保存到: {product_name_file}")
                    
                    # 异步调用分析脚本
                    import subprocess
                    try:
                        # 调用品牌+名称分析脚本
                        brand_script = r"AIGC\Comparison_of_similar_products_and_external_link_information\AIs\prod_brand&name_analysis.py"
                        subprocess.Popen(["python", brand_script])
                        
                        # 调用纯名称分析脚本
                        name_script = r"AIGC\Comparison_of_similar_products_and_external_link_information\AIs\prod_name_analysis.py"
                        subprocess.Popen(["python", name_script])
                        
                        print("分析脚本已异" \
                        "步启动")
                        subprocess.run(["python", name_script], check=True)
                        
                        print(" 已完成商品名称分析")
                    except subprocess.CalledProcessError as e:
                        print(f" 分析脚本执行失败: {str(e)}")
        
                    
                except Exception as e:
                    print(f"保存商品名称失败: {str(e)}")
            else:
                print("未找到商品名称元素")
        except Exception as e:
            print(f"获取商品名称时出错: {str(e)}")


        try:
            review_btn = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(@class, '15e2446')]"))
            )
            self.driver.execute_script("arguments[0].click();", review_btn)
            time.sleep(1.5)
        except Exception as e:
            raise RuntimeError(f"[错误] 无法打开评价页面: {str(e)}")
        
        processed = set()
        retry_count = 0
        max_retries = 5
        collected_enough = False

        with open(output_file, 'w', encoding='utf-8') as f:
            while retry_count < max_retries and not collected_enough:
                new_comments, collected_enough = self._collect_comments(processed, max_comments)
                new_added = len(new_comments)
                
                if new_comments:
                    f.write('\n'.join(new_comments) + '\n')
                    print(f"[成功] 新增 {new_added} 条评论 [{len(processed)}/{max_comments}]")
                    
                if collected_enough:
                    print(f"[完成] 成功收集 {max_comments} 条不重复有效评论")
                    break
                
                if new_added < 5:
                    retry_count += 1
                else:
                    retry_count = 0
                
                if not self.smart_scroll():
                    retry_count += 1
                
                delay = 0.2 if new_added > 0 else 0.5
                time.sleep(delay)
                
                if retry_count >= max_retries:
                    print("[警告] 已达到最大重试次数，停止收集")
                    break

    def remove_default_reviews(self, file_path: str):
        """删除文件中的默认评价"""
        default_reviews = [
            "此用户没有填写评价。",
            "评价方未及时做出评价,系统默认好评!",
            "更多"
            
        ]
        
        # 创建临时文件
        temp_file = file_path + '.tmp'
        
        try:
            # 读取并过滤
            with open(file_path, 'r', encoding='utf-8') as infile, \
                 open(temp_file, 'w', encoding='utf-8') as outfile:
                
                removed_count = 0
                for line in infile:
                    line = line.strip()
                    if line not in default_reviews:
                        outfile.write(line + '\n')
                    else:
                        removed_count += 1
                
                print(f"[清理] 已删除 {removed_count} 条默认评价")
            
            # 替换原文件
            os.replace(temp_file, file_path)
            
        except Exception as e:
            print(f"[错误] 处理文件出错: {str(e)}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def close(self):
        if self.driver:
            self.driver.quit()
            print("[系统] 浏览器实例已关闭")
            if os.path.exists(self.cookie_file):
                os.remove(self.cookie_file)
                print("[清理] 临时Cookie文件已清理")

if __name__ == "__main__":
    import argparse
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='taobao_scraper.log'
    )
    
    parser = argparse.ArgumentParser(description='淘宝商品评论爬取工具')
    parser.add_argument('--manual_input', type=lambda x: x.lower() == 'true', 
                       default=True, help='是否手动输入链接')
    parser.add_argument('--preset_url', type=str, 
                       default="", help='预设商品链接')
    
    args = parser.parse_args()
    
    # 验证驱动路径
    driver_path = r"AIGC\edgedriver\msedgedriver.exe"
    if not os.path.exists(driver_path):
        logging.error(f"Edge驱动路径不存在: {driver_path}")
        raise FileNotFoundError(f"Edge驱动路径不存在: {driver_path}")
    
    logging.info(f"启动爬虫，参数: manual_input={args.manual_input}, preset_url={args.preset_url}")
    
    output_file = r'AIGC\Comment_crawling_and_analysis\reviews.txt'
    with TaobaoScraperNew(
        driver_path=r"AIGC\edgedriver\msedgedriver.exe"
    ) as scraper:
        scraper.ensure_login()
        scraper.scrape_reviews(
            output_file=output_file,
            max_comments=200,
            manual_input=args.manual_input,
            preset_url=args.preset_url
        )
        # 爬取完成后自动删除默认评价
        scraper.remove_default_reviews(output_file)
        
