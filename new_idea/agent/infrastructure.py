"""基础设施 - 日志、错误处理、工具装饰器"""

import functools
import logging
import sys
import time
from typing import TypeVar, Callable, Any, Optional
from dataclasses import dataclass


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("Agent")


# 自定义异常
class AgentError(Exception):
    """基础Agent异常"""
    pass


class ToolError(AgentError):
    """工具调用异常"""
    def __init__(self, message: str, tool_name: str = "", original_error: Optional[Exception] = None):
        super().__init__(message)
        self.tool_name = tool_name
        self.original_error = original_error


class ConfigError(AgentError):
    """配置错误"""
    pass


class CrawlerError(AgentError):
    """爬虫错误"""
    pass


class ModelError(AgentError):
    """模型错误"""
    pass


@dataclass
class ToolResult:
    """工具调用结果包装"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    tool_name: str = ""
    execution_time: float = 0.0

    @classmethod
    def ok(cls, data: Any, tool_name: str = "", execution_time: float = 0.0) -> "ToolResult":
        return cls(success=True, data=data, tool_name=tool_name, execution_time=execution_time)

    @classmethod
    def fail(cls, error: str, tool_name: str = "", execution_time: float = 0.0) -> "ToolResult":
        return cls(success=False, error=error, tool_name=tool_name, execution_time=execution_time)


T = TypeVar('T')


def with_retry(max_retries: int = 2, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """重试装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(f"{func.__name__} 第{attempt + 1}次尝试失败: {e}，{max_retries - attempt}次重试...")
                        time.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} 最终失败: {e}")
                        raise ToolError(f"工具{func.__name__}调用失败: {e}", tool_name=func.__name__, original_error=e)
            raise last_error
        return wrapper
    return decorator


def with_retry_advanced(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    on_retry_callback: Callable = None
):
    """增强版重试装饰器 - 支持指数退避和用户反馈

    Args:
        max_retries: 最大重试次数
        base_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
        backoff_factor: 退避因子
        retryable_exceptions: 可重试的异常类型
        on_retry_callback: 重试时的回调函数 (attempt, error, next_delay)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_error = e
                    if attempt < max_retries:
                        # 计算指数退避延迟
                        delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                        logger.warning(f"🔁 [{func.__name__}] 第{attempt + 1}次尝试失败，{delay:.1f}秒后重试... 错误: {str(e)[:50]}")

                        # 调用回调通知用户
                        if on_retry_callback:
                            try:
                                on_retry_callback(attempt + 1, e, delay)
                            except:
                                pass

                        time.sleep(delay)
                    else:
                        logger.error(f"❌ [{func.__name__}] 最终失败（已重试{max_retries}次）: {e}")
                        raise
            raise last_error
        return wrapper
    return decorator


# 判断错误是否可重试（用于HTTP错误）
def is_retryable_error(error) -> bool:
    """判断错误是否值得重试"""
    # HTTP 状态码
    if hasattr(error, 'code'):
        status = error.code
        # 429 (限流), 502 (网关错误), 503 (服务不可用), 504 (网关超时)
        return status in (429, 502, 503, 504)
    if hasattr(error, 'status'):
        status = error.status
        return status in (429, 502, 503, 504)

    # 连接错误
    error_msg = str(error).lower()
    retryable_keywords = [
        'timeout', 'timed out', 'connection', 'refused', 'reset',
        'temporarily unavailable', 'service unavailable', 'bad gateway'
    ]
    return any(kw in error_msg for kw in retryable_keywords)


def timed_tool(func: Callable[..., T]) -> Callable[..., ToolResult]:
    """计时工具装饰器 - 返回ToolResult"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> ToolResult:
        start = time.time()
        tool_name = func.__name__
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start
            logger.info(f"✅ {tool_name} 完成 ({execution_time:.2f}s)")
            return ToolResult.ok(result, tool_name=tool_name, execution_time=execution_time)
        except Exception as e:
            execution_time = time.time() - start
            logger.error(f"❌ {tool_name} 失败: {e}")
            return ToolResult.fail(str(e), tool_name=tool_name, execution_time=execution_time)
    return wrapper


def validate_required_fields(*fields: str):
    """验证必需参数字段"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for field in fields:
                if field not in kwargs or not kwargs[field]:
                    raise ToolError(f"缺少必需参数: {field}", tool_name=func.__name__)
            return func(*args, **kwargs)
        return wrapper
    return decorator


class EventBus:
    """简单的事件总线 - 用于组件间通信"""
    def __init__(self):
        self._listeners: dict[str, list[Callable]] = {}

    def on(self, event: str, handler: Callable):
        """注册事件处理器"""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(handler)

    def emit(self, event: str, data: Any = None):
        """触发事件"""
        if event in self._listeners:
            for handler in self._listeners[event]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"事件处理器错误: {e}")

    def off(self, event: str, handler: Callable):
        """移除事件处理器"""
        if event in self._listeners and handler in self._listeners[event]:
            self._listeners[event].remove(handler)


# 全局事件总线
events = EventBus()
