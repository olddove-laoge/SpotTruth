from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pickle
import os

class TextContentScraper:
    def __init__(self, 
                 driver_path: str,
                 search_keyword: str,
                 user_data_dir: str = r"C:\taobao_bot_profile",
                 cookie_file: str = "taobao_cookies.pkl"):
        if not isinstance(search_keyword, str) or not search_keyword.strip():
            raise ValueError("必须提供有效的搜索关键词")
        self.search_keyword = search_keyword
                 
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
        print("1.访问 https://login.taobao.com")
        print("2.使用手机淘宝扫码完成登录")
        print("3.登录成功后保持页面不动")
        
        self.driver.get("https://login.taobao.com")
        input("完成登录后按回车继续...")
        
        if not self.check_login_status():
            raise RuntimeError("手动登录验证失败")
        
        with open(self.cookie_file, 'wb') as f:
            pickle.dump(self.driver.get_cookies(), f)
        print("登录凭证已存储")

    def load_cookies(self) -> bool:
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'rb') as f:
                    cookies = pickle.load(f)
                    self.driver.delete_all_cookies()
                    for cookie in cookies:
                        self.driver.add_cookie(cookie)
                self.driver.refresh()
                print("历史Cookie加载完成")
                return True
            except Exception as e:
                print(f"Cookie加载异常: {str(e)}")
                return False
        return False

    def ensure_login(self):
        if not self.check_login_status():
            print("检测到登录状态失效，尝试恢复...")
            if not self.load_cookies() or not self.check_login_status():
                self.manual_login()

    def get_target_url(self):
        """动态构建目标URL"""
        import urllib.parse
        encoded_keyword = urllib.parse.quote(self.search_keyword)
        return f"https://s.taobao.com/search?page=1&q={encoded_keyword}&spm=tbpc.item_error.top_search.search_in_taobao_manual&tab=all"

    def _payment_check(self, line: str) -> tuple:
        """检查付款金额是否符合条件"""
        if "付款" not in line:
            return None, False
            
        import re
        num_match = re.search(r'(\d+\.?\d*)[万]?', line)
        if not num_match:
            print(f"金额不足: {line[:30]}...")
            return None, False
            
        num = float(num_match.group(1))
        if '万' in line:
            num *= 10000
        return num, num >= 1000

    def _validate_element(self, element, line: str) -> dict:
        """验证元素并返回有效数据"""
        num, is_valid = self._payment_check(line)
        if not is_valid:
            return None
            
        href = element.get_attribute('href')
        if not href:
            return None
            
        return {
            'text': line,
            'href': href,
            'amount': num
        }

    def _process_element_text(self, element) -> dict:
        """处理单个元素的文本内容"""
        full_text = element.text.strip()
        if not full_text:
            return None

        return next(
            (result for line in full_text.split('\n') 
             if (result := self._validate_element(element, line.strip()))),
            None
        )

    def scrape_text_content(self, max_elements: int = 12):
        """爬取元素的文本内容"""
        try:
            self.ensure_login()
            target_url = self.get_target_url()
            self.driver.get(target_url)
            time.sleep(3)  # 等待页面加载
            
            # 预设的XPath路径 - 匹配评论内容元素
            xpath = "//*[starts-with(@id, 'item_id_')]"
            elements = self.driver.find_elements(By.XPATH, xpath)
            
            # 如果没有找到元素，尝试备用CSS选择器
            if not elements:
                css_selector = "div.comment-content"
                elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
            
            results = []
            for i, element in enumerate(elements[:max_elements]):
                try:
                    result = self._process_element_text(element)
                    if result:
                        results.append(result)
                        print(f"符合条件({result['amount']}): {result['text'][:30]}... [链接已记录]")
                    else:
                        print(f"第 {i+1} 个元素无符合条件的付款信息")
                except Exception as e:
                    print(f"获取第 {i+1} 个元素文本时出错: {str(e)}")
            
            return results[:3]  # 限制5条结果
        except Exception as e:
            print(f"爬取过程中出错: {str(e)}")
            return []

    def close(self):
        if self.driver:
            self.driver.quit()
            print("浏览器实例已关闭")



    def save_results_to_file(self, results: list, output_path: str) -> None:
        """将结果保存到指定文件
        
        Args:
            results: 要保存的结果列表
            output_path: 输出文件路径
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                for item in results:
                    if isinstance(item, dict):
                        f.write(f"{item['href']}\n")

                    else:
                        f.write(f"{item}\n")
                print(f"已保存 {len(results)} 条结果到 {output_path}")
        except IOError as e:
            print(f"保存文件时出错: {str(e)}")

if __name__ == "__main__":
    # 使用示例 - URL必须在程序内配置
    with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\simple_prod_name.txt', 'r', encoding='utf-8') as f:
        search_keyword = f.read().strip()

    with TextContentScraper(
        driver_path=r"AIGC\edgedriver\msedgedriver.exe",
        search_keyword=search_keyword
    ) as scraper:
        results = scraper.scrape_text_content()
        output_path = r"AIGC\Comparison_of_similar_products_and_external_link_information\rela_prods_links.txt"
        scraper.save_results_to_file(results, output_path)
