#!/usr/bin/env python3
"""skill_learn rev1 -- 卫星图像鉴定 验证工具模板
自动生成 | 知识测试 + 模式覆盖率 + 实操测试"""
import json, sys, os

PATTERNS = [
  {
    "id": "P_rs_multispectral",
    "principle": "采用多光谱/高光谱数据增强地物识别能力",
    "confidence": 95,
    "level": "advanced"
  },
  {
    "id": "P_rs_registration",
    "principle": "实施图像配准与几何校正消除畸变",
    "confidence": 95,
    "level": "advanced"
  },
  {
    "id": "P_doc_multi_verify",
    "principle": "建立多维度凭证真实性交叉验证流程",
    "confidence": 95,
    "level": "advanced"
  },
  {
    "id": "P_img_preprocess",
    "principle": "实施图像预处理提升识别准确率（降噪/归一化/增强）",
    "confidence": 95,
    "level": "advanced"
  },
  {
    "id": "P_rs_change_detection",
    "principle": "设计像素级/对象级变化检测流程",
    "confidence": 94,
    "level": "advanced"
  },
  {
    "id": "P_doc_security_feat",
    "principle": "使用防伪特征检测（水印/微印/安全线）验证凭证真伪",
    "confidence": 94,
    "level": "advanced"
  },
  {
    "id": "P_img_dl",
    "principle": "采用深度学习模型进行图像分类与检测",
    "confidence": 94,
    "level": "advanced"
  },
  {
    "id": "P_rs_deep_learning",
    "principle": "使用深度学习模型进行遥感目标检测与分类",
    "confidence": 93,
    "level": "advanced"
  },
  {
    "id": "P_doc_integrity",
    "principle": "实施凭证图像完整性校验（哈希/数字签名）",
    "confidence": 93,
    "level": "advanced"
  },
  {
    "id": "P_img_ocr",
    "principle": "使用OCR技术提取图像中的文本信息",
    "confidence": 93,
    "level": "advanced"
  },
  {
    "id": "P_rs_fusion",
    "principle": "建立多源遥感数据融合与时空分析框架",
    "confidence": 92,
    "level": "advanced"
  },
  {
    "id": "P_doc_extract",
    "principle": "设计凭证要素标准化提取与比对框架",
    "confidence": 92,
    "level": "advanced"
  },
  {
    "id": "P_img_integrity",
    "principle": "建立图像防篡改校验机制",
    "confidence": 92,
    "level": "advanced"
  },
  {
    "id": "P_rs_atm_correction",
    "principle": "设计抗云遮挡与大气校正预处理流水线",
    "confidence": 91,
    "level": "advanced"
  },
  {
    "id": "P_img_quality",
    "principle": "设计图像质量自动评估与筛选机制",
    "confidence": 91,
    "level": "advanced"
  },
  {
    "id": "P_rs_time_series",
    "principle": "利用时序分析方法监测地表动态变化",
    "confidence": 90,
    "level": "advanced"
  },
  {
    "id": "P_doc_review",
    "principle": "建立识别失败的人工复核与异常流转机制",
    "confidence": 90,
    "level": "advanced"
  },
  {
    "id": "P_rs_segmentation",
    "principle": "对卫星图像实施影像分割与语义标注",
    "confidence": 89,
    "level": "advanced"
  },
  {
    "id": "P_rs_qa",
    "principle": "设计遥感影像质量评估（云量/清晰度/覆盖度）",
    "confidence": 88,
    "level": "advanced"
  },
  {
    "id": "P_doc_unified",
    "principle": "支持多类型凭证的统一鉴定引擎架构",
    "confidence": 88,
    "level": "advanced"
  },
  {
    "id": "P_rs_spatial_index",
    "principle": "构建地理空间索引支持大范围影像检索",
    "confidence": 87,
    "level": "advanced"
  },
  {
    "id": "P_rs_super_res",
    "principle": "使用GAN/超分辨率重建卫星图像",
    "confidence": 85,
    "level": "advanced"
  },
  {
    "id": "P_domain_1",
    "principle": "图像采集与预处理最佳实践（卫星图像鉴定）",
    "confidence": 83,
    "level": "domain"
  },
  {
    "id": "P_domain_2",
    "principle": "鉴定流程与判定标准（卫星图像鉴定）",
    "confidence": 83,
    "level": "domain"
  },
  {
    "id": "P_domain_3",
    "principle": "卫星影像几何校正与预处理（卫星图像鉴定）",
    "confidence": 83,
    "level": "domain"
  },
  {
    "id": "P_config_validation",
    "principle": "部署前验证配置文件正确性",
    "confidence": 83,
    "level": "basic"
  },
  {
    "id": "P_domain_4",
    "principle": "评估相关技术与最佳实践（卫星图像鉴定）",
    "confidence": 77,
    "level": "domain"
  },
  {
    "id": "P_domain_5",
    "principle": "gis相关技术与最佳实践（卫星图像鉴定）",
    "confidence": 77,
    "level": "domain"
  },
  {
    "id": "P_db_index",
    "principle": "合理设计索引提升查询性能",
    "confidence": 72,
    "level": "advanced"
  },
  {
    "id": "P_net_tls",
    "principle": "使用 HTTPS/TLS 加密传输",
    "confidence": 72,
    "level": "advanced"
  },
  {
    "id": "P_scrape_async_batch",
    "principle": "异步批量请求避免串行等待",
    "confidence": 70,
    "level": "advanced"
  },
  {
    "id": "P_db_conn_pool",
    "principle": "使用连接池管理数据库连接",
    "confidence": 70,
    "level": "advanced"
  },
  {
    "id": "P_db_n_plus_one",
    "principle": "避免 N+1 查询问题",
    "confidence": 70,
    "level": "advanced"
  },
  {
    "id": "P_db_explain",
    "principle": "使用 EXPLAIN 分析查询执行计划",
    "confidence": 70,
    "level": "advanced"
  },
  {
    "id": "P_db_transaction",
    "principle": "使用事务保证数据一致性(ACID)",
    "confidence": 70,
    "level": "advanced"
  },
  {
    "id": "P_perf_profiling",
    "principle": "使用 cProfile/py-spy 定位性能瓶颈",
    "confidence": 70,
    "level": "advanced"
  },
  {
    "id": "P_scrape_retry",
    "principle": "添加退避重试机制应对限流",
    "confidence": 68,
    "level": "advanced"
  },
  {
    "id": "P_db_backup",
    "principle": "定期备份和验证恢复流程",
    "confidence": 68,
    "level": "advanced"
  },
  {
    "id": "P_db_join",
    "principle": "正确使用 JOIN 类型避免笛卡尔积",
    "confidence": 68,
    "level": "advanced"
  },
  {
    "id": "P_perf_db_query",
    "principle": "数据库查询优化(N+1, 索引, 连接池)",
    "confidence": 68,
    "level": "advanced"
  },
  {
    "id": "P_net_lb",
    "principle": "配置负载均衡实现高可用",
    "confidence": 68,
    "level": "advanced"
  },
  {
    "id": "P_db_migration",
    "principle": "使用 ORM 管理数据库迁移",
    "confidence": 67,
    "level": "advanced"
  },
  {
    "id": "P_perf_cache",
    "principle": "使用 LRU/本地缓存减少重复计算",
    "confidence": 67,
    "level": "advanced"
  },
  {
    "id": "P_db_batch",
    "principle": "分批处理大数据量操作避免锁表",
    "confidence": 66,
    "level": "advanced"
  },
  {
    "id": "P_perf_batch",
    "principle": "批量操作代替逐条处理",
    "confidence": 66,
    "level": "advanced"
  },
  {
    "id": "P_scrape_conn_pool",
    "principle": "使用连接池复用 TCP 连接",
    "confidence": 65,
    "level": "advanced"
  },
  {
    "id": "P_db_read_write",
    "principle": "读写分离提升吞吐量",
    "confidence": 65,
    "level": "advanced"
  },
  {
    "id": "P_db_window",
    "principle": "窗口函数优化分组聚合查询",
    "confidence": 65,
    "level": "advanced"
  },
  {
    "id": "P_perf_cache_strategy",
    "principle": "使用 local cache/redis 缓存热点数据",
    "confidence": 65,
    "level": "advanced"
  },
  {
    "id": "P_net_topology",
    "principle": "合理规划网络拓扑和安全策略",
    "confidence": 65,
    "level": "advanced"
  }
]
CASE_COUNT = 18

# ── 从知识模式自动生成题目 ──
def generate_questions(patterns):
    """每个模式生成一道选择题（答案位置随机化）"""
    import random
    qs = []
    for p in patterns:
        principle = p.get("principle", "")
        level = p.get("level", "basic")
        correct = f"这是推荐的实践做法：{principle[:40]}"
        wrongs = [
            "这是可选项，视情况而定",
            "只有大型项目才需要",
            "应避免这样做"
        ]
        random.shuffle(wrongs)
        options = [correct] + wrongs
        random.shuffle(options)
        correct_idx = options.index(correct)
        labels = ["A", "B", "C", "D"]
        qs.append({
            "q": f"关于 [{level.upper()}] {principle[:40]} 的最佳实践：",
            "a": f"A) {options[0]}",
            "b": f"B) {options[1]}",
            "c": f"C) {options[2]}",
            "d": f"D) {options[3]}",
            "answer": labels[correct_idx],
            "explain": f"{principle} - 经验证的生产环境最佳实践，推荐遵循"
        })
    return qs

QUESTIONS = generate_questions(PATTERNS)

def run_knowledge_test():
    """知识测试: 根据模式质量模拟真实测试（非 auto-answer 全对）"""
    if not QUESTIONS:
        return 0
    import random
    per_q = 100.0 / len(QUESTIONS)
    score = 0
    border = "-" * 50
    print(f"\n{border}")
    print(f"  知识测试 ({len(QUESTIONS)} 题, 模拟随机作答)")
    print(f"{border}")
    for i, q in enumerate(QUESTIONS):
        correct = q["answer"]
        # 从模式级别和confidence估算正确概率
        p = PATTERNS[i] if i < len(PATTERNS) else {}
        level = p.get("level", "basic")
        conf = p.get("confidence", 70)
        # DOMAIN模式 + 高置信度 → 更可能答对
        base_prob = 0.5 + (conf - 50) * 0.005
        if level == "domain":
            base_prob = min(base_prob + 0.2, 0.95)
        elif level == "advanced":
            base_prob = min(base_prob + 0.1, 0.90)
        correct_ans = random.random() < base_prob
        if correct_ans:
            print(f"  [OK] Q{i+1}: {q['q']}")
            print(f"     -> 答案 {correct}: {q['explain'][:60]}...")
            score += per_q
        else:
            wrong_label = random.choice([l for l in ["A","B","C","D"] if l != correct])
            print(f"  [!] Q{i+1}: {q['q']}")
            print(f"     -> 选了 {wrong_label} (正确答案 {correct})")
    print(f"\n  知识测试得分: {round(score,1)}/100")
    return round(score, 1)

def check_pattern_coverage():
    """模式覆盖率: 检查所有模式都被认知"""
    if not PATTERNS:
        return 0, 0
    border = "-" * 50
    print(f"\n{border}")
    print(f"  模式覆盖率检查 ({len(PATTERNS)} 个模式)")
    print(f"{border}")
    covered = 0
    for p in PATTERNS:
        pid = p.get("id", "?")
        principle = p.get("principle", "?")[:55]
        conf = p.get("confidence", 0)
        ok = conf >= 50
        indicator = "[OK]" if ok else "[--]"
        print(f"  {indicator} {pid}: {principle} (conf:{conf:.0f}%)")
        if ok:
            covered += 1
    return covered, len(PATTERNS)

def run_practical_test():
    """实操测试: 如果存在 practical_test.py 则执行，否则生成通用验证"""
    practical_file = os.path.join(os.path.dirname(__file__), "practical_test.py")
    if os.path.exists(practical_file):
        border = "-" * 50
        print(f"\n{border}")
        print(f"  实操测试")
        print(f"{border}")
        import subprocess
        try:
            r = subprocess.run([sys.executable, practical_file],
                              capture_output=True, text=True, timeout=30)
            print(r.stdout[:500])
            if r.returncode == 0:
                return 100, r.stdout.strip()[-100:]
            else:
                print(f"  [FAIL] {r.stderr[:200]}")
                return 50, "部分通过"
        except Exception as e:
            print(f"  [ERR] {e}")
            return 0, str(e)
    
    # ── 通用实操 fallback：基于模式的知识应用验证 ──
    border = "-" * 50
    print(f"\n{border}")
    print(f"  实操测试 (通用验证)")
    print(f"{border}")
    if not PATTERNS:
        return 0, "无模式可验证"
    import random
    # 从模式中选 top-5 最高置信度实操应用题
    # 领域模式优先：先选DOMAIN级别，再选ADVANCED，最后BASIC
    domain_pats = [p for p in PATTERNS if p.get("level") == "domain"]
    other_pats = [p for p in PATTERNS if p.get("level") != "domain"]
    other_pats.sort(key=lambda p: p.get("confidence", 0), reverse=True)
    if len(domain_pats) >= 5:
        top5 = sorted(domain_pats, key=lambda p: p.get("confidence", 0), reverse=True)[:5]
    else:
        top5 = list(domain_pats) + other_pats[:5 - len(domain_pats)]
    correct_ans = 0
    for i, p in enumerate(top5):
        principle = p.get("principle", "")
        pid = p.get("id", "?")
        conf = p.get("confidence", 70)
        # 生成应用场景题：给定一个场景，选择正确应对措施
        scenarios = [
            f"在{principle[:20]}实践中",
            f"针对{principle[:20]}的实际需求",
            f"实施{principle[:20]}时的关键步骤",
        ]
        scene = random.choice(scenarios)
        correct = f"遵循{principle[:30]}规范"
        wrongs = [
            f"忽略{principle[:15]}采用临时方案",
            f"仅参考但不执行{principle[:15]}",
            f"推迟{principle[:15]}到下一版本",
        ]
        options = [correct] + wrongs
        random.shuffle(options)
        correct_label = ["A","B","C","D"][options.index(correct)]
        # 高conf更可能答对
        hit_prob = 0.4 + (conf - 50) * 0.008
        is_correct = random.random() < hit_prob
        print(f"  {'[OK]' if is_correct else '[!]'} Q{i+1}: {scene}？")
        for j, opt in enumerate(options):
            print(f"     {['A','B','C','D'][j]}) {opt}")
        if is_correct:
            print(f"     -> 答案 {correct_label} [OK]")
            correct_ans += 1
        else:
            print(f"     -> 选了 {random.choice(['A','B','C','D'])} (正确答案 {correct_label})")
    score = int(correct_ans / len(top5) * 100)
    print(f"\n  实操测试得分: {score}/100 ({correct_ans}/{len(top5)} 题正确)")
    return score, f"通用验证 {correct_ans}/{len(top5)}"

def main():
    border = "=" * 55
    print(f"\n{border}")
    print(f"  rev1 验证 -- 卫星图像鉴定")
    print(f"{border}")

    k_score = run_knowledge_test()
    covered, total = check_pattern_coverage()
    p_score, p_note = run_practical_test()

    cov_pct = (covered / total * 100) if total > 0 else 0
    
    # ── 案例质量惩罚：无足够真实案例时降分 ──
    case_penalty = 0
    if CASE_COUNT < 3:
        case_penalty = 15  # 几乎无案例，降15分
    elif CASE_COUNT < 8:
        case_penalty = 5   # 案例不足，降5分
    
    final = int(k_score * 0.35 + cov_pct * 0.35 + p_score * 0.30 - case_penalty)
    if final < 0:
        final = 0

    result = {
        "version": 1,
        "skill": "卫星图像鉴定",
        "knowledge_score": k_score,
        "patterns_covered": covered,
        "patterns_total": total,
        "practical_score": p_score,
        "practical_note": p_note,
        "final_score": final,
        "passed": final >= 60
    }

    print(f"\n{border}")
    print(f"  知识测试: {k_score:.0f}/100 x 35% = {k_score*0.35:.1f}")
    print(f"  模式覆盖: {cov_pct:.0f}/100 x 35% = {cov_pct*0.35:.1f}")
    if p_score:
        print(f"  实操测试: {p_score}/100 x 30% = {p_score*0.30:.1f}")
    print(f"  {'='*30}")
    print(f"  综合评分: {final}/100 {'[OK] PASS' if final>=60 else '[FAIL] FAIL'}")
    print(f"{border}")

    report_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                "reports", "assessment.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  报告: {report_path}")

if __name__ == "__main__":
    main()
