"""
MQTT BBS Client — Agent协作消息总线客户端

供智能体（Agent）使用的 MQTT 客户端库，
不依赖任何服务端组件，可独立分发。

快速开始:
    from Mqtt_bbs_client import BBSClient
    
    # 创建客户端连接
    client = BBSClient("my_agent")
    client.connect()
    client.publish("bbs/test/hello", {"msg": "Hello MQTT!"})
"""

from .client import BBSClient, TaskMessage, TaskOutput
from .types import TaskStatus
from . import config

__version__ = "0.1.0"
