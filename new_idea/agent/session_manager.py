"""会话管理器 - 多Session缓存和隔离

提供:
- Session创建、加载、列出、切换
- 商品数据缓存（淘宝、小红书、黑猫）
- 分析结果缓存
- 跨Session隔离
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from config import paths as paths_config
from agent.infrastructure import logger
from agent.models import AnalysisResult


@dataclass
class ProductCache:
    """商品缓存数据"""
    product_name: str
    brand: str = ""
    category: str = ""

    # 原始数据
    taobao_comments: List[str] = None
    xiaohongshu_notes: List[str] = None
    heimao_complaints: List[str] = None

    # 分析结果
    taobao_analysis: Dict[str, Any] = None  # stats, results, summary, advice
    xiaohongshu_analysis: Dict[str, Any] = None
    heimao_analysis: Dict[str, Any] = None

    # 元数据
    created_at: str = ""
    updated_at: str = ""
    analyzed_platforms: List[str] = None

    def __post_init__(self):
        if self.taobao_comments is None:
            self.taobao_comments = []
        if self.xiaohongshu_notes is None:
            self.xiaohongshu_notes = []
        if self.heimao_complaints is None:
            self.heimao_complaints = []
        if self.analyzed_platforms is None:
            self.analyzed_platforms = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def has_platform_data(self, platform: str) -> bool:
        """检查是否有某平台的数据"""
        if platform == 'taobao':
            return len(self.taobao_comments) > 0
        elif platform == 'xiaohongshu':
            return len(self.xiaohongshu_notes) > 0
        elif platform == 'heimao':
            return len(self.heimao_complaints) > 0
        return False

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProductCache':
        return cls(**data)


@dataclass
class SessionMetadata:
    """会话元数据"""
    session_id: str
    created_at: str
    updated_at: str
    current_product: str = ""
    analyzed_products: List[str] = None
    description: str = ""  # 用户可添加的描述

    def __post_init__(self):
        if self.analyzed_products is None:
            self.analyzed_products = []

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionMetadata':
        return cls(**data)


class SessionManager:
    """会话管理器"""

    CACHE_EXPIRY_HOURS = 24  # 缓存24小时过期

    def __init__(self):
        self.sessions_dir = paths_config.data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_id: Optional[str] = None
        self.metadata: Optional[SessionMetadata] = None
        self.cache: Dict[str, ProductCache] = {}  # 内存缓存

    def create_session(self, description: str = "") -> str:
        """创建新会话"""
        session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        session_dir = self.sessions_dir / session_id
        cache_dir = session_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        self.metadata = SessionMetadata(
            session_id=session_id,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            description=description
        )
        self.current_session_id = session_id
        self.cache = {}
        self._save_metadata()

        logger.info(f"✅ 创建新会话: {session_id}")
        return session_id

    def load_session(self, session_id: str) -> bool:
        """加载会话"""
        session_dir = self.sessions_dir / session_id
        if not session_dir.exists():
            logger.error(f"❌ 会话不存在: {session_id}")
            return False

        # 加载元数据
        metadata_file = session_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                self.metadata = SessionMetadata.from_dict(json.load(f))
        else:
            self.metadata = SessionMetadata(
                session_id=session_id,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )

        self.current_session_id = session_id
        self.cache = {}  # 延迟加载，按需读取
        logger.info(f"✅ 加载会话: {session_id}, 当前商品: {self.metadata.current_product}")
        return True

    def list_sessions(self) -> List[SessionMetadata]:
        """列出所有会话"""
        sessions = []
        for session_dir in sorted(self.sessions_dir.iterdir(), key=lambda x: x.name, reverse=True):
            if session_dir.is_dir():
                metadata_file = session_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            sessions.append(SessionMetadata.from_dict(json.load(f)))
                    except:
                        pass
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        session_dir = self.sessions_dir / session_id
        if not session_dir.exists():
            return False

        import shutil
        shutil.rmtree(session_dir)
        logger.info(f"🗑️  删除会话: {session_id}")

        if self.current_session_id == session_id:
            self.current_session_id = None
            self.metadata = None
            self.cache = {}

        return True

    def get_product_cache(self, product_name: str) -> Optional[ProductCache]:
        """获取商品缓存（内存+文件）"""
        # 先查内存
        if product_name in self.cache:
            return self.cache[product_name]

        # 再查文件
        cache_file = self._get_cache_file(product_name)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = ProductCache.from_dict(json.load(f))
                    # 检查是否过期
                    updated = datetime.fromisoformat(cache.updated_at)
                    if datetime.now() - updated > timedelta(hours=self.CACHE_EXPIRY_HOURS):
                        logger.info(f"⏰ 缓存已过期: {product_name}")
                        return None
                    # 加载到内存
                    self.cache[product_name] = cache
                    return cache
            except Exception as e:
                logger.error(f"❌ 加载缓存失败: {e}")

        return None

    def save_product_cache(self, cache: ProductCache):
        """保存商品缓存"""
        if not self.current_session_id:
            logger.error("❌ 没有活跃的会话")
            return

        cache.updated_at = datetime.now().isoformat()
        self.cache[cache.product_name] = cache

        # 保存到文件
        cache_file = self._get_cache_file(cache.product_name)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"💾 保存缓存: {cache.product_name}")
        except Exception as e:
            logger.error(f"❌ 保存缓存失败: {e}")

        # 更新元数据
        if cache.product_name not in self.metadata.analyzed_products:
            self.metadata.analyzed_products.append(cache.product_name)
        self.metadata.updated_at = datetime.now().isoformat()
        self._save_metadata()

    def update_current_product(self, product_name: str):
        """更新当前商品"""
        if self.metadata:
            self.metadata.current_product = product_name
            self._save_metadata()

    def get_current_product(self) -> str:
        """获取当前商品"""
        return self.metadata.current_product if self.metadata else ""

    def get_analyzed_platforms(self, product_name: str) -> List[str]:
        """获取商品已分析的平台"""
        cache = self.get_product_cache(product_name)
        return cache.analyzed_platforms if cache else []

    def _get_cache_file(self, product_name: str) -> Path:
        """获取缓存文件路径"""
        # 商品名做文件名（简化处理）
        safe_name = "".join(c if c.isalnum() or c in '_- ' else '_' for c in product_name)
        safe_name = safe_name[:50]  # 限制长度
        return self.sessions_dir / self.current_session_id / "cache" / f"{safe_name}.json"

    def _save_metadata(self):
        """保存会话元数据"""
        if not self.current_session_id or not self.metadata:
            return

        metadata_file = self.sessions_dir / self.current_session_id / "metadata.json"
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ 保存元数据失败: {e}")


def prompt_select_session() -> Optional[str]:
    """交互式选择会话"""
    manager = SessionManager()
    sessions = manager.list_sessions()

    if not sessions:
        print("📂 没有找到历史会话，创建新会话...")
        return manager.create_session()

    print("\n📁 历史会话：")
    print("-" * 60)
    for i, s in enumerate(sessions[:5], 1):  # 只显示最近5个
        created = datetime.fromisoformat(s.created_at).strftime('%m-%d %H:%M')
        desc = f" - {s.description}" if s.description else ""
        current = f" (当前: {s.current_product})" if s.current_product else ""
        print(f"   {i}. [{created}] {desc}{current}")
    print(f"   N. 创建新会话")
    print("-" * 60)

    while True:
        choice = input("请选择 (1-5/N): ").strip().upper()
        if choice == 'N':
            desc = input("会话描述（可选）: ").strip()
            return manager.create_session(desc)
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(sessions[:5]):
                return sessions[idx].session_id
        except ValueError:
            pass
        print("❌ 无效选择")


if __name__ == "__main__":
    # 测试
    session_id = prompt_select_session()
    print(f"选中会话: {session_id}")
