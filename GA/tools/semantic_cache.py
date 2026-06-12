#!/usr/bin/env python3
"""
Semantic Cache for LLM responses

方案A(语义embedding) + 方案B(意图签名) 融合缓存。
在精确 SHA256 hash 缓存之前，先用语义相似度匹配查找缓存。

策略:
1. _extract_intent: 从 messages 中提取意图签名 (替换具体值为占位符)
2. _get_embedding: 将意图签名转为向量 (char n-gram + numpy)
3. lookup: 余弦相似度匹配 > threshold 则命中
4. store: 实际 API 调用后存入语义缓存

依赖: numpy (已安装), 可选 sentence-transformers (自动检测使用)
"""

import re
import time
import hashlib
import logging
from collections import OrderedDict

import numpy as np

logger = logging.getLogger(__name__)

# ── 尝试使用 sentence-transformers (更精确的语义匹配) ──
_USE_SENTENCE_TRANSFORMERS = False
_sentence_model = None

try:
    from sentence_transformers import SentenceTransformer
    _USE_SENTENCE_TRANSFORMERS = True
    logger.info("semantic_cache: sentence-transformers available, will use for embeddings")
except ImportError:
    logger.info("semantic_cache: sentence-transformers not available, using char n-gram fallback")


def _get_sentence_model(model_name="all-MiniLM-L6-v2"):
    """延迟加载 sentence-transformers 模型"""
    global _sentence_model
    if _sentence_model is None and _USE_SENTENCE_TRANSFORMERS:
        try:
            _sentence_model = SentenceTransformer(model_name)
            logger.info("semantic_cache: loaded sentence model %s", model_name)
        except Exception as e:
            logger.warning("semantic_cache: failed to load sentence model: %s", e)
    return _sentence_model


# ── 意图签名提取 (方案B) ──

# 需要替换为占位符的模式
_INTENT_PATTERNS = [
    # 文件路径: D:\xxx\yyy 或 /home/xxx/yyy (字符串开头或空格/引号后)
    (re.compile(r'(?:(?<=^)|(?<=[\s"\'`]))[A-Za-z]:\\[^\s,;)\]]{3,}'), '@fp'),
    (re.compile(r'(?:(?<=^)|(?<=[\s"\'`]))/[^\s,;)\]]{3,}'), '@fp'),
    # 行号: "line 42" 或 ":42"
    (re.compile(r'\bline\s+\d+\b', re.IGNORECASE), 'line @n'),
    (re.compile(r':(\d{2,})\b'), ':@n'),
    # UUID
    (re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'), '@u'),
    # 长 hex hash
    (re.compile(r'\b[0-9a-f]{16,}\b'), '@h'),
    # 时间戳: 2026-06-10 或 2026/06/10 (必须在通用数字之前)
    (re.compile(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}'), '@d'),
    # URL (必须在通用数字之前)
    (re.compile(r'https?://\S+'), '@url'),
    # 百分比: 25% 或 25.5% (必须在通用数字之前)
    (re.compile(r'\d+\.?\d*%'), '@pct'),
    # IP 地址: 192.168.1.1 (必须在通用数字之前)
    (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '@ip'),
    # 端口: :8080 等 (必须在通用数字之前)
    (re.compile(r':\d{4,5}\b'), ':@p'),
    # 常见文件名.ext: config.json, app.py, main.go (必须在通用数字之前)
    (re.compile(r'\b\w+\.(json|yaml|yml|py|txt|csv|xml|html?|js|ts|go|java|cpp?|h|md|ini|cfg|toml|env|log|sql|sh|bat|ps1|cfg|conf|key|crt|pem)\b', re.IGNORECASE), '@f'),
    # 驼峰/下划线变量名 (2个词以上)
    (re.compile(r'\b[a-z]+[A-Z][a-z]+[A-Za-z]*\b'), '@v'),
    (re.compile(r'\b[a-z]+_[a-z]+_[a-z]+\b'), '@v'),
    # 数字 (2位以上)
    (re.compile(r'\b\d{2,}\b'), '@n'),
    # 引号内的具体内容 (保留引号结构)
    (re.compile(r'"[^"]{3,}"'), '"@s"'),
    (re.compile(r"'[^']{3,}'"), "'@s'"),
    # 代码/错误码: ABC-123, ERR_234, 等 (大写, 2+字母+2+数字)
    (re.compile(r'\b[A-Z]{2,}\d{2,}\b'), '@c'),
    # 大写缩写: 3+ 字母 (如 ABC, ERROR, WARNING)
    (re.compile(r'\b[A-Z]{3,}\b'), '@c'),
]


def _extract_intent(messages, system=None) -> str:
    """
    从 messages 中提取意图签名。

    策略:
    - 保留最后 2 轮 user/assistant 的消息模式
    - 替换具体值 (路径/行号/错误/数字) 为占位符
    - 保留消息结构 (角色+内容框架)

    Returns:
        意图签名字符串，用于 embedding 和 hash
    """
    if not messages:
        return ""

    # 提取最近 2 轮 user/assistant 消息
    recent = []
    seen_roles = set()
    for msg in reversed(messages):
        role = msg.get('role', '')
        if role in ('user', 'assistant'):
            content = msg.get('content', '')
            # 提取文本内容 (content 可能是 list 或 str)
            if isinstance(content, list):
                texts = []
                for block in content:
                    if isinstance(block, dict):
                        texts.append(block.get('text', ''))
                content = ' '.join(texts)
            elif not isinstance(content, str):
                content = str(content)

            recent.append((role, content))
            seen_roles.add(role)
            if len(seen_roles) >= 2 and len(recent) >= 4:
                break

    # 反转回正常顺序
    recent.reverse()

    # 构建原始文本
    parts = []
    if system:
        parts.append(f"sys:{system[:200]}")
    for role, content in recent:
        parts.append(f"{role}:{content[:500]}")

    raw = '\n'.join(parts)

    # 应用占位符替换
    for pattern, replacement in _INTENT_PATTERNS:
        raw = pattern.sub(replacement, raw)

    # 压缩空白
    raw = re.sub(r'\s+', ' ', raw).strip()

    return raw[:1000]  # 限制长度


def _get_last_user_message(messages):
    """获取最后一条 user message 的文本内容"""
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            content = msg.get('content', '')
            if isinstance(content, list):
                texts = []
                for block in content:
                    if isinstance(block, dict):
                        texts.append(block.get('text', ''))
                content = ' '.join(texts)
            elif not isinstance(content, str):
                content = str(content)
            return content
    return ""


# ── Char N-Gram Embedding (方案A 降级方案) ──

def _char_ngram_embedding(text, n_min=2, n_max=5):
    """
    字符 n-gram embedding，返回稀疏向量 (dict of gram->tf)。
    对短文本 (<200 chars) 效果较好，适合 intent 签名。
    n=2-5 覆盖 unigram-4gram，较好的语义分离度。
    """
    if not text:
        return {}
    grams = {}
    text_lower = text.lower()
    for n in range(n_min, n_max + 1):
        for i in range(len(text_lower) - n + 1):
            gram = text_lower[i:i + n]
            grams[gram] = grams.get(gram, 0) + 1
    # TF 归一化 (子线性 + IDF 模拟)
    total = sum(grams.values())
    if total > 0:
        n_grams = len(grams)
        for k in grams:
            # 长 n-gram 权重更高 (区分度更好)
            length_bonus = 1.0 + 0.2 * (len(k) - 2)
            grams[k] = length_bonus * (1.0 + np.log1p(grams[k]))
    return grams


def _cosine_similarity_dict(a, b):
    """两个 dict 表示的稀疏向量的余弦相似度"""
    if not a or not b:
        return 0.0
    all_keys = set(a.keys()) | set(b.keys())
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for k in all_keys:
        va = a.get(k, 0.0)
        vb = b.get(k, 0.0)
        dot += va * vb
        norm_a += va * va
        norm_b += vb * vb
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (np.sqrt(norm_a) * np.sqrt(norm_b))


# ── 主缓存类 ──

class SemanticCache:
    """
    语义缓存 — 用 embedding 相似度匹配 LLM 请求。

    支持两种 embedding 后端:
    1. sentence-transformers (更精确, 需安装)
    2. char n-gram + numpy (无额外依赖, 已内建)

    用法:
        cache = SemanticCache(threshold=0.92)
        result = cache.lookup(messages, system, model)
        if result is None:
            response = llm_call(...)
            cache.store(messages, system, model, response)
    """

    def __init__(self, max_entries=200, threshold=None):
        """
        Args:
            max_entries: 最大缓存条目数
            threshold: 语义相似度阈值。
                - None: 自动选择 (sentence-transformers: 0.88, char-gram: 0.70)
                - float: 手动指定
        """
        self.max_entries = max_entries
        # 自动检测阈值
        if threshold is not None:
            self.threshold = threshold
        elif _USE_SENTENCE_TRANSFORMERS:
            self.threshold = 0.88
        else:
            self.threshold = 0.70  # char-gram 的区分度较低
        # entries: [(intent_signature, embedding_dict_or_array, response_tuple, timestamp)]
        self.entries = []
        # LRU 顺序
        self._lru = OrderedDict()

        # 统计
        self.hits = 0
        self.misses = 0
        self.stores = 0
        self.evicts = 0

        # 加载 sentence model (如果可用)
        if _USE_SENTENCE_TRANSFORMERS:
            _get_sentence_model()

    def _get_embedding(self, text):
        """获取文本的 embedding 向量"""
        if _USE_SENTENCE_TRANSFORMERS and _sentence_model is not None:
            # sentence-transformers 返回 numpy array
            try:
                emb = _sentence_model.encode(text, show_progress_bar=False)
                return emb
            except Exception as e:
                logger.warning("semantic_cache: sentence-transformers encode failed: %s", e)
                # 降级到 char n-gram
        return _char_ngram_embedding(text)

    def _cosine_similarity(self, a, b):
        """计算两个 embedding 的余弦相似度"""
        if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
            # numpy array
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b))
        else:
            # dict (char n-gram)
            return _cosine_similarity_dict(a, b)

    def lookup(self, messages, system=None, model=None):
        """
        语义查找缓存。

        Args:
            messages: 消息列表
            system: 系统提示
            model: 模型名

        Returns:
            (response_chunks, similarity_score) 或 None
        """
        try:
            intent = _extract_intent(messages, system)
            if not intent:
                self.misses += 1
                return None

            embedding = self._get_embedding(intent)

            best_match = None
            best_sim = 0.0

            for i, (stored_intent, stored_emb, response, _ts) in enumerate(self.entries):
                sim = self._cosine_similarity(embedding, stored_emb)
                if sim > best_sim:
                    best_sim = sim
                    best_match = i

            if best_match is not None and best_sim >= self.threshold:
                self.hits += 1
                # LRU: 移到末尾
                entry = self.entries.pop(best_match)
                self.entries.append(entry)
                return entry[2], best_sim

            self.misses += 1
            return None

        except Exception as e:
            logger.warning("semantic_cache lookup error: %s", e)
            self.misses += 1
            return None

    def store(self, messages, system, model, response_chunks):
        """
        存储响应到语义缓存。

        Args:
            messages: 消息列表 (用于提取意图)
            system: 系统提示
            model: 模型名
            response_chunks: 响应 chunks (tuple)
        """
        try:
            intent = _extract_intent(messages, system)
            if not intent or not response_chunks:
                return

            # 意图 + 模型作为缓存区分
            cache_key = f"{intent}||model={model or 'default'}"

            # 检查是否已存在 (用精确 hash 去重)
            key_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
            for i, (si, _, _, _) in enumerate(self.entries):
                if hashlib.sha256(f"{si}||model={model or 'default'}".encode()).hexdigest()[:16] == key_hash:
                    # 已存在，更新 LRU 位置
                    entry = self.entries.pop(i)
                    self.entries.append(entry)
                    return

            embedding = self._get_embedding(intent)

            # LRU 淘汰
            if len(self.entries) >= self.max_entries:
                self.entries.pop(0)
                self.evicts += 1

            self.entries.append((intent, embedding, tuple(response_chunks), time.time()))
            self.stores += 1

        except Exception as e:
            logger.warning("semantic_cache store error: %s", e)

    def get_stats(self):
        """获取缓存统计"""
        total = self.hits + self.misses
        rate = f"{self.hits / total * 100:.1f}%" if total else "N/A"
        return {
            'semantic_hit': self.hits,
            'semantic_miss': self.misses,
            'semantic_rate': rate,
            'semantic_store': self.stores,
            'semantic_evict': self.evicts,
            'semantic_size': len(self.entries),
        }

    def get_stats_str(self):
        """获取统计字符串 (与 _cache_stats_str 格式兼容)"""
        s = self.get_stats()
        total = s['semantic_hit'] + s['semantic_miss']
        return (f"semantic_hit={s['semantic_hit']} semantic_miss={s['semantic_miss']} "
                f"semantic_rate={s['semantic_rate']} store={s['semantic_store']} "
                f"evict={s['semantic_evict']} size={s['semantic_size']}")


# ── 全局实例 ──

_SEMANTIC_CACHE_INSTANCE = None


def get_semantic_cache(threshold=0.92, max_entries=200):
    """获取/创建全局语义缓存实例"""
    global _SEMANTIC_CACHE_INSTANCE
    if _SEMANTIC_CACHE_INSTANCE is None:
        _SEMANTIC_CACHE_INSTANCE = SemanticCache(
            max_entries=max_entries,
            threshold=threshold,
        )
    return _SEMANTIC_CACHE_INSTANCE


# ── 测试 ──

def _demo():
    """简单的功能验证"""
    cache = SemanticCache(threshold=0.85, max_entries=10)

    # 测试1: 意图提取
    msgs1 = [
        {"role": "user", "content": "搜索文件 D:\\projects\\test.txt 第 42 行 error code ABC-123"}
    ]
    intent1 = _extract_intent(msgs1, "你是助手")
    print(f"意图1: {intent1}")

    msgs2 = [
        {"role": "user", "content": "搜索文件 C:\\data\\config.json 第 99 行 warning code XYZ-789"}
    ]
    intent2 = _extract_intent(msgs2, "你是助手")
    print(f"意图2: {intent2}")

    # 测试2: 相似意图应命中
    response = ("这是搜索结果",)
    cache.store(msgs1, "你是助手", "claude-3", response)
    result = cache.lookup(msgs2, "你是助手", "claude-3")
    if result:
        print(f"命中! 相似度={result[1]:.3f}")
    else:
        print("未命中 (阈值可能过高)")

    # 测试3: 不同意图不应命中
    msgs3 = [
        {"role": "user", "content": "帮我写一首关于春天的诗"}
    ]
    result = cache.lookup(msgs3, "你是助手", "claude-3")
    if result:
        print(f"误命中! 相似度={result[1]:.3f}")
    else:
        print("正确拒绝不同意图")

    print(f"\n统计: {cache.get_stats_str()}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    _demo()
