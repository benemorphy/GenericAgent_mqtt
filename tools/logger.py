"""
GenericAgent 日志模块 — 替代 print 的分级日志

用法:
    from tools.logger import log
    log.info("Agent started")
    log.warn("Retry attempt %d", n)
    log.error("Failed: %s", err, exc_info=True)

分级:
    DEBUG, INFO, WARN, ERROR — 分别对应不同的终端颜色
    默认显示 >= INFO，设 env LOG_LEVEL=DEBUG 可见调试日志
"""

import os, sys, logging, threading

_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARN": logging.WARN,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}

class ColorFormatter(logging.Formatter):
    """终端带颜色的日志格式"""
    _COLORS = {
        "DEBUG": "\033[36m",      # 青色
        "INFO": "\033[32m",       # 绿色
        "WARNING": "\033[33m",    # 黄色
        "ERROR": "\033[31m",      # 红色
        "RESET": "\033[0m",
    }

    def format(self, record):
        level = record.levelname
        color = self._COLORS.get(level, self._COLORS["RESET"])
        reset = self._COLORS["RESET"]
        record.levelname = f"{color}{level:5s}{reset}"
        return super().format(record)


def _setup():
    """初始化根日志器"""
    level = _LEVEL_MAP.get(_LOG_LEVEL, logging.INFO)
    logger = logging.getLogger("ga")
    logger.setLevel(level)

    if logger.handlers:
        return logger  # 防止重复初始化

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = ColorFormatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # 可选文件日志
    log_dir = os.environ.get("LOG_DIR", "")
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        fh = logging.FileHandler(
            os.path.join(log_dir, "ga.log"),
            encoding="utf-8"
        )
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(fh)

    return logger


log = _setup()

__all__ = ["log"]
