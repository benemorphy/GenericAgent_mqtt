"""
Observability — 结构化日志 + Prometheus Metrics

用法:
    from tools.observability import metrics, setup_metrics_server
    metrics.inc("mqtt_messages", {"type": "register"})
"""

import os, threading, time

_ENABLED = os.environ.get("OBSERVABILITY_ENABLED", "true").lower() == "true"
_METRICS_PORT = int(os.environ.get("METRICS_PORT", "9090"))


class _MetricsCollector:
    """Metrics 收集器（prometheus_client 可选）"""

    def __init__(self):
        self._counters = {}
        self._histograms = {}
        if _ENABLED:
            try:
                from prometheus_client import Counter, Histogram
                self._counters = {
                    "mqtt_messages": Counter("mqtt_messages_total", "MQTT messages", ["type"]),
                    "register": Counter("bbs_register_total", "Register requests", ["board"]),
                    "post": Counter("bbs_post_total", "Post requests", ["board"]),
                }
                self._histograms = {
                    "process_time": Histogram("bbs_process_seconds", "Processing time", ["handler"]),
                }
            except ImportError:
                pass

    def inc(self, name, labels=None):
        c = self._counters.get(name)
        if c:
            c.labels(**(labels or {})).inc()

    def observe(self, name, value, labels=None):
        h = self._histograms.get(name)
        if h:
            h.labels(**(labels or {})).observe(value)


metrics = _MetricsCollector()


def setup_metrics_server():
    """启动 Prometheus metrics HTTP 服务器（daemon 线程）"""
    if not _ENABLED:
        return
    try:
        from prometheus_client import start_http_server
        t = threading.Thread(target=start_http_server, args=(_METRICS_PORT,), daemon=True)
        t.start()
        import logging
        logging.getLogger("observability").info(f"Metrics server on :{_METRICS_PORT}")
    except ImportError:
        pass
