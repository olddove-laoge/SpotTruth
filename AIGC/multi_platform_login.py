from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
import pickle
import os
import time

class PlatformLoginManager:
    def __init__(self):
        self.driver_path = r"AIGC\edgedriver\msedgedriver.exe"
        self.profiles = {
            'taobao': {
                'url': 'https://login.taobao.com',
                'cookie_file': 'taobao_cookies.pkl',
                'profile_dir': r'C:\taobao_bot_profile'
            },
            'xiaohongshu': {
                'url': 'https://www.xiaohongshu.com',
                'cookie_file': 'xiaohongshu_cookies.pkl',
                'profile_dir': r'C:\xiaohongshu_bot_profile'
            },
            'tousu': {
                'url': 'https://tousu.sina.com.cn',
                'cookie_file': 'tousu_cookies.pkl',
                'profile_dir': r'C:\tousu_bot_profile'
            }
        }
        self.drivers = {}
        self.lock = threading.Lock()

    def init_driver(self, platform):
        """初始化浏览器驱动"""
        options = webdriver.EdgeOptions()
        options.use_chromium = True
        
        # 配置用户数据目录
        profile_dir = self.profiles[platform]['profile_dir']
        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir)
        options.add_argument(f"user-data-dir={profile_dir}")
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        driver = webdriver.Edge(
            service=Service(self.driver_path),
            options=options
        )
        
        with self.lock:
            self.drivers[platform] = driver



    def save_cookies(self, platform):
        """保存cookies"""
        driver = self.drivers[platform]
        cookies = driver.get_cookies()
        with open(self.profiles[platform]['cookie_file'], 'wb') as f:
            pickle.dump(cookies, f)
        print(f"{platform} cookies saved")

    def platform_login(self, platform):
        """处理单个平台的登录流程"""
        self.init_driver(platform)
        driver = self.drivers[platform]
        
        print(f"请登录 {platform} 平台...")
        driver.get(self.profiles[platform]['url'])
        
        # 等待用户手动登录
        logged_in = False
        while True:
            try:
                # 检查窗口是否仍然打开
                _ = driver.window_handles
                time.sleep(1)
                
                # 每5秒尝试保存一次cookies
                if int(time.time()) % 1 == 0 and not logged_in:
                    try:
                        self.save_cookies(platform)
                        logged_in = True
                    except:
                        pass
            except:
                # 窗口已关闭，最后保存一次cookies
                try:
                    self.save_cookies(platform)
                except Exception as e:
                    print(f"保存cookies失败: {str(e)}")
                print(f"{platform} 窗口已关闭")
                break

    def start(self):
        """启动多平台登录"""
        print("即将打开淘宝、小红书和黑猫投诉的登录页面，请依次登录...")
        
        threads = []
        for platform in self.profiles:
            t = threading.Thread(target=self.platform_login, args=(platform,))
            t.start()
            threads.append(t)
        
        # 等待所有平台登录完成
        for t in threads:
            t.join()
            
        print("所有平台登录凭证已保存")

if __name__ == "__main__":
    manager = PlatformLoginManager()
    manager.start()
