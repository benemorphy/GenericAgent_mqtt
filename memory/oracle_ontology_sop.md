# 甲骨文本体 SOP

## 项目位置
`knowledge/oracle_ontology/`

## 文件结构

| 文件 | 说明 |
|------|------|
| `oracle_ontology.ttl` | RDF/Turtle 本体数据，187 三元组 |
| `query.py` | 查询接口：按字/按构件/按时代查询 |
| `schema.py` | 数据库连接配置（预留 Neo4j） |
| `__init__.py` | 包初始化 |

## 本体架构：四层模型

```
Glyph(字形层) → realizes → Grapheme(字位层) → denotes → Sense(语义层)
  ↑ composes
Component(构件层)
```

辅助类: Era(时代), Region(地域), Inscription(甲骨片), Controversy(争议)

## 当前数据

- 10 个基础甲骨文（日/月/山/水/雨/王/贞/卜/田/年）
- 包含异体关系（王字两种写法）
- 包含争议节点示例

## 查询用法

```bash
cd knowledge/oracle_ontology
python query.py                           # 统计 + 列出全部
python query.py --char 雨                 # 查单个字
python query.py --component 人            # 按构件查字
python query.py --era 武丁               # 按时代查字
```

## 后续扩展方向

1. 扩充到 200 个常用甲骨文（Agent A 方向）
2. 导入辞例共现关系（Agent B 方向）
3. 对接 Neo4j（密码需确认）
4. 构建 CV 候选过滤管道（Agent C 方向）
