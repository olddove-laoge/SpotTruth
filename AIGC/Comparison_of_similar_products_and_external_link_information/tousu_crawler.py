from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class TousuCrawler:
    def __init__(self, keyword=None, max_items=1000):
        """初始化爬虫
        
        Args:
            keyword (str, optional): 搜索关键词. Defaults to None.
            max_items (int, optional): 最大收集数量. Defaults to 1000.
        """
        with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\simple_prod_name_with_brand.txt', 'r', encoding='utf-8') as f:
            self.keyword = f.read().strip()

        self.max_items = max_items
        self.driver = self._init_driver()
        
    def _init_driver(self):
        """初始化浏览器驱动"""
        from selenium.webdriver.edge.service import Service as EdgeService
        edge_options = webdriver.EdgeOptions()
        edge_options.add_argument("user-data-dir=C:\\Temp\\EdgeProfile")
        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        edge_service = EdgeService(r"AIGC\edgedriver\msedgedriver.exe")
        return webdriver.Edge(service=edge_service, options=edge_options)
    
    def check_login_status(self):
        """检查用户登录状态"""
        try:
            login_element = self.driver.find_element(
                By.CSS_SELECTOR, 
                "#SI_User > div.ac-login.ac-logined > ul > li:nth-child(1) > a"
            )
            return True
        except:
            return False
    
    def collect_complaints(self):
        """收集投诉内容"""
        collected_items = set()
        last_count = 0
        no_new_count = 0
        
        while len(collected_items) < self.max_items and no_new_count < 3:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            complaints = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "#search_tab > div.blackcat-container > div.tab-con.tousu-list > div > a > h1"
            )
            
            current_count = len(collected_items)
            for complaint in complaints:
                if complaint.text not in collected_items:
                    collected_items.add(complaint.text)
            
            if len(collected_items) == current_count:
                no_new_count += 1
            else:
                no_new_count = 0
        
        return list(collected_items)
    
    def run(self):
        """运行爬虫"""
        self.driver.get("https://tousu.sina.com.cn/")
        
        # 提示用户确保已登录

        
        # 获取搜索关键词
        if self.keyword is None:
            self.keyword = input("请输入要搜索的关键词: ")
        
        search_url = f"https://tousu.sina.com.cn/index/search/?keywords={self.keyword}&t=1"
        self.driver.get(search_url)
        
        # 收集投诉内容
        complaints = self.collect_complaints()
        
        # 保存结果
        with open(r"AIGC\Comparison_of_similar_products_and_external_link_information\tousu.txt", "w", encoding="utf-8") as f:
            for item in complaints:
                f.write(item + "\n")
        
        print(f"成功收集到{len(complaints)}条投诉信息，已保存到tousu.txt")
        self.driver.quit()

if __name__ == "__main__":
    crawler = TousuCrawler()
    crawler.run()
