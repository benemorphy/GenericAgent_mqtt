"""
CuriosityBoard Plugin — BBS 好奇心讨论板

Agent在感知中产生的好奇心信号 (CuriositySignal) 可发布到此板，
其他Agent（或同一Agent不同时段）可订阅、讨论、合并视角。

Topics:
    board/curiosity/post          → 发布好奇心帖
    board/curiosity/post/{oid}    → 指定帖子的详情请求
    board/curiosity/discuss/{oid} → 对帖子的回复
    curiosity/post/response/{corr_id}  → 发帖响应
    curiosity/discuss/response/{corr_id} → 回复响应

帖子结构:
    {
        "id": "uuid",
        "type": "anomaly|pattern|new|missing|change|connection",
        "source": "file_read|web_scan|code_run(dir)|agent_dreaming",
        "target": "curiosity_target",
        "reason": "why curious",
        "severity": 0.5,
        "author": "agent_id",
        "created_at": timestamp,
        "status": "open|discussing|resolved|archived",
        "responses": [{"author", "content", "created_at"}, ...]
    }
"""

import json, uuid, time
from mqtt_bbs.plugin import Plugin, plugin_hook

POST_BASE = "board/curiosity"
POST_TOPIC = f"{POST_BASE}/post"

@plugin_hook
class CuriosityBoardPlugin(Plugin):
    name = "curiosity_board"
    version = "0.1"
    description = "基于BBS的好奇心讨论板 — 发帖/讨论/归档"

    def __init__(self):
        super().__init__()
        self._posts: dict[str, dict] = {}  # id → post
        self._voters: dict[str, set] = {}  # post_id → {agent_ids} 去重
        self._archive_timer = None

    def on_load(self, ctx):
        # 订阅好奇心发布和讨论
        ctx.subscribe(f"{POST_BASE}/post", self._on_post)
        ctx.subscribe(f"{POST_BASE}/post/+", self._on_post_detail)
        ctx.subscribe(f"{POST_BASE}/discuss/+", self._on_discuss)
        ctx.subscribe(f"{POST_BASE}/query", self._on_query)
        ctx.subscribe(f"{POST_BASE}/status/+", self._on_status)
        ctx.subscribe(f"{POST_BASE}/hot", self._on_hot)
        # P1: 投票
        ctx.subscribe(f"{POST_BASE}/vote/+", self._on_vote)

        # 加载已有帖子（如果配置了持久化路径）
        data_file = ctx.get_config("data_file", "")
        if data_file:
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    self._posts = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                self._posts = {}

        print(f"  [Plugin curiosity_board] 已加载 (共 {len(self._posts)} 个历史帖子)")

    def on_unload(self):
        # 持久化帖子
        self._save_posts()

    # ── 内部方法 ──

    def _save_posts(self):
        data_file = self.ctx.get_config("data_file", "")
        if data_file:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(self._posts, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _is_duplicate(a: dict, b: dict) -> bool:
        """判断两条帖子是否相似（关键词重叠率 > 0.7 且同 author 同 type）"""
        if a.get("author") != b.get("author") or a.get("type") != b.get("type"):
            return False
        words_a = set(a.get("reason", "").lower().split()[:10])
        words_b = set(b.get("reason", "").lower().split()[:10])
        if not words_a or not words_b:
            return False
        overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
        return overlap > 0.7

    def _archive_stale(self):
        """归档 48 小时无回应的帖子"""
        cutoff = time.time() - 172800  # 48h
        archived = 0
        for pid, post in list(self._posts.items()):
            if post["status"] in ("open",) and post["created_at"] < cutoff:
                post["status"] = "archived"
                archived += 1
        if archived:
            print(f"  [Curiosity] 归档 {archived} 条过期好奇心")

    def _respond(self, topic_suffix: str, corr_id: str, data: dict):
        """向请求者发送响应"""
        topic = f"curiosity/{topic_suffix}/response/{corr_id}"
        self.ctx.publish(topic, data)

    # ── 事件处理 ──

    def _on_post(self, topic: str, payload):
        """收到新好奇心帖"""
        if not isinstance(payload, dict):
            return
        corr_id = payload.get("corr_id", str(uuid.uuid4()))
        now = time.time()

        # P1: 去重 — 24h 内同作者同类型相似内容
        for existing in self._posts.values():
            if existing["created_at"] > now - 86400 and self._is_duplicate(existing, payload):
                self._respond("post", corr_id, {"ok": True, "id": existing["id"], "status": "duplicate"})
                print(f"  [Curiosity] 去重: 定向到 #{existing['id']}")
                return

        post_id = str(uuid.uuid4())[:8]
        post = {
            "id": post_id,
            "type": payload.get("type", "anomaly"),
            "source": payload.get("source", "unknown"),
            "target": payload.get("target", ""),
            "reason": payload.get("reason", ""),
            "severity": float(payload.get("severity", 0.5)),
            "author": payload.get("agent_id", payload.get("author", "unknown")),
            "created_at": now,
            "updated_at": now,
            "status": "open",
            "responses": [],
        }
        self._posts[post_id] = post
        self._save_posts()

        # 广播到新的帖子主题
        self.ctx.publish(f"{POST_BASE}/new", post)

        # 回复创建者
        # P1: 标签订阅 — 按标签发布到独立 topic
        tags = payload.get("tags", []) if isinstance(payload, dict) else []
        for tag in tags:
            tag_clean = tag.strip().lstrip("#")
            self.ctx.publish(f"{POST_BASE}/tag/{tag_clean}", {
                "id": post_id, "type": post["type"],
                "reason": post["reason"][:100], "author": post["author"],
            })
        self._respond("post", corr_id, {"ok": True, "id": post_id, "status": "open"})
        print(f"  [Curiosity] 新帖子 #{post_id}: [{post['type']}] {post['reason'][:60]}")

    def _on_post_detail(self, topic: str, payload):
        """请求指定帖子的详情"""
        # topic: board/curiosity/post/{post_id}
        parts = topic.split("/")
        if len(parts) < 4:
            return
        post_id = parts[-1]
        corr_id = payload.get("corr_id", "") if isinstance(payload, dict) else ""

        post = self._posts.get(post_id)
        if post:
            self._respond("post", corr_id, {"ok": True, "post": post})
        else:
            self._respond("post", corr_id, {"ok": False, "error": f"帖子 #{post_id} 不存在"})

    def _on_discuss(self, topic: str, payload):
        """收到对帖子的回复讨论"""
        if not isinstance(payload, dict):
            return
        # topic: board/curiosity/discuss/{post_id}
        parts = topic.split("/")
        if len(parts) < 4:
            return
        post_id = parts[-1]
        corr_id = payload.get("corr_id", "")
        now = time.time()

        post = self._posts.get(post_id)
        if post is None:
            self._respond("discuss", corr_id, {"ok": False, "error": f"帖子 #{post_id} 不存在"})
            return

        response = {
            "author": payload.get("agent_id", payload.get("author", "unknown")),
            "content": payload.get("content", ""),
            "created_at": now,
        }
        post["responses"].append(response)
        post["updated_at"] = now
        post["status"] = "discussing"  # 任何回复自动标记为讨论中
        self._save_posts()

        self._respond("discuss", corr_id, {"ok": True, "post_id": post_id, "response_count": len(post["responses"])})
        print(f"  [Curiosity] #{post_id} 收到新回复 ({len(post['responses'])} 条)")

    def _on_vote(self, topic: str, payload):
        """投票: board/curiosity/vote/{post_id}"""
        if not isinstance(payload, dict):
            return
        parts = topic.split("/")
        if len(parts) < 4:
            return
        post_id = parts[-1]
        change = int(payload.get("change", 1))
        agent = payload.get("agent_id", "")
        # 去重: 每个 agent 只算一次
        if post_id in self._voters and agent in self._voters[post_id]:
            return
        post = self._posts.get(post_id)
        if post is None:
            return
        self._voters.setdefault(post_id, set()).add(agent)
        post["votes"] = post.get("votes", 0) + change
        print(f"  [Curiosity] #{post_id} 投票: {change:+d} (now {post['votes']})")

    def _on_status(self, topic: str, payload):
        """更新帖子状态"""
        if not isinstance(payload, dict):
            return
        parts = topic.split("/")
        if len(parts) < 4:
            return
        post_id = parts[-1]
        corr_id = payload.get("corr_id", "")

        post = self._posts.get(post_id)
        if post is None:
            self._respond("status", corr_id, {"ok": False, "error": f"帖子 #{post_id} 不存在"})
            return

        new_status = payload.get("status", "")
        if new_status in ("open", "discussing", "resolved", "archived"):
            post["status"] = new_status
            post["updated_at"] = time.time()
            self._save_posts()
            self._respond("status", corr_id, {"ok": True, "post_id": post_id, "status": new_status})
        else:
            self._respond("status", corr_id, {"ok": False, "error": f"无效状态: {new_status}"})

    def _on_query(self, topic: str, payload):
        """查询帖子列表"""
        corr_id = payload.get("corr_id", "") if isinstance(payload, dict) else ""
        filters = {}
        if isinstance(payload, dict):
            filters = {
                "status": payload.get("status"),
                "type": payload.get("type"),
                "limit": min(int(payload.get("limit", 20)), 100),
            }

        results = list(self._posts.values())
        # 按状态过滤
        if filters.get("status"):
            results = [p for p in results if p["status"] == filters["status"]]
        if filters.get("type"):
            results = [p for p in results if p["type"] == filters["type"]]
        # 按时间排序（最新在前面）
        results.sort(key=lambda p: p.get("created_at", 0), reverse=True)
        # 截断
        limit = filters.get("limit", 20)
        results = results[:limit]

        self._respond("query", corr_id, {"ok": True, "count": len(results), "posts": results})

    def _on_hot(self, topic: str, payload):
        """获取热门/活跃的好奇心帖子"""
        corr_id = payload.get("corr_id", "") if isinstance(payload, dict) else ""

        # 按活跃度排序: 回复数 * 0.4 + 优先级 * 0.6
        scored = []
        for post in self._posts.values():
            if post["status"] not in ("open", "discussing"):
                continue
            score = len(post["responses"]) * 0.4 + post.get("severity", 0.5) * 0.6
            scored.append((score, post))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_posts = [p for _, p in scored[:10]]

        self._respond("hot", corr_id, {"ok": True, "count": len(top_posts), "posts": top_posts})
