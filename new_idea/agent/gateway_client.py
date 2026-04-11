"""网关客户端 - 通过Go网关调用远程分析服务

用于联调场景:
- 本地运行: python run.py --local
- 网关模式: python run.py --gateway http://127.0.0.1:8080

环境变量:
- GATEWAY_URL: 网关地址
- GATEWAY_ACCOUNT: 登录账号 (默认: spottruth_user)
- GATEWAY_PASSWORD: 登录密码 (默认: spottruth_user_123)
"""

import os
import sys
import time
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin

# 配置日志
def _get_logger():
    """获取logger(兼容独立运行和模块导入)"""
    try:
        from agent.infrastructure import logger
        return logger
    except ImportError:
        # 独立运行时使用简单日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

logger = _get_logger()


@dataclass
class GatewayConfig:
    """网关配置"""
    base_url: str = "http://127.0.0.1:8080"
    account: str = "spottruth_user"
    password: str = "spottruth_user_123"
    timeout: int = 30
    auto_refresh: bool = True  # Token过期自动刷新


class GatewayClient:
    """网关客户端 - 管理鉴权和API调用"""

    def __init__(self, config: Optional[GatewayConfig] = None):
        self.config = config or GatewayConfig()
        self.access_token: Optional[str] = None
        self.token_expires_at: float = 0
        self._ensure_env_config()

    def _ensure_env_config(self):
        """从环境变量加载配置"""
        if url := os.getenv("GATEWAY_URL"):
            self.config.base_url = url
        if account := os.getenv("GATEWAY_ACCOUNT"):
            self.config.account = account
        if password := os.getenv("GATEWAY_PASSWORD"):
            self.config.password = password

    def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        auth: bool = True,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """发起HTTP请求（带重试）"""
        url = urljoin(self.config.base_url, path)
        req_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # 添加认证头
        if auth and self.access_token:
            req_headers["Authorization"] = f"Bearer {self.access_token}"

        # 添加自定义头
        if headers:
            req_headers.update(headers)

        # 准备请求体
        body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None

        last_error = None
        for attempt in range(max_retries + 1):
            req = Request(
                url=url,
                data=body,
                headers=req_headers,
                method=method
            )

            try:
                with urlopen(req, timeout=self.config.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except HTTPError as e:
                error_body = e.read().decode("utf-8")
                # 可重试的错误：429(限流), 502(网关错误), 503(服务不可用), 504(网关超时)
                if e.code in (429, 502, 503, 504) and attempt < max_retries:
                    delay = min(1.0 * (2 ** attempt), 8.0)  # 指数退避，最大8秒
                    logger.warning(f"🔁 [Gateway] HTTP {e.code}，{delay:.1f}秒后重试... ({attempt + 1}/{max_retries})")
                    import time
                    time.sleep(delay)
                    continue

                # 不可重试的HTTP错误
                try:
                    error_data = json.loads(error_body)
                    raise GatewayError(
                        f"API错误: {error_data.get('message', error_body)}",
                        status=e.code,
                        code=error_data.get('code', 'UNKNOWN')
                    )
                except json.JSONDecodeError:
                    raise GatewayError(f"HTTP {e.code}: {error_body}", status=e.code)
            except URLError as e:
                # 连接错误可重试
                if attempt < max_retries:
                    delay = min(1.0 * (2 ** attempt), 8.0)
                    logger.warning(f"🔁 [Gateway] 连接失败，{delay:.1f}秒后重试... ({attempt + 1}/{max_retries}): {e.reason}")
                    import time
                    time.sleep(delay)
                    continue
                raise GatewayError(f"连接失败: {e.reason}")
            except Exception as e:
                # 其他异常
                if attempt < max_retries:
                    delay = min(1.0 * (2 ** attempt), 8.0)
                    logger.warning(f"🔁 [Gateway] 请求异常，{delay:.1f}秒后重试... ({attempt + 1}/{max_retries}): {e}")
                    import time
                    time.sleep(delay)
                    continue
                raise GatewayError(f"请求失败: {e}")

    def login(self) -> str:
        """登录获取Token"""
        logger.info(f"正在登录网关: {self.config.base_url}")

        try:
            resp = self._make_request(
                "POST",
                "/api/v1/auth/login",
                data={
                    "account": self.config.account,
                    "password": self.config.password,
                    "login_type": "password"
                },
                auth=False
            )

            self.access_token = resp["data"]["access_token"]
            expires_in = resp["data"].get("expires_in", 1800)
            self.token_expires_at = time.time() + expires_in - 60  # 提前60秒刷新

            logger.info(f"✅ 登录成功, Token有效期: {expires_in}秒")
            return self.access_token

        except GatewayError:
            raise
        except Exception as e:
            raise GatewayError(f"登录失败: {e}")

    def ensure_authenticated(self):
        """确保已认证(自动登录/刷新)"""
        if not self.access_token or time.time() > self.token_expires_at:
            self.login()

    def health_check(self) -> Dict:
        """健康检查"""
        return self._make_request("GET", "/healthz", auth=False)

    def ready_check(self) -> Dict:
        """就绪检查"""
        return self._make_request("GET", "/readyz", auth=False)

    def classify_product(self, product_name: str) -> str:
        """品类分类"""
        self.ensure_authenticated()

        resp = self._make_request(
            "POST",
            "/api/classify",
            data={"product_name": product_name},
            headers={"X-Request-ID": f"classify-{int(time.time())}"}
        )

        return resp.get("category", "electronics")

    def analyze_comments(
        self,
        comments: List[str],
        product_name: str,
        category: str = ""
    ) -> Dict[str, Any]:
        """分析评论(讽刺检测+情感分析)"""
        self.ensure_authenticated()

        return self._make_request(
            "POST",
            "/api/analyze",
            data={
                "comments": comments,
                "product_name": product_name,
                "category": category
            },
            headers={"X-Request-ID": f"analyze-{int(time.time())}"}
        )

    def summarize(
        self,
        statistics: Dict[str, Any],
        sample_comments: List[Dict]
    ) -> Dict[str, str]:
        """生成总结报告"""
        self.ensure_authenticated()

        return self._make_request(
            "POST",
            "/api/summarize",
            data={
                "statistics": statistics,
                "sample_comments": sample_comments
            }
        )

    def parse_intent(
        self,
        user_input: str,
        conversation_history: List[Dict[str, str]] = None,
        current_product: str = "",
        analyzed_platforms: List[str] = None
    ) -> Dict[str, Any]:
        """解析用户意图"""
        self.ensure_authenticated()

        return self._make_request(
            "POST",
            "/api/parse_intent",
            data={
                "user_input": user_input,
                "conversation_history": conversation_history or [],
                "current_product": current_product,
                "analyzed_platforms": analyzed_platforms or []
            }
        )

    def analyze_xiaohongshu(
        self,
        notes: List[Dict[str, Any]],
        keyword: str
    ) -> Dict[str, Any]:
        """分析小红书笔记"""
        self.ensure_authenticated()

        return self._make_request(
            "POST",
            "/api/analyze_xiaohongshu",
            data={
                "notes": notes,
                "keyword": keyword
            }
        )

    def analyze_heimao(
        self,
        complaints: List[Dict[str, Any]],
        brand: str
    ) -> Dict[str, Any]:
        """分析黑猫投诉"""
        self.ensure_authenticated()

        return self._make_request(
            "POST",
            "/api/analyze_heimao",
            data={
                "complaints": complaints,
                "brand": brand
            }
        )

    def generate_comparison_conclusion(
        self,
        product_a_name: str,
        product_b_name: str,
        stats_a: Dict[str, Any],
        stats_b: Dict[str, Any],
        summary_a: str,
        summary_b: str,
        advice_a: str,
        advice_b: str,
        heimao_analysis_a: Optional[Dict] = None,
        heimao_analysis_b: Optional[Dict] = None,
        xhs_analysis_a: Optional[Dict] = None,
        xhs_analysis_b: Optional[Dict] = None,
        has_taobao_a: bool = False,
        has_taobao_b: bool = False
    ) -> str:
        """生成对比结论"""
        self.ensure_authenticated()

        resp = self._make_request(
            "POST",
            "/api/compare_conclusion",
            data={
                "product_a_name": product_a_name,
                "product_b_name": product_b_name,
                "stats_a": stats_a,
                "stats_b": stats_b,
                "summary_a": summary_a,
                "summary_b": summary_b,
                "advice_a": advice_a,
                "advice_b": advice_b,
                "heimao_analysis_a": heimao_analysis_a,
                "heimao_analysis_b": heimao_analysis_b,
                "xhs_analysis_a": xhs_analysis_a,
                "xhs_analysis_b": xhs_analysis_b,
                "has_taobao_a": has_taobao_a,
                "has_taobao_b": has_taobao_b
            }
        )
        return resp.get("conclusion", "")


class GatewayError(Exception):
    """网关错误"""
    def __init__(self, message: str, status: Optional[int] = None, code: str = "UNKNOWN"):
        super().__init__(message)
        self.status = status
        self.code = code


class GatewayDataService:
    """基于网关的数据服务(替代本地爬虫)"""

    def __init__(self, client: Optional[GatewayClient] = None):
        self.client = client or GatewayClient()

    def search_product(self, brand: str, product: str):
        """搜索商品(网关模式暂不支持爬虫,返回空)"""
        logger.warning("网关模式不支持实时爬取,请直接提供评论数据")
        return None

    def get_comments(self, product_url: str, max_comments: int = 100):
        """获取评论(网关模式暂不支持,返回空列表)"""
        logger.warning("网关模式不支持实时爬取,请直接提供评论数据")
        return []

    def analyze_local_comments(
        self,
        comments: List[str],
        product_name: str
    ) -> Dict[str, Any]:
        """分析本地评论数据"""
        # 1. 品类分类
        category = self.client.classify_product(product_name)
        logger.info(f"商品分类: {category}")

        # 2. 分析评论
        result = self.client.analyze_comments(comments, product_name, category)

        # 3. 生成总结(如果需要)
        stats = result.get("statistics", {})
        sample_results = result.get("results", [])[:10]

        if sample_results:
            try:
                summary_resp = self.client.summarize(
                    stats,
                    [
                        {"text": r["text"], "sentiment": r["sentiment"], "is_sarcasm": r["is_sarcasm"]}
                        for r in sample_results
                    ]
                )
                result["summary"] = summary_resp.get("summary", "")
                result["advice"] = summary_resp.get("advice", "")
            except GatewayError as e:
                logger.warning(f"生成总结失败: {e}")
                result["summary"] = ""
                result["advice"] = ""

        return result


def create_gateway_client() -> GatewayClient:
    """工厂函数:创建网关客户端"""
    return GatewayClient()


def test_gateway_connection(url: str = "http://127.0.0.1:8080") -> bool:
    """测试网关连接"""
    print(f"\n[测试] 网关连接: {url}")

    client = GatewayClient(GatewayConfig(base_url=url))

    # 1. 健康检查
    try:
        health = client.health_check()
        print(f"   [OK] 健康检查: {health.get('status')}")
    except GatewayError as e:
        print(f"   [FAIL] 健康检查失败: {e}")
        return False

    # 2. 就绪检查
    try:
        ready = client.ready_check()
        print(f"   [OK] 就绪检查: {ready.get('status')} ({ready.get('mode')})")
    except GatewayError as e:
        print(f"   [FAIL] 就绪检查失败: {e}")
        return False

    # 3. 登录测试
    try:
        client.login()
        print(f"   [OK] 登录成功")
    except GatewayError as e:
        print(f"   [FAIL] 登录失败: {e}")
        return False

    # 4. 分类测试
    try:
        category = client.classify_product("iPhone 15")
        print(f"   [OK] 分类测试: {category}")
    except GatewayError as e:
        print(f"   [FAIL] 分类测试失败: {e}")
        return False

    print("\n[成功] 网关连接测试全部通过!")
    return True


if __name__ == "__main__":
    # 直接运行测试
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
    success = test_gateway_connection(url)
    sys.exit(0 if success else 1)
