"""数据服务层 - 统一封装爬虫调用"""

import sys
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config import paths as paths_config
from agent.infrastructure import logger, timed_tool, ToolResult, ToolError, validate_required_fields
from agent.models import Comment, ProductInfo, SourceType


@dataclass
class CrawlerConfig:
    """爬虫配置"""
    driver: Any = None
    driver_path: str = paths_config.driver_path


class DataService:
    """数据服务 - 统一的数据采集接口"""

    def __init__(self, crawler_config: CrawlerConfig):
        self.config = crawler_config
        self._taobao_scraper_class = None
        self._xhs_scraper_class = None
        self._heimao_scraper_class = None

    def _get_taobao_scraper(self):
        """获取淘宝爬虫类"""
        if self._taobao_scraper_class is None:
            try:
                if paths_config.taobao_crawler_path not in sys.path:
                    sys.path.insert(0, paths_config.taobao_crawler_path)
                from taobao_new import TaobaoScraperNew
                self._taobao_scraper_class = TaobaoScraperNew
            except Exception as e:
                raise ToolError(f"导入淘宝爬虫失败: {e}")
        return self._taobao_scraper_class

    def _get_xhs_scraper(self):
        """获取小红书爬虫类"""
        if self._xhs_scraper_class is None:
            try:
                if paths_config.xhs_crawler_path not in sys.path:
                    sys.path.insert(0, paths_config.xhs_crawler_path)
                from xiaohongshu_scraper import XiaohongshuScraper
                self._xhs_scraper_class = XiaohongshuScraper
            except Exception as e:
                raise ToolError(f"导入小红书爬虫失败: {e}")
        return self._xhs_scraper_class

    def _get_heimao_scraper(self):
        """获取黑猫爬虫类"""
        if self._heimao_scraper_class is None:
            try:
                if paths_config.xhs_crawler_path not in sys.path:
                    sys.path.insert(0, paths_config.xhs_crawler_path)
                from tousu_crawler import TousuCrawler
                self._heimao_scraper_class = TousuCrawler
            except Exception as e:
                raise ToolError(f"导入黑猫爬虫失败: {e}")
        return self._heimao_scraper_class

    @timed_tool
    @validate_required_fields("brand", "product")
    def search_product(self, brand: str, product: str, max_results: int = 5) -> ToolResult:
        """搜索淘宝商品"""
        try:
            TaobaoScraperNew = self._get_taobao_scraper()

            if self.config.driver:
                # 使用已登录的driver
                scraper = TaobaoScraperNew.__new__(TaobaoScraperNew)
                scraper.driver = self.config.driver
                products = scraper.search_products(brand, product, max_results)
            else:
                with TaobaoScraperNew(driver_path=self.config.driver_path) as scraper:
                    scraper.ensure_login()
                    products = scraper.search_products(brand, product, max_results)

            # 转换为ProductInfo
            result = []
            for p in products:
                result.append(ProductInfo(
                    name=p.get("name", ""),
                    url=p.get("url", ""),
                    price=p.get("price", ""),
                    sales=p.get("sales", ""),
                    shop_name=p.get("shop_name", ""),
                    shop_tag=p.get("shop_tag", ""),
                    image_url=p.get("image_url", "")
                ))

            return result

        except Exception as e:
            raise ToolError(f"搜索商品失败: {e}", tool_name="search_product")

    @timed_tool
    def get_comments(
        self,
        url: str = "",
        brand: str = "",
        product: str = "",
        max_count: int = 100
    ) -> ToolResult:
        """获取淘宝评论"""
        try:
            TaobaoScraperNew = self._get_taobao_scraper()

            # 使用内存存储替代临时文件
            comments_data = []

            if self.config.driver:
                scraper = TaobaoScraperNew.__new__(TaobaoScraperNew)
                scraper.driver = self.config.driver

                if url:
                    # 直接访问URL获取评论
                    scraper.scrape_reviews(
                        output_file="/dev/null",  # 不使用文件
                        max_comments=max_count,
                        manual_input=False,
                        preset_url=url
                    )
                else:
                    scraper.select_product_and_scrape(
                        brand=brand,
                        product=product,
                        output_file="/dev/null",
                        max_comments=max_count
                    )

                # TODO: 修改爬虫支持返回数据而非写入文件
                # 临时方案：读取临时文件
                temp_file = os.path.join(paths_config.data_dir, "temp_comments.txt")
                if os.path.exists(temp_file):
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        comments_data = [
                            Comment(text=line.strip(), source=SourceType.TAOBAO)
                            for line in f if line.strip()
                        ][:max_count]
            else:
                with TaobaoScraperNew(driver_path=self.config.driver_path) as scraper:
                    scraper.ensure_login()
                    temp_file = os.path.join(paths_config.data_dir, "temp_comments.txt")

                    if url:
                        scraper.scrape_reviews(
                            output_file=temp_file,
                            max_comments=max_count,
                            manual_input=False,
                            preset_url=url
                        )
                    else:
                        scraper.select_product_and_scrape(
                            brand=brand,
                            product=product,
                            output_file=temp_file,
                            max_comments=max_count
                        )

                    if os.path.exists(temp_file):
                        with open(temp_file, 'r', encoding='utf-8') as f:
                            comments_data = [
                                Comment(text=line.strip(), source=SourceType.TAOBAO)
                                for line in f if line.strip()
                            ][:max_count]

            return comments_data

        except Exception as e:
            raise ToolError(f"获取评论失败: {e}", tool_name="get_comments")

    @timed_tool
    @validate_required_fields("keyword")
    def search_xiaohongshu(self, keyword: str, max_notes: int = 30) -> ToolResult:
        """搜索小红书笔记"""
        try:
            XiaohongshuScraper = self._get_xhs_scraper()
            temp_file = os.path.join(paths_config.data_dir, "temp_xhs.txt")

            if self.config.driver:
                scraper = XiaohongshuScraper.__new__(XiaohongshuScraper)
                scraper.driver = self.config.driver
                scraper.scrape_search_results(
                    keyword=keyword,
                    output_file=temp_file,
                    max_items=max_notes
                )
            else:
                with XiaohongshuScraper(driver_path=self.config.driver_path) as scraper:
                    scraper.ensure_login()
                    scraper.scrape_search_results(
                        keyword=keyword,
                        output_file=temp_file,
                        max_items=max_notes
                    )

            # 读取详情
            notes = []
            desc_file = temp_file.replace('.txt', '_desc.txt')
            if os.path.exists(desc_file):
                with open(desc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    entries = content.split('URL:')
                    for entry in entries:
                        if '内容:' in entry:
                            parts = entry.split('内容:')
                            if len(parts) > 1:
                                text = parts[1].strip()
                                if text:
                                    notes.append(Comment(
                                        text=text,
                                        source=SourceType.XIAOHONGSHU
                                    ))

            return notes[:max_notes]

        except Exception as e:
            raise ToolError(f"搜索小红书失败: {e}", tool_name="search_xiaohongshu")

    @timed_tool
    @validate_required_fields("brand")
    def search_heimao(self, brand: str, max_complaints: int = 50) -> ToolResult:
        """搜索黑猫投诉"""
        try:
            TousuCrawler = self._get_heimao_scraper()
            temp_file = os.path.join(paths_config.xhs_crawler_path, "tousu.txt")

            # 写入品牌
            brand_file = os.path.join(paths_config.xhs_crawler_path, "simple_prod_name_with_brand.txt")
            with open(brand_file, 'w', encoding='utf-8') as f:
                f.write(brand)

            if self.config.driver:
                scraper = TousuCrawler.__new__(TousuCrawler)
                scraper.driver = self.config.driver
                scraper.keyword = brand
                scraper.max_items = max_complaints

                search_url = f"https://tousu.sina.com.cn/index/search/?keywords={brand}&t=1"
                self.config.driver.get(search_url)
                import time
                time.sleep(3)

                collected = scraper.collect_complaints()
                with open(temp_file, 'w', encoding='utf-8') as f:
                    for item in collected:
                        f.write(item + "\n")
            else:
                scraper = TousuCrawler(keyword=brand, max_items=max_complaints)
                collected = scraper.collect_complaints()
                with open(temp_file, 'w', encoding='utf-8') as f:
                    for item in collected:
                        f.write(item + "\n")
                scraper.driver.quit()

            # 读取结果
            complaints = []
            if os.path.exists(temp_file):
                with open(temp_file, 'r', encoding='utf-8') as f:
                    complaints = [
                        Comment(text=line.strip(), source=SourceType.HEIMAO)
                        for line in f if line.strip()
                    ][:max_complaints]

            return complaints

        except Exception as e:
            raise ToolError(f"搜索黑猫投诉失败: {e}", tool_name="search_heimao")
