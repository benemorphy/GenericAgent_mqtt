"""Browser Service - 惰性WebDriver服务，支持优雅降级

将WebDriver生命周期封装为惰性服务，按需初始化，失败时优雅降级。
浏览器不可用时，Agent的文件操作、代码执行等核心功能不受影响。

Usage:
    from tools.browser_service import browser_service
    if browser_service.available:
        driver = browser_service.driver
        sessions = browser_service.get_all_sessions()

设计原则：
- 惰性初始化：仅在首次访问时加载TMWebDriver
- 优雅降级：浏览器不可用时不崩溃，返回明确错误
- 线程安全：双重检查锁定防止竞态
- 可恢复：支持reset()重置后重试
"""

import time
import threading
import traceback


class BrowserService:
    """惰性浏览器服务

    封装TMWebDriver的初始化与生命周期管理。
    - 首次调用时惰性初始化
    - 初始化失败返回明确错误而非崩溃
    - 支持重置以尝试恢复
    """

    def __init__(self):
        self._driver = None
        self._initialized = False
        self._init_error = None
        self._lock = threading.Lock()

    def _lazy_init(self):
        """真正初始化WebDriver（仅在首次调用时执行，线程安全）"""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:  # 双重检查锁定
                return
            self._initialized = True
            try:
                from TMWebDriver import TMWebDriver
                self._driver = TMWebDriver()
                for i in range(20):
                    time.sleep(1)
                    sess = self._driver.get_all_sessions()
                    if len(sess) > 0:
                        break
                if len(sess) == 0:
                    self._init_error = "浏览器初始化超时：无可用标签页（20秒等待后仍无会话）"
                    self._driver = None
                    return
                if len(sess) == 1:
                    time.sleep(3)  # 等待单个标签页稳定
            except Exception:
                self._init_error = f"浏览器初始化失败: {traceback.format_exc()}"
                self._driver = None

    @property
    def available(self) -> bool:
        """浏览器是否可用"""
        if self._driver is None:
            self._lazy_init()
        return self._driver is not None

    @property
    def driver(self):
        """获取TMWebDriver实例，按需初始化

        如果浏览器不可用，返回None。调用方应先用available检查。
        """
        if self._driver is None:
            self._lazy_init()
        return self._driver

    @property
    def init_error(self) -> str:
        """初始化错误信息（如果有）"""
        self._lazy_init()
        return self._init_error or ""

    def get_all_sessions(self):
        """获取所有标签页会话

        Returns:
            list: 会话列表，浏览器不可用时返回空列表
        """
        if not self.available:
            return []
        try:
            return self._driver.get_all_sessions()
        except Exception:
            self._init_error = f"获取会话失败: {traceback.format_exc()}"
            return []

    @property
    def default_session_id(self):
        """获取当前默认会话ID（代理到driver属性）"""
        if not self.available:
            return None
        return self._driver.default_session_id

    @default_session_id.setter
    def default_session_id(self, session_id):
        """设置默认会话ID"""
        if self.available:
            self._driver.default_session_id = session_id

    def reset(self):
        """重置浏览器服务（用于尝试恢复）"""
        with self._lock:
            if self._driver is not None:
                try:
                    self._driver.quit()
                except Exception:
                    pass
            self._driver = None
            self._initialized = False
            self._init_error = None


# 模块级单例
browser_service = BrowserService()
