from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pickle
import os
import time
import random
from datetime import datetime
class XiaohongshuScraper:
    def _get_valid_href(self, item) -> str:
        """获取有效的href属性"""
        try:
            href = item.get_attribute("href")
            if href and href.startswith("https://www.xiaohongshu.com/search_result/"):
                return href
        except Exception as e:
            print(f" 处理链接时出错: {str(e)}")
        return ""

    def _process_item(self, item, processed: set) -> tuple:
        """处理单个链接元素，返回(链接, 是否新增)"""
        href = self._get_valid_href(item)
        if not href:
            return None, False
            
        href_hash = hash(href.strip().lower())
        if href_hash in processed:
            return None, False
            
        processed.add(href_hash)
        return href, True



    def _collect_items(self, processed: set, max_items: int) -> tuple:
        """收集当前页面链接，返回(新增链接列表, 是否收集足够)"""
        current_items = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")
        new_items = []
        collected_enough = False
        
        for item in current_items:
            content, is_new = self._process_item(item, processed)
            if not is_new:
                continue
                
            new_items.append(content)
            if len(processed) >= max_items:
                collected_enough = True
                break
                
        return new_items, collected_enough

    def __init__(self, 
                 driver_path: str,
                 user_data_dir: str = r"C:\xiaohongshu_bot_profile",
                 cookie_file: str = "xiaohongshu_cookies.pkl"):
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
            self.driver.get("https://www.xiaohongshu.com")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '我')]"))
            )
            return True
        except Exception as e:
            print(f"登录状态检查失败: {str(e)}")
            return False

    def manual_login(self):
        print("请按以下步骤操作：")
        print("1.访问 https://www.xiaohongshu.com")
        print("2.使用手机小红书扫码完成登录")
        print("3.登录成功后保持页面不动")
        
        self.driver.get("https://www.xiaohongshu.com")
        input(" 完成登录后按回车继续...")
        
        if not self.check_login_status():
            raise RuntimeError(" 手动登录验证失败")
        
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

    def smart_scroll(self):
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(0.5, 1.5))
            return True
        except Exception as e:
            print(f"滚动异常: {str(e)}")
            return False

    def _extract_single_desc(self, index: int) -> str:
        """提取单个描述元素内容"""
        selector = f"#detail-desc > span > span:nth-child({index})"
        try:
            element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element.text
        except:
            return None

    def _extract_desc_content(self, url: str) -> list:
        """提取详情页描述内容"""
        self.driver.get(url)
        time.sleep(2)
        
        contents = []
        index = 1
        while True:
            content = self._extract_single_desc(index)
            if not content:
                break
            contents.append(content)
            index += 1
                
        return contents

    def scrape_search_results(self, 
                            keyword: str,
                            output_file: str, 
                            max_items: int = 30):
        """爬取小红书搜索结果及详情页内容
        
        Args:
            keyword: 搜索关键词
            output_file: 输出文件路径
            max_items: 最大内容数量
        """
        search_url = f"https://www.xiaohongshu.com/search_result/?keyword={keyword}&source=web_search_result_notes&type=51"
        self.driver.get(search_url)
        time.sleep(2)

        # 检查安全提示元素
        try:
            security_element = self.driver.find_element(
                By.CSS_SELECTOR,
                "#global > div.main-container > div.with-side-bar.main-content > div > div > div.search-layout__middle > div.securityOnebox > div > div.desc"
            )
            desc_file = output_file.replace('.txt', '_desc.txt')
            with open(desc_file, 'w', encoding='utf-8') as f:
                f.write(security_element.text)
            # 清空原始文件
            with open(output_file, 'w', encoding='utf-8') as f:
                pass
            print("检测到安全提示，已保存提示内容到_desc.txt并清空原始文件")
            return
        except:
            pass  # 没有安全提示，继续正常流程
        
        processed = set()
        retry_count = 0
        max_retries = 5
        collected_enough = False
        collected_urls = []

        # 第一阶段：收集搜索结果链接
        with open(output_file, 'w', encoding='utf-8') as f:
            while retry_count < max_retries and not collected_enough:
                new_items, collected_enough = self._collect_items(processed, max_items)
                new_added = len(new_items)
                
                if new_items:
                    collected_urls.extend(new_items)
                    f.write('\n'.join(new_items) + '\n')
                    print(f"新增 {new_added} 条内容 [{len(processed)}/{max_items}]")
                    
                if collected_enough:
                    print(f"成功收集 {max_items} 条不重复有效内容")
                    break
                
                if new_added < 5:
                    retry_count += 1
                    print(f"新增内容不足，尝试滚动加载 ({retry_count}/{max_retries})")
                
                if not self.smart_scroll():
                    retry_count += 1
                    print(f"滚动未加载新内容 ({retry_count}/{max_retries})")
                
                time.sleep(random.uniform(1, 2))

        # 第二阶段：爬取每个详情页内容
        if collected_urls:
            print("\n开始爬取详情页内容...")
            desc_file = output_file.replace('.txt', '_desc.txt')
            with open(desc_file, 'w', encoding='utf-8') as f:
                for url in collected_urls:
                    try:
                        contents = self._extract_desc_content(url)
                        if contents:
                            f.write(f"URL: {url}\n")
                            f.write("内容:\n")
                            f.write('\n'.join(contents) + '\n\n')
                            print(f"已爬取: {url}")
                        else:
                            print(f"未找到内容: {url}")
                    except Exception as e:
                        print(f"爬取失败 {url}: {str(e)}")

    def close(self):
        if self.driver:
            self.driver.quit()
            print("浏览器实例已关闭")
            if os.path.exists(self.cookie_file):
                print("Cookie文件已保留")

    

if __name__ == "__main__":
    with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\simple_prod_name_with_brand.txt', 'r', encoding='utf-8') as f:
        keyword = f.read().strip()
    with XiaohongshuScraper(
        driver_path=r"AIGC\edgedriver\msedgedriver.exe"
    ) as scraper:
        scraper.ensure_login()
        output_file =  r'AIGC\Comparison_of_similar_products_and_external_link_information\xhs_search_results.txt'
        keyword = keyword + " 避雷"
        scraper.scrape_search_results(
            keyword=keyword,
            output_file=output_file,
            max_items=5
        )
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
