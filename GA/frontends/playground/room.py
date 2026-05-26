"""
Playground 房间系统 — 每个 MQTT 主题空间映射为一个"房间"

房间属性:
  - topic: 绑定的 MQTT 主题
  - name: 房间名（如 "公告板大厅"）
  - icon: 图标
  - commands: 房间内可用命令
"""

import re
from dataclasses import dataclass, field
from typing import Optional

ROOMS = [
    {
        "id": "lobby",
        "name": "公告板大厅",
        "icon": "🏛",
        "topic": "bbs/#",
        "desc": "BBS 消息总汇，浏览所有公开帖子",
        "commands": ["look", "listen", "post"],
    },
    {
        "id": "curiosity",
        "name": "好奇心花园",
        "icon": "🌱",
        "topic": "board/curiosity/#",
        "desc": "Agent 好奇心的种子在这里生长",
        "commands": ["look", "plant", "water"],
    },
    {
        "id": "agents",
        "name": "Agent 大厅",
        "icon": "🤖",
        "topic": "node/+/status",
        "desc": "查看在线 Agent 状态",
        "commands": ["look", "whisper"],
    },
    {
        "id": "tasks",
        "name": "任务大厅",
        "icon": "⚡",
        "topic": "board/task/#",
        "desc": "查看和发布任务",
        "commands": ["look", "claim", "post"],
    },
]
