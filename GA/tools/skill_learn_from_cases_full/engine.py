"""
engine.py -- skill_learn_from_cases 核心引擎

5 阶段流程编排：
  Phase 0: 启动 + 目录创建
  Phase 1: 技能定义（skill_search 查前置知识）
  Phase 2: 案例搜索（skill_search + Web Search）
  Phase 3: 分析提炼知识模式
  Phase 4: 构建验证工具
  Phase 5: 运行验证 -> 出报告
"""

import sys
import os
import json
import subprocess
from pathlib import Path

# -- 项目路径 --
GA_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(GA_ROOT))
sys.path.insert(0, str(GA_ROOT / "memory" / "skill_search"))

# -- 自动启用LLM（从本地API密钥配置加载）--
if not os.environ.get("SKILL_LLM_ENABLE"):
    try:
        from tools.utils.config_service import ConfigService
        cfg = ConfigService.instance().get('native_oai_config') or {}
        if cfg and cfg.get('apikey') and cfg.get('apibase'):
            os.environ.setdefault("SKILL_LLM_ENABLE", "1")
            os.environ.setdefault("LLM_API_BASE", cfg['apibase'].rstrip('/'))
            os.environ.setdefault("LLM_API_KEY", cfg['apikey'])
            os.environ.setdefault("LLM_MODEL", cfg.get('model', 'gpt-4'))
            os.environ.setdefault("LLM_TIMEOUT", "120")
    except Exception:
        pass  # mykey不存在或无可用配置，LLM不启用

from tools.skill_learn_from_cases_full import dir_manager
from tools.skill_learn_from_cases_full.restore_funcs import _import_skill_search, _import_web_search, _web_search_wikipedia
from tools.skill_learn_from_cases_full.llm_helper import call_llm_json, llm_available


def _detect_docker():
    """检测 Docker 是否可用"""
    try:
        r = subprocess.run(
            ["wsl.exe", "--exec", "bash", "-c", "docker --version 2>/dev/null"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and r.stdout.strip():
            ver = r.stdout.strip()
            print(f"  Docker: [OK] {ver}")
            return ver
    except Exception:
        pass

    
    return None


def _phase0_bootstrap(skill_name: str) -> dict:
    """启动环境 + 创建 revN 目录"""
    print(f"\n{'='*55}")
    print(f"  skill_learn_from_cases(\"{skill_name}\")")
    print(f"{'='*55}")

    # 已有版本
    versions = dir_manager.get_versions(skill_name)
    if versions:
        print(f"  已有版本: rev{', rev'.join(map(str, versions))}")
    else:
        print("  新技能，无历史版本")

    # 创建新目录
    ver = dir_manager.next_version(skill_name)
    rev_dir = dir_manager.create_revision_dir(skill_name, ver)
    print(f"  创建: rev{ver}/")

    # 继承上一版模式
    inherited_patterns = dir_manager.get_latest_patterns(skill_name)
    if inherited_patterns:
        patterns_file = rev_dir / "patterns" / "knowledge_patterns.json"
        with open(patterns_file, "w", encoding="utf-8") as f:
            json.dump(inherited_patterns, f, indent=2, ensure_ascii=False)
        print(f"  继承: {len(inherited_patterns)} 个知识模式")
    else:
        print("  无继承模式")

    # 探测 Docker
    docker_ver = _detect_docker()
    if docker_ver:
        print(f"  Docker: [OK] {docker_ver}")
    else:
        print("  Docker: [FAIL] 不可用（compose 语法校验将跳过）")

    return {
        "skill_name": skill_name,
        "version": ver,
        "rev_dir": rev_dir,
        "docker_ver": docker_ver,
        "inherited_patterns": inherited_patterns
    }


# ===============================================================
# Phase 1: 技能定义
# ===============================================================

def _llm_enrich_definition(ctx: dict, name_clean: str):
    """
    使用 LLM 丰富技能定义：生成结构化定义、前置知识、核心概念、常见陷阱。
    仅增强，不破坏已有字段。
    """
    prompt = f"""技能名称: {name_clean}

请为这个技能生成一份结构化学习定义，包含以下字段（JSON 格式）：
1. description: 一段精炼的简介（100-200字），面向想学习该技能的开发者
2. prerequisites: 前置知识列表（数组，每项含 name 和 reason 字段）
3. core_concepts: 3-6个核心概念/知识点
4. common_pitfalls: 3-5个常见错误/陷阱（每项含 pitfall 和 advice 字段）

当前已有描述: {ctx['skill_definition'].get('description','')}

请以 JSON 格式输出，strict 模式：
{{"description": "...", "prerequisites": [{{"name": "docker", "reason": "容器化基础"}}], "core_concepts": ["..."], "common_pitfalls": [{{"pitfall": "...", "advice": "..."}}]}}
"""

    result = call_llm_json(prompt,
        system_prompt="你是技术技能学习专家，擅长生成结构化、可操作的学习定义。输出纯 JSON。",
        temperature=0.3,
        max_tokens=4096)

    if not isinstance(result, dict):
        return

    # 增强描述（如果 LLM 返回的描述更长更好）
    if result.get("description") and len(result["description"]) > len(ctx["skill_definition"].get("description", "")):
        ctx["skill_definition"]["description"] = result["description"][:500]

    # 前置知识
    if result.get("prerequisites"):
        ctx["skill_definition"]["prerequisites"] = result["prerequisites"]

    # 核心概念
    if result.get("core_concepts"):
        ctx["skill_definition"]["core_concepts"] = result["core_concepts"]

    # 常见陷阱
    if result.get("common_pitfalls"):
        ctx["skill_definition"]["common_pitfalls"] = result["common_pitfalls"]

    print(f"  [LLM] 定义增强: 前置知识 {len(result.get('prerequisites',[]))} 项, "
          f"核心概念 {len(result.get('core_concepts',[]))} 项, "
          f"常见陷阱 {len(result.get('common_pitfalls',[]))} 项")


def _phase1_define(ctx: dict):
    """定义技能：查 skill hub 获取前置知识"""
    print(f"\n{'-'*55}")
    print("  Phase 1: 技能定义")
    print(f"{'-'*55}")

    # 从技能名称推断
    name_clean = ctx["skill_name"].replace("_", " ").title()
    ctx["skill_definition"] = {
        "name": ctx["skill_name"],
        "display_name": name_clean,
        "prerequisites": [],
        "description": f"通过案例学习 {name_clean}",
    }
    print(f"  技能: {name_clean}")

    # 尝试用 skill_search 获取更精确的定义
    search_fn = _import_skill_search()
    if search_fn:
        try:
            results = search_fn(name_clean, top_k=3)
            if results:
                tags = []
                for r in results:
                    if hasattr(r, 'skill') and hasattr(r.skill, 'tags'):
                        tags.extend(r.skill.tags or [])
                    desc = getattr(r, 'skill', None)
                    if desc and getattr(desc, 'description', None):
                        ctx["skill_definition"]["description"] = desc.description[:200]
                ctx["skill_definition"]["related_tags"] = list(set(tags))[:10]
                print(f"  Skill Hub: {len(results)} 条相关技能卡")
        except Exception as e:
            print(f"  Skill Hub: [!] {e}")
    
    # 尝试用 Web 搜索增强定义（含 Wikipedia fallback）
    web_fn = _import_web_search()
    wiki_fn = None
    try:
        from tools.skill_learn_from_cases.engine import _web_search_wikipedia as wiki_fn
    except Exception:
        pass
    snippets = []
    if web_fn:
        try:
            web_results = web_fn(keyword=name_clean, size=3)
            if web_results and isinstance(web_results, list):
                for r in web_results[:3]:
                    s = r.get("snippet", "") or r.get("summary", "") or ""
                    if s:
                        snippets.append(s[:200])
                if snippets:
                    brief = "；".join(snippets)[:300]
                    ctx["skill_definition"]["description"] = brief
                    ctx["skill_definition"]["web_summary"] = brief
                    print(f"  Web 摘要: {len(snippets)} 条")
        except Exception:
            pass
    
    # ── 搜索引擎无结果时，Wikipedia 降级 ├────
    if not snippets and wiki_fn:
        try:
            wiki_results = wiki_fn(keyword=name_clean, size=3)
            if wiki_results:
                valid_snippets = []
                for r in wiki_results[:3]:
                    s = r.get("snippet", "") or ""
                    if s:
                        # 过滤无关结果（如产品介绍而非技能描述）
                        s_lower = s.lower()
                        skill_words = set(name_clean.lower().split())
                        s_words = set(s_lower.split())
                        word_overlap = s_words & skill_words
                        irr_signals = ["was a", "is a ", "corporation", "inc.", "company",
                                        "is a web", "is a software", "is a service"]
                        irr_count = sum(1 for sig in irr_signals if sig in s_lower)
                        if irr_count >= 1 and len(word_overlap) <= 1:
                            print(f"  [WIKI跳过] 不相关: {s[:60]}...")
                            continue
                        valid_snippets.append(s[:200])
                snippets = valid_snippets
                if snippets:
                    brief = "；".join(snippets)[:300]
                    ctx["skill_definition"]["wiki_summary"] = brief
                    ctx["skill_definition"]["description"] = brief
                    print(f"  Wikipedia 摘要: {len(snippets)} 条")
        except Exception:
            pass

    # ── LLM 增强：丰富技能定义 ──
    if llm_available():
        _llm_enrich_definition(ctx, name_clean)

    # 写入定义
    def_file = ctx["rev_dir"] / "reports" / "skill_definition.json"
    with open(def_file, "w", encoding="utf-8") as f:
        json.dump(ctx["skill_definition"], f, indent=2, ensure_ascii=False)
    print("  [OK] 定义已保存")


# ===============================================================
# Phase 2: 案例搜索
# ===============================================================

def _llm_generate_search_queries(skill_name: str) -> list[str] | None:
    """
    使用 LLM 生成多样化搜索查询词。
    返回查询列表或 None（降级到硬编码查询）。
    """
    if not llm_available():
        return None

    name = skill_name.replace("_", " ").title()
    has_cjk = any('\u4e00' <= c <= '\u9fff' for c in skill_name)

    prompt = f"""技能名称: {skill_name}
显示名: {name}
包含中文: {'是' if has_cjk else '否'}

请为搜索该技能的学习案例，生成 4~6 个多样化的搜索查询词。
要求：
1. 覆盖不同角度：最佳实践、技术方案、实战经验、常见陷阱
2. 中英文混合策略：{'同时生成中文和英文查询' if has_cjk else '全英文查询'}
3. 如果技能有特定产品/框架名，优先使用原名
4. 每个查询应能搜到不同的内容类型

请以 JSON 数组输出，如 ["查询1", "查询2", ...]
"""

    result = call_llm_json(prompt,
        system_prompt="你是一个搜索引擎优化专家，擅长为技能学习生成高效的搜索查询。输出纯 JSON 数组。",
        temperature=0.5,
        max_tokens=2048)

    if isinstance(result, list) and len(result) >= 2:
        valid = [str(q) for q in result if len(str(q)) > 5][:8]
        if valid:
            print(f"  [LLM] 搜索词: {len(valid)} 个")
            for q in valid:
                print(f"    - {q}")
            return valid
    return None


def _phase2_search(ctx: dict):
    """双渠道搜索案例（编排版）"""
    print(f"\n{'-'*55}")
    print("  Phase 2: 案例搜索")
    print(f"{'-'*55}")

    all_cases = []

    # 渠道 A: Skill Hub
    hub_cases = _search_skill_hub(ctx)
    all_cases += hub_cases

    # 渠道 B: Web 搜索
    web_cases = _search_web(ctx)
    all_cases += web_cases

    # 渠道 C: Sophub
    sophub_cases = _search_sophub(ctx)
    all_cases += sophub_cases

    # 继承上一版案例（如果有）
    inherited = ctx.get("inherited_cases", [])
    if inherited:
        all_cases += inherited
        print(f"  [继承] {len(inherited)} 个案例")

    # 去重
    seen = set()
    unique = []
    for c in all_cases:
        key = c.get("url", "") or c.get("title", "")
        if key not in seen:
            seen.add(key)
            unique.append(c)

    print(f"  Phase 2 完成: {len(unique)} 个案例 (来自 {len(all_cases)} 总)")
    ctx["cases"] = unique
    return unique
def _decompose_skill_name(skill_name: str, cases: list) -> list:
    """将技能名分解为子主题，生成初始模式（0案例fallback用）"""
    if not cases:
        cases = []
    
    # 从技能名称中提取有意义片段
    words = skill_name.replace("_", " ").replace("-", " ")
    # 对中文名按语义切分
    parts = []
    buf = ""
    for ch in words:
        if '\u4e00' <= ch <= '\u9fff':
            if buf and not any('\u4e00' <= c <= '\u9fff' for c in buf):
                parts.append(buf.strip())
                buf = ""
            buf += ch
        elif ch == ' ':
            if buf:
                parts.append(buf.strip())
                buf = ""
        else:
            buf += ch
    if buf:
        parts.append(buf.strip())
    parts = [p for p in parts if len(p) > 1]
    
    # 基于常见技能后缀生成子主题模板映射
    topic_map = {
        # ── wiki/知识库/搜索 ──
        "wiki": "Wiki系统搭建与内容管理最佳实践",
        "search": "搜索算法与检索排序优化策略",
        "搜索": "搜索算法与检索排序优化策略",
        "文档": "文档结构化解析与关键信息提取",
        "知识库": "知识库构建与知识管理最佳实践",
        "knowledge": "知识库构建与知识管理最佳实践",
        "documentation": "文档编写与API文档自动化工具链",
        "doc": "文档编写与API文档自动化工具链",
        # ── 图像/凭证 ──
        "图像": "图像采集与预处理最佳实践",
        "图片": "图像采集与预处理最佳实践",
        "凭证": "凭证标准化与格式校验规范",
        "证件": "凭证标准化与格式校验规范",
        "鉴定": "鉴定流程与判定标准",
        "验证": "验证流程与防篡改机制",
        "识别": "识别算法选型与准确率优化",
        "检测": "异常检测与告警阈值设定",
        "审核": "审核流程自动化与风控策略",
        "审查": "审核流程自动化与风控策略",
        "贷款": "贷款业务场景与合规要求",
        "信贷": "贷款业务场景与合规要求",
        "金融": "金融级安全与数据隐私保护",
        "风控": "金融级安全与数据隐私保护",
        "OCR": "OCR识别与文字提取技术选型",
        "ocr": "OCR识别与文字提取技术选型",
        "防伪": "防伪特征检测与真伪鉴别",
        "篡改": "图像篡改检测与完整性校验",
        "安全": "安全防护与数据隐私合规",
        "合规": "合规审查与审计追溯",
        "小微": "小微金融业务风控体系",
        "文档": "文档结构化解析与关键信息提取",
        "合同": "合同关键条款抽取与比对",
        "报表": "报表自动生成与数据可视化",
        "签名": "电子签名与数字证书验证",
        "水印": "水印检测与防伪溯源",
        "卫星": "卫星影像几何校正与预处理",
        "遥感": "多光谱遥感数据分析与解译",
        "无人机": "无人机影像处理与拼接",
        "航拍": "航拍影像三维重建与正射校正",
        "SAR": "SAR雷达影像处理与目标识别",
        "雷达": "SAR雷达影像处理与目标识别",
        "光谱": "光谱分析在地物分类中的应用",
        "测绘": "测绘数据标准化与地图制图",
        "地理": "地理空间分析与GIS集成",
        "像素": "像素级影像融合与分辨率增强",
        "neo4j": "Neo4j图数据库建模与Cypher查询",
        "cypher": "Cypher查询语言核心语法与模式匹配",
        "图数据": "图数据建模与路径查询优化",
        "图查询": "图查询语言与遍历算法",
        "节点": "图数据库节点类型与属性设计",
        "关系": "图数据库关系建模与关联分析",
        "知识图谱": "知识图谱构建与图数据库存储",
        "图算法": "图算法在路径分析与社区发现中的应用",
    }
    
    sub_patterns = []
    seen = set()
    for part in parts:
        for keyword, pattern_text in topic_map.items():
            if keyword in part or keyword in skill_name:
                if keyword not in seen:
                    seen.add(keyword)
                    sub_patterns.append((f"{pattern_text}（{skill_name[:20]}）", 78))
    
    # 从案例标题/摘要中提取关键词，新增为低置信度模式
    case_keywords_found = set()
    for c in cases:
        text = (c.get("title","") + " " + c.get("snippet","")).lower()
        # 提取案例中的技术/业务关键词
        for tech_term in ["ocr","深度学习","cnn","数字签名","哈希校验",
                          "篡改检测","防伪","水印","合规","审计",
                          "风控","信用","评估","识别率","准确率",
                          "卫星","遥感","光谱","雷达","sar","gis",
                          "变化检测","目标检测","语义分割","像素",
                          "多光谱","高光谱","无人机","航拍","配准",
                          "neo4j","cypher","图数据库","知识图谱",
                          "图算法","图查询","图遍历","节点","关系",
                          "wiki","wikidata","wikipedia","sparql",
                          "搜索","检索","搜索引擎","ranking",
                          "api","rest","http","爬虫","crawler"]:
            if tech_term in text and tech_term not in seen:
                case_keywords_found.add(tech_term)
    
    for kw in case_keywords_found:
        sub_patterns.append((f"{kw}相关技术与最佳实践（{skill_name[:20]}）", 72))
        seen.add(kw)
    
    # 如果找不到匹配，生成通用结构
    if not sub_patterns:
        generic_subs = [
            f"{skill_name[:30]}核心概念与术语体系",
            f"{skill_name[:30]}常见场景与解决方案",
            f"{skill_name[:30]}工具链与环境搭建",
        ]
        sub_patterns = [(s, 70) for s in generic_subs]
    
    return sub_patterns[:5]

def _extract_patterns_from_cases(cases, skill_name):
    """从案例中提取知识模式（编排版）"""
    if not cases:
        return []

    generic = _load_generic_patterns()
    domain = _load_skill_domain_patterns(skill_name)
    all_patterns = generic + domain

    matched = _match_patterns_to_cases(cases, all_patterns)
    scored = _score_and_rank_patterns(matched, skill_name)

    if not scored:
        print("  [WARN] 未匹配到任何模式")
        return []

    print(f"  {len(scored)} 个模式匹配 (来源于 {len(generic)} 通用 + {len(domain)} 领域)")
    return scored
def _llm_extract_patterns(cases: list[dict], skill_name: str) -> list[dict] | None:
    """
    使用 LLM 从案例中提取知识模式。

    返回 patterns 列表（每个含 id/principle/confidence/level），
    LLM 不可用或解析失败时返回 None（触发 fallback）。
    """
    if not llm_available():
        return None

    # 构造案例摘要（控制 token 量）
    case_summaries = []
    for c in cases[:12]:  # 最多 12 条，控制成本
        title = c.get("title") or c.get("key") or "?"
        snippet = c.get("snippet") or c.get("description") or ""
        case_summaries.append(f"- [{title}] {snippet[:200]}")

    case_text = "\n".join(case_summaries)

    prompt = f"""技能名称: {skill_name}

请分析以下案例，提取该技能领域的核心知识模式（最佳实践/原则/规范）。

要求:
1. 每个模式包含: id(如"P_xxx"), principle(具体原则描述), confidence(0-100,基于案例支持度), level("domain"或"advanced")
2. 从案例真实内容中提炼，不要凭空编造
3. 模式应该具有实践指导意义，不泛泛而谈
4. 如果案例不足，可以适度基于领域常识补充，但降低 confidence

案例：
{case_text}

请以 JSON 数组格式输出，每个元素: {{"id": "P_xxx", "principle": "...", "confidence": 85, "level": "domain"}}
"""

    result = call_llm_json(prompt,
        system_prompt="你是技能学习专家，擅长从案例中提炼可操作的实践模式。输出纯 JSON 数组，不要额外说明。",
        temperature=0.3,
        max_tokens=4096)

    if result is None:
        return None
    if isinstance(result, list):
        # 验证结构
        valid = []
        for item in result:
            if isinstance(item, dict) and "id" in item and "principle" in item:
                item.setdefault("confidence", 75)
                item.setdefault("level", "domain")
                valid.append(item)
        if valid:
            print(f"  [LLM] 智能模式提取: {len(valid)} 个模式")
            return valid
    return None


def _llm_decompose_skill_name(skill_name: str, cases: list) -> list | None:
    """
    使用 LLM 将技能名分解为子主题（当没有案例时的 fallback 改进）。
    返回 [(子主题, 置信度), ...] 或 None。
    """
    if not llm_available():
        return None

    name_clean = skill_name.replace("_", " ").title()
    case_titles = []
    for c in (cases or [])[:8]:
        case_titles.append(c.get("title", "?") or c.get("key", "?"))

    case_hint = "\n".join(f"- {t}" for t in case_titles) if case_titles else "（暂无案例）"

    prompt = f"""技能名称: {name_clean}

请将这个技能分解为 3~5 个子主题（sub-topics），每个子主题代表该领域的一个重要实践方向。
子主题应该是可操作的、有区分度的，而非空泛概念。

参考案例标题：
{case_hint}

请以 JSON 数组格式输出，每个元素: {{"topic": "子主题名称（含简要说明）", "confidence": 78}}
confidence 表示该子主题与技能的相关程度（0-100）。
"""

    result = call_llm_json(prompt,
        system_prompt="你是技能学习专家，善于将复杂技能拆解为可学习的子主题。输出纯 JSON 数组。",
        temperature=0.3,
        max_tokens=2048)

    if isinstance(result, list) and result:
        subs = []
        for item in result:
            if isinstance(item, dict) and "topic" in item:
                conf = item.get("confidence", 70)
                subs.append((item["topic"], conf))
        if subs:
            print(f"  [LLM] 技能分解: {len(subs)} 个子主题")
            return subs
    return None


def _llm_enhance_patterns(patterns, skill_name):
    """LLM 增强模式提取 — 可能返回 None"""
    llm_available = os.environ.get("SKILL_LLM_ENABLE") == "1"
    if llm_available:
        try:
            from tools.llm_providers import chat
            prompt = f"""分析以下技能的模式提取结果，补充遗漏的重要模式。
技能: {skill_name}
当前模式: {json.dumps(patterns, indent=2, ensure_ascii=False)}
请返回 JSON 数组，每个元素包含 principle, id, confidence, category 字段。
只返回 JSON，不要解释。"""
            resp = chat(prompt)
            if resp:
                extra = json.loads(resp)
                if isinstance(extra, list):
                    return patterns + extra
        except Exception:
            pass
    return patterns


def _merge_inherited_patterns(ctx, patterns):
    """合并继承的模式，过滤不相关的领域模式"""
    existing = ctx.get("inherited_patterns", [])
    if not existing:
        return patterns
    
    skill_lower = ctx["skill_name"].lower()
    merged = list(patterns)
    filtered = 0
    
    for p in existing:
        pid = p.get("id", "")
        # 通用模式总是保留
        if any(pid.startswith(pre) for pre in ["P_pin_", "P_env_", "P_res_"]):
            merged.append(p)
            continue
        # 领域相关模式
        for kw, prefixes in SKILL_DOMAIN_PREFIXES.items():
            if kw in skill_lower and any(pid.startswith(pre) for pre in prefixes):
                merged.append(p)
                break
        else:
            filtered += 1
    
    # 限前5个
    if len(merged) > 5:
        print(f"  [继承] 保留 {len(merged)} 个模式 (过滤 {filtered} 个不相关)")
    return merged[:5]


def _phase3_analyze(ctx: dict):
    """Phase 3: 分析提炼知识模式（编排版）"""
    print(f"\n{'-'*55}")
    print("  Phase 3: 模式提炼")
    print(f"{'-'*55}")

    cases = ctx.get("cases", [])
    skill_name = ctx["skill_name"]

    # 规则路径提取模式
    patterns = _extract_patterns_from_cases(cases, skill_name)
    if not patterns:
        patterns = _llm_extract_patterns(cases, skill_name)

    # LLM 增强
    if os.environ.get("SKILL_LLM_ENABLE") == "1":
        patterns = _llm_enhance_patterns(patterns, skill_name)

    # 合并继承的模式
    patterns = _merge_inherited_patterns(ctx, patterns)

    print(f"  模式: {len(patterns)} 条")
    for p in patterns[:5]:
        print(f"    · {p.get('principle', '')[:80]}")
    if len(patterns) > 5:
        print(f"    ... 另有 {len(patterns)-5} 条")

    ctx["patterns"] = patterns
    return patterns
def _phase4_build_tool(ctx: dict):
    """生成验证工具"""
    print(f"\n{'-'*55}")
    print("  Phase 4: 构建验证工具")
    print(f"{'-'*55}")

    patterns = ctx.get("patterns", [])
    patterns_json = json.dumps(patterns, indent=2, ensure_ascii=False)
    case_count = len(ctx.get("cases", []))

    # 从外部模板文件读取
    template_file = Path(__file__).parent / 'assess_template.py'
    tool_code = template_file.read_text(encoding='utf-8')
    tool_code = tool_code.replace("__VERSION__", str(ctx["version"]))
    tool_code = tool_code.replace("__SKILL__", ctx["skill_name"])
    tool_code = tool_code.replace("__SKILL_DISPLAY__",
        ctx.get("skill_definition", {}).get("display_name", ctx["skill_name"]))
    tool_code = tool_code.replace("__PATTERNS_JSON__", patterns_json)
    tool_code = tool_code.replace("__CASE_COUNT__", str(case_count))

    tool_file = ctx["rev_dir"] / "tools" / "assess.py"
    with open(tool_file, "w", encoding="utf-8") as f:
        f.write(tool_code)

    # 语法检查
    try:
        compile(tool_code, str(tool_file), "exec")
        print("  [OK] 工具已创建: tools/assess.py (语法检查通过)")
    except SyntaxError as e:
        print(f"  [!]  工具已创建，但语法检查失败: {e}")

    ctx["tool_file"] = tool_file

    # ── 实践环节：检测所有匹配的 practical hook，复制到 practice/ ──
    skill_lower = ctx["skill_name"].lower()
    hooks_dir = Path(__file__).parent / "practical_hooks"

    # 关键词匹配规则
    hook_rules = [
        ("docker", "docker_compose.py"),
        ("compose", "docker_compose.py"),
        ("container", "docker_compose.py"),
        ("neo4j", "neo4j_hook.py"),
        ("cypher", "neo4j_hook.py"),
        ("graph_database", "neo4j_hook.py"),
        ("图数据库", "neo4j_hook.py"),
        ("sql", "sql.py"),
        ("mysql", "sql.py"),
        ("postgres", "sql.py"),
        ("git", "git.py"),
        ("async", "python_async.py"),   # Python async 技能
        ("asyncio", "python_async.py"),
        ("图像", "document_check.py"),   # 图像/文档鉴权技能
        ("凭证", "document_check.py"),
        ("证件", "document_check.py"),
        ("鉴定", "document_check.py"),
        ("ocr", "document_check.py"),
        ("image", "document_check.py"),
        ("ui", "ui_design_hook.py"),     # UI/UX设计技能 → 设计工具验证
        ("ux", "ui_design_hook.py"),
        ("设计", "ui_design_hook.py"),
        ("prototype", "ui_design_hook.py"),
        ("handoff", "ui_design_hook.py"),
        ("react", "react_hook.py"),
        ("frontend", "react_hook.py"),
        ("hooks", "react_hook.py"),
    ]

    import shutil
    matched_hooks = []
    seen_hooks = set()
    # hook互斥规则：如果特定hook已匹配，则排除其互斥hook
    hook_exclusions = {
        "neo4j_hook.py": ["sql.py", "docker_compose.py"],
        "docker_compose.py": ["sql.py"],
    }
    for keyword, hook_name in hook_rules:
        if keyword in skill_lower and hook_name not in seen_hooks:
            # 互斥检查：如果已匹配的hook排斥当前hook则跳过
            if any(hook_name in excl_list for excl_hook, excl_list in hook_exclusions.items() if excl_hook in seen_hooks):
                continue
            hook_file = hooks_dir / hook_name
            if hook_file.exists():
                seen_hooks.add(hook_name)
                practice_target = ctx["rev_dir"] / "practice" / hook_name
                shutil.copy2(str(hook_file), str(practice_target))
                matched_hooks.append(hook_name)

    ctx["practice_hooks"] = matched_hooks
    ctx["has_practical"] = len(matched_hooks) > 0
    if matched_hooks:
        print(f"  [OK] 实践环节: {', '.join(matched_hooks)}")
    else:
        print("  [OK] 无匹配实践")



# ===============================================================
# Phase 5: 运行验证
# ===============================================================

def _phase5_validate(ctx: dict):
    """运行验证工具"""
    print(f"\n{'-'*55}")
    print("  Phase 5: 运行验证")
    print(f"{'-'*55}")

    tool_file = ctx.get("tool_file")
    if not tool_file or not tool_file.exists():
        print("  [FAIL] 验证工具不存在")
        return

    # 直接在本 Python 进程中运行
    try:
        # 安全：从父进程复制环境变量，过滤掉敏感密钥
        subprocess_env = os.environ.copy()
        # 过滤敏感密钥（仅限 API 密钥和 Token，保留数据库密码供 practical hook 使用）
        _sensitive_suffixes = ("_API_KEY", "_API_SECRET", "_ACCESS_KEY", "_SECRET_KEY", "_AUTH_TOKEN")
        for key in list(subprocess_env.keys()):
            if any(key.upper().endswith(suf) for suf in _sensitive_suffixes):
                del subprocess_env[key]
        # 确保 LLM 变量被传递
        for key in ("SKILL_LLM_ENABLE", "LLM_API_BASE", "LLM_API_KEY", "LLM_MODEL", "LLM_TIMEOUT"):
            if key in os.environ:
                subprocess_env[key] = os.environ[key]
        # GA_ROOT = Path(__file__).resolve().parents[2]
        ga_root = str(Path(__file__).resolve().parents[2])
        subprocess_env.setdefault("PYTHONPATH", "")
        paths = subprocess_env["PYTHONPATH"].split(os.pathsep) if subprocess_env["PYTHONPATH"] else []
        if ga_root not in paths:
            subprocess_env["PYTHONPATH"] = ga_root + os.pathsep + subprocess_env["PYTHONPATH"]
        
        result = subprocess.run(
            [sys.executable, str(tool_file)],
            capture_output=True, text=True, timeout=90,
            env=subprocess_env
        )
        print(result.stdout)
        if result.stderr:
            print(f"  [stderr]: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print("  [!]  验证超时")
    except Exception as e:
        print(f"  [!]  运行失败: {e}")

    # 读取报告
    report_file = ctx["rev_dir"] / "reports" / "assessment.json"
    if report_file.exists():
        with open(report_file, encoding="utf-8") as f:
            report = json.load(f)
        ctx["assessment"] = report
        passed = report.get("passed", False)
        score = report.get("final_score", 0)
        print(f"\n  {'='*55}")
        print(f"  rev{ctx['version']} {'[OK] PASS' if passed else '[FAIL] FAIL'} ({score}/100)")
        print(f"  {'='*55}")

        # 更新 meta.json
        meta_file = ctx["rev_dir"] / "meta.json"
        if meta_file.exists():
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)
            meta["status"] = "passed" if passed else "failed"
            meta["score"] = score
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
    else:
        print("  [!]  未生成验证报告")


# ===============================================================
# 主入口
# ===============================================================

def _extract_url_text(url: str) -> list[dict]:
    """从URL提取文本内容（自动检测WeRead启用翻页提取）"""
    if 'weread.qq.com' in url:
        from tools.skill_learn_from_cases_full.weread_extract import extract_url_cases
        return extract_url_cases(url)
    """从URL提取文本内容，分块返回案例列表"""
    import requests
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.encoding = resp.apparent_encoding
        html_text = resp.text
    except Exception as e:
        print(f"  [URL] ⚠ 请求失败: {e}")
        # 尝试用 urllib 兜底
        import urllib.request
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as r:
                html_text = r.read().decode(r.headers.get_content_charset() or 'utf-8', errors='replace')
        except Exception as e2:
            print(f"  [URL] ⚠ urllib也失败: {e2}")
            return []

    # 简易HTML→文本：提取<p>/<li>/<div>/<h1~6>/<pre>/<code>/<article>/<main>等标签内容
    import re
    # 尝试提取 <article> 或 <main> 内容，否则用body
    body = ""
    m = re.search(r'<article[^>]*>(.*?)</article>', html_text, re.DOTALL | re.IGNORECASE)
    if not m:
        m = re.search(r'<main[^>]*>(.*?)</main>', html_text, re.DOTALL | re.IGNORECASE)
    if not m:
        m = re.search(r'<body[^>]*>(.*?)</body>', html_text, re.DOTALL | re.IGNORECASE)
    if m:
        body = m.group(1)
    else:
        body = html_text

    # 提取文本块
    chunks = []
    # 按段落/标题分割
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'pre', 'code']:
        for m in re.finditer(f'<{tag}[^>]*>(.*?)</{tag}>', body, re.DOTALL | re.IGNORECASE):
            text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if len(text) > 20:  # 过滤过短片段
                chunks.append(text)

    if not chunks:
        # 兜底：暴力去标签
        text = re.sub(r'<[^>]+>', '\n', body)
        text = re.sub(r'\n\s*\n', '\n', text)
        lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 30]
        chunks = lines[:100]  # 最多100段

    # 合并小段为较大案例（每段500~2000字符）
    cases = []
    current = ""
    for chunk in chunks:
        if len(current) + len(chunk) < 2000:
            current += "\n" + chunk if current else chunk
        else:
            if len(current) > 200:
                cases.append(current)
            current = chunk
    if len(current) > 200:
        cases.append(current)

    # 转为标准案例格式
    result = []
    for i, text in enumerate(cases):
        result.append({
            "source": "url",
            "type": "article",
            "key": f"{url}#part{i+1}",
            "description": text[:2000],
            "tags": [],
            "score": 1.0,
            "relevance": "high",
            "title": f"URL摘录 {i+1}"
        })

    print(f"  [URL] 从 {url} 提取 {len(result)} 条案例 ({sum(len(c['description']) for c in result)} chars)")
    return result


def learn_skill(skill_name: str, from_url: str = None):
    """
    案例驱动技能学习完整流程

    用法:
        learn_skill("docker_compose_production")
    """
    ctx = {}

    try:
        ctx = _phase0_bootstrap(skill_name)
        
        # ── 环境探测 (Phase 0.5) ──
        try:
            from tools.skill_learn_from_cases.env_detector import detect_all
            ctx["env"] = detect_all()
            # 如果有可用环境，给用户提示
            available = [k for k,v in ctx["env"].items() if v.get("available")]
            need_auth = [k for k,v in ctx["env"].items() if v.get("url") and not v.get("auth")]
            if available:
                print(f"  [环境] 可用: {', '.join(available)}")
            if need_auth:
                print(f"  [环境] ⚠ 需密码: {', '.join(need_auth)}（设置 {x}_password 环境变量）")
        except Exception as e:
            print(f"  [环境] [!] 探测失败: {e}")
            ctx["env"] = {}
        
        _phase1_define(ctx)

        # ── URL案例注入 (Phase 1.5) ──
        if from_url:
            url_cases = _extract_url_text(from_url)
            if url_cases:
                existing = ctx.get("cases", [])
                ctx["cases"] = existing + url_cases
                print(f"  [注入] 已添加 {len(url_cases)} 条URL案例到案例池")

        _phase2_search(ctx)
        _phase3_analyze(ctx)
        _phase4_build_tool(ctx)
        _phase5_validate(ctx)
    except KeyboardInterrupt:
        print("\n  NO_ENTRY 用户中断")
        return
    except Exception as e:
        print(f"\n  [FAIL] 流程异常: {e}")
        import traceback
        traceback.print_exc()
        return

    # 输出总结
    assessment = ctx.get("assessment", {})
    print(f"\n  [CHART] 总结: rev{ctx.get('version','?')} | "
          f"模式: {len(ctx.get('patterns',[]))}个 | "
          f"评分: {assessment.get('final_score','?')}/100")
    print(f"  目录: {ctx.get('rev_dir','')}")

    # 生成 Markdown 报告
    _generate_markdown_report(ctx)


def _generate_markdown_report(ctx: dict):
    """生成人类可读的 Markdown 学习报告"""
    rev_dir = ctx.get("rev_dir")
    if not rev_dir:
        return
    skill = ctx.get("skill_name", "unknown")
    version = ctx.get("version", 0)
    patterns = ctx.get("patterns", [])
    cases = ctx.get("cases", [])
    assessment = ctx.get("assessment", {})
    score = assessment.get("final_score", 0)
    passed = assessment.get("passed", False)
    inherited = ctx.get("inherited_patterns", [])
    inherited_ids = {p["id"] for p in inherited}
    prev_version = version - 1 if version > 1 else None

    # 分割模式
    domains = [p for p in patterns if p.get("level") == "domain"]
    advanced = [p for p in patterns if p.get("level") == "advanced"]
    basics = [p for p in patterns if p.get("level") == "basic"]
    
    # 区分继承vs新增
    inherited_cnt = sum(1 for p in patterns if p["id"] in inherited_ids)
    new_cnt = len(patterns) - inherited_cnt

    lines = []
    lines.append(f"# 技能学习报告: {skill}")
    lines.append("")
    lines.append("| 属性 | 值 |")
    lines.append("|------|-----|")
    lines.append(f"| 版本 | rev{version} |")
    lines.append(f"| 评分 | {score}/100 {'PASS' if passed else 'FAIL'} |")
    lines.append(f"| 案例数 | {len(cases)} 条 |")
    lines.append(f"| 模式总数 | {len(patterns)} 个 |")
    if prev_version:
        lines.append(f"| 继承自 rev{prev_version} | {inherited_cnt} 个 |")
        lines.append(f"| 新增 | {new_cnt} 个 |")
    lines.append("")
    lines.append("## 知识模式")
    lines.append("")
    if domains:
        lines.append(f"### 领域专有 ({len(domains)}个)")
        for p in sorted(domains, key=lambda x: -x.get("confidence", 0)):
            lines.append(f"- [{p['confidence']}%] {p['principle']}")
        lines.append("")
    if advanced:
        lines.append(f"### 高级模式 ({len(advanced)}个)")
        for p in sorted(advanced, key=lambda x: -x.get("confidence", 0)):
            lines.append(f"- [{p['confidence']}%] {p['principle']}")
        lines.append("")
    if basics:
        lines.append(f"### 基础模式 ({len(basics)}个)")
        for p in sorted(basics, key=lambda x: -x.get("confidence", 0)):
            lines.append(f"- [{p['confidence']}%] {p['principle']}")
        lines.append("")

    # 案例摘要
    if cases:
        lines.append(f"## 参考案例 ({len(cases)}条)")
        lines.append("")
        for c in cases[:10]:
            title = c.get("title", c.get("key", "?"))
            url = c.get("url", "")
            if url:
                lines.append(f"- [{title}]({url})")
            else:
                lines.append(f"- {title}")

    report_path = rev_dir / "reports" / "learning_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("  [OK] 学习报告: reports/learning_report.md")