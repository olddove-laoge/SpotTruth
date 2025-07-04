import os
import sys
import threading
import time
import pickle
import random
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from taobao_new import TaobaoScraperNew

class MultiPageScraper:
    def __init__(self, driver_path, max_threads=3):
        self.driver_path = driver_path
        self.max_threads = max_threads
        self.semaphore = threading.Semaphore(max_threads)
        self.cookies = None
        self.cookie_file = "taobao_shared_cookies.pkl"
        self.scroll_lock = threading.Lock()
        self.last_scroll_time = 0
        
    def initialize_login(self):
        """主线程统一处理登录"""
        print("主线程正在初始化登录状态...")
        with TaobaoScraperNew(driver_path=self.driver_path) as scraper:
            scraper.ensure_login()
            self.cookies = scraper.driver.get_cookies()
            with open(self.cookie_file, 'wb') as f:
                pickle.dump(self.cookies, f)
        print("登录状态已初始化并保存")
        
    def smart_scroll(self, driver):
        """智能轮流滚动"""
        with self.scroll_lock:
            # 控制滚动间隔至少3秒
            current_time = time.time()
            if current_time - self.last_scroll_time < 1:
                time.sleep(1 - (current_time - self.last_scroll_time))
            
            try:
                scroll_container = driver.execute_script("""
                    return document.querySelector("body > div[class*='7efaeec'] > div[class*='e320bf32'] > div > div[class*='00182ac']") 
                    || document.documentElement
                """)
                
                driver.execute_script("""
                    arguments[0].scrollTop += arguments[0].clientHeight * 15;
                """, scroll_container)
                
                self.last_scroll_time = time.time()
                time.sleep(random.uniform(1.0, 2.5))  # 随机延迟
                return True
            except Exception as e:
                print(f"滚动异常: {str(e)}")
                return False

    def process_comment(self, comment, processed, f):
        """处理单个评论"""
        try:
            content = comment.find_element(By.XPATH, ".//*[contains(@class, 'content')]").text.strip()
            if not content.strip():
                return False
                
            content_hash = hash(content.strip().lower())
            if content_hash not in processed:
                f.write(content + '\n')
                processed.add(content_hash)
                print(f"新增评论 [{len(processed)}/200]: {content[:30]}...")
                return True
        except Exception as e:
            print(f"处理评论时出错: {str(e)}")
        return False

    def collect_comments(self, scraper, output_txt, max_comments=200):
        """收集评论到文件"""
        processed = set()
        retry_count = 0
        max_retries = 5
        
        with open(output_txt, 'w', encoding='utf-8') as f:
            while retry_count < max_retries and len(processed) < max_comments:
                current_comments = scraper.driver.find_elements(By.XPATH, "//*[contains(@class, '0b4e753')]")
                new_added = sum(self.process_comment(c, processed, f) for c in current_comments)
                
                if len(processed) >= max_comments:
                    print(f"成功收集 {max_comments} 条不重复有效评论，任务完成")
                    break
                    
                retry_count = 0 if new_added >= 5 else retry_count + 1
                if not self.smart_scroll(scraper.driver):
                    retry_count += 1
                
                time.sleep(0.5 if new_added > 0 else 1.0)
        
        return len(processed) >= max_comments

    def setup_directories(self, product_id, output_dir, index):
        """设置输出目录结构"""
        comment_dir = os.path.abspath(os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "Comparison_of_similar_products_and_external_link_information",
            "relative_product_comments"
        ))
        os.makedirs(comment_dir, exist_ok=True)
        return (
            os.path.join(comment_dir, f"prod{index+1}_comment.txt"),
            os.path.join(output_dir, f"profile_{index}")
        )

    def scrape_single_product(self, product_url, output_dir, index):
        """单个商品爬取任务"""
        with self.semaphore:
            product_id = self.get_product_id(product_url)
            output_txt, profile_dir = self.setup_directories(product_id, output_dir, index)
            print(f"开始爬取 {product_url} (线程 {threading.current_thread().name})")
            
            try:
                with TaobaoScraperNew(driver_path=self.driver_path, user_data_dir=profile_dir) as scraper:
                    if self.cookies:
                        scraper.driver.get("https://www.taobao.com")
                        scraper.driver.delete_all_cookies()
                        for cookie in self.cookies:
                            scraper.driver.add_cookie(cookie)
                        scraper.driver.refresh()
                    
                    scraper.driver.get(product_url)
                    time.sleep(2)
                    
                    review_btn = WebDriverWait(scraper.driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[contains(@class, '15e2446')]"))
                    )
                    scraper.driver.execute_script("arguments[0].click();", review_btn)
                    time.sleep(1.5)
                    
                    if self.collect_comments(scraper, output_txt):
                        scraper.remove_default_reviews(output_txt)
                        print(f"完成爬取 {product_url}")
                        return output_txt
                    return None
                    
            except Exception as e:
                print(f"爬取 {product_url} 失败: {str(e)}")
                return None

    def get_product_id(self, url):
        """从URL中提取商品ID"""
        try:
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            return params.get('id', ['unknown'])[0][:20]  # 限制ID长度
        except:
            return "unknown"

def read_product_links():
    """从sim_prods.txt读取商品链接"""
    sim_prods_path = os.path.abspath(os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "Comparison_of_similar_products_and_external_link_information",
        "rela_prods_links.txt"
    ))
   
    try:
        with open(sim_prods_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
            
        if not urls:
            print("sim_prods.txt中没有有效的商品链接")
            sys.exit(1)
            
        print(f"\n从sim_prods.txt读取到{len(urls)}个商品链接")
        return urls
    except Exception as e:
        print(f"读取sim_prods.txt失败: {str(e)}")
        sys.exit(1)

def create_and_run_threads(scraper, urls, output_dir):
    """创建并运行爬取线程"""
    threads = []
    output_files = []
    
    print(f"\n启动 {len(urls)} 个爬取线程(最多同时{scraper.max_threads}个)...")
    
    for i, url in enumerate(urls):
        t = threading.Thread(
            target=lambda u, idx: output_files.append(
                scraper.scrape_single_product(u, output_dir, idx)
            ),
            args=(url, i),
            name=f"Scraper-{i}"
        )
        t.start()
        threads.append(t)
        time.sleep(0.5)
    
    return threads, output_files

def wait_for_threads(threads):
    """等待所有线程完成"""
    for t in threads:
        t.join()
        print(f"  线程 {t.name} 已完成")

def setup_environment():
    """设置工作环境和目录"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    output_dir = os.path.join(base_dir, "相关商品评论")
    os.makedirs(output_dir, exist_ok=True)
    
    comment_dir = os.path.abspath(os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "Comparison_of_similar_products_and_external_link_information",
        "relative_product_comments"
    ))
    os.makedirs(comment_dir, exist_ok=True)
    
    return output_dir, comment_dir

def main():
    try:
        output_dir, comment_dir = setup_environment()
        # 使用绝对路径定位驱动文件
        driver_path = os.path.abspath(os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "edgedriver",
            "msedgedriver.exe"
        ))
        
        # 验证驱动路径
        if not os.path.exists(driver_path):
            raise FileNotFoundError(f"Edge驱动文件不存在: {driver_path}")
        if not os.access(driver_path, os.X_OK):
            raise PermissionError(f"Edge驱动文件没有执行权限: {driver_path}")
            
        print(f"[DEBUG] 使用Edge驱动路径: {driver_path}")
        scraper = MultiPageScraper(driver_path, max_threads=3)
        
        scraper.initialize_login()
        urls = read_product_links()
        
        threads, output_files = create_and_run_threads(scraper, urls, output_dir)
        wait_for_threads(threads)
        
        print("\n所有商品评论已爬取完成")
        print(f"每个商品的评论已单独保存在: {comment_dir}")
        
    except Exception as e:
        print(f"\n处理失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
