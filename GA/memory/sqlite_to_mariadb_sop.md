# SQLite -> MariaDB 迁移 SOP

## 前置条件
BoardService 使用 MariaDB (config.DB_CONFIG)，不再使用 SQLite。

## 迁移检查清单（每项都是踩坑验证过的）

### 1. 导入替换
- `sqlite3` -> `pymysql` (保留 `import time`，别误删)
- `sqlite3.IntegrityError` -> `pymysql.err.IntegrityError`

### 2. 连接管理
- `sqlite3.connect(path)` -> `pymysql.connect(**cfg.DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)`
- `check_same_thread=False` -> 去掉（pymysql 不需要）
- 连接对象改为类实例变量（self._mariadb），不要每 board 一个连接
- `_dbs` 从 dict 改为 set（只存 board_key，连接共用）
- 加 `_MariaDBWrapper` 代理类：包装 Connection，提供 `.execute()` 方法（内部创建 cursor）

### 3. SQL 语法转换
- `?` 占位符 -> `%s`
- `time.time()` 时间戳 -> `NOW(3)` / `FROM_UNIXTIME(%s)`
- `cur.lastrowid` -> 兼容（pymysql 也支持）
- `row_factory=sqlite3.Row` -> `cursorclass=DictCursor`（dict 访问兼容）

### 4. 表名与结构
- `users` -> `bbs_users`（加 board 列）
- `posts` -> `bbs_posts`（加 board 列）
- `content` 列类型：MariaDB 用 `LONGTEXT`（不要用 JSON，普通字符串会报错）

### 5. 查询中加 board 过滤
所有 SELECT/INSERT/UPDATE/DELETE 加 `WHERE board=%s` / `board=%s`
否则不同 board 的数据会互相污染并导致重复 key 冲突。

### 6. 返回值处理
- `datetime` 对象 -> 转 ISO 字符串（`v.isoformat()`），否则 JSON 序列化失败
- `DictCursor.fetchone()` 返回 dict（兼容 `row["name"]` 语法）

### 7. 启动顺序
- `start()` 中 `for board_key, bconf in self._boards.items():` 必须同时调用 `_ensure_db()`
- `_load_boards()` 不要自己调 `_ensure_db()`，让 `start()` 统一管理

## 当代码被多次 patch 改乱时的恢复策略
```python
# 不要继续 patch 了！直接 git restore + 干净重做
git checkout <clean_commit> -- Mqtt_bbs/board_service.py
# 然后在一轮内完成全部修改
```

## 已知坑
- file_patch 工具反复出现 Permission denied -> 改用 code_run 直接读写文件
- MariaDB `posts` 表已存在（从之前 RMQTT 持久化遗留），确保 CREATE TABLE IF NOT EXISTS
- 多 board 共享表时必须加 WHERE board=... 过滤
