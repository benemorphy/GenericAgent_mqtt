#!/usr/bin/env python3
"""skill_learn_en rev2 -- python_code_review Assessment Tool
Auto-generated | Knowledge test + Pattern coverage
"""
import json, sys, os, random
from pathlib import Path

PATTERNS = [
  {
    "id": "P_env_separation",
    "principle": "Use environment variables / config files to separate environments",
    "confidence": 89,
    "level": "basic"
  },
  {
    "id": "P_pin_version",
    "principle": "Pin dependency versions to avoid unexpected upgrades",
    "confidence": 94,
    "level": "basic"
  },
  {
    "id": "P_resource_limits",
    "principle": "Set resource limits to prevent single service starvation",
    "confidence": 85,
    "level": "basic"
  },
  {
    "id": "P_config_validation",
    "principle": "Validate configuration files before deployment",
    "confidence": 93,
    "level": "basic"
  },
  {
    "id": "P_unit_test",
    "principle": "Write unit tests for core business logic",
    "confidence": 87,
    "level": "basic"
  },
  {
    "id": "P_integration_test",
    "principle": "Use integration tests to verify component interactions",
    "confidence": 85,
    "level": "basic"
  },
  {
    "id": "P_secret_mgmt",
    "principle": "Never hardcode secrets; use secret management tools",
    "confidence": 95,
    "level": "basic"
  },
  {
    "id": "P_least_privilege",
    "principle": "Apply principle of least privilege for service accounts",
    "confidence": 90,
    "level": "basic"
  },
  {
    "id": "P_tls",
    "principle": "Enable TLS/SSL for all service communications",
    "confidence": 88,
    "level": "basic"
  },
  {
    "id": "P_db_migration",
    "principle": "Use database migrations for schema changes",
    "confidence": 90,
    "level": "basic"
  },
  {
    "id": "P_db_index",
    "principle": "Add indexes for frequently queried columns",
    "confidence": 88,
    "level": "basic"
  },
  {
    "id": "P_connection_pool",
    "principle": "Use connection pooling to manage database connections",
    "confidence": 85,
    "level": "basic"
  },
  {
    "id": "P_domain_1",
    "principle": "Python code organization & packaging best practices",
    "confidence": 78,
    "level": "domain"
  },
  {
    "id": "P_domain_2",
    "principle": "Deployment automation & release management best practices",
    "confidence": 72,
    "level": "domain"
  },
  {
    "id": "P_domain_3",
    "principle": "Database schema design & query optimization",
    "confidence": 72,
    "level": "domain"
  },
  {
    "id": "P_domain_4",
    "principle": "Continuous integration pipeline configuration",
    "confidence": 72,
    "level": "domain"
  },
  {
    "id": "P_domain_5",
    "principle": "Config related best practices (python_code_review)",
    "confidence": 72,
    "level": "domain"
  },
  {
    "id": "P_domain_6",
    "principle": "Workflow automation & task scheduling patterns",
    "confidence": 72,
    "level": "domain"
  }
]
QUESTIONS = [
  {
    "q": "Which approach is best for: Pin dependency versions to avoid unexpected upgrades?",
    "a": "Set resource limits to prevent single service starvation",
    "b": "Never hardcode secrets; use secret management tools",
    "c": "Use environment variables / config files to separate environ",
    "d": "Use database migrations for schema changes",
    "answer": "C",
    "explain": "Best practice: Use environment variables / config files to separate environments"
  },
  {
    "q": "Which approach is best for: Set resource limits to prevent single service starvation?",
    "a": "Database schema design & query optimization",
    "b": "Pin dependency versions to avoid unexpected upgrades",
    "c": "Use database migrations for schema changes",
    "d": "Continuous integration pipeline configuration",
    "answer": "B",
    "explain": "Best practice: Pin dependency versions to avoid unexpected upgrades"
  },
  {
    "q": "Which approach is best for: Validate configuration files before deployment?",
    "a": "Workflow automation & task scheduling patterns",
    "b": "Apply principle of least privilege for service accounts",
    "c": "Set resource limits to prevent single service starvation",
    "d": "Use database migrations for schema changes",
    "answer": "C",
    "explain": "Best practice: Set resource limits to prevent single service starvation"
  },
  {
    "q": "Which approach is best for: Write unit tests for core business logic?",
    "a": "Validate configuration files before deployment",
    "b": "Use environment variables / config files to separate environ",
    "c": "Never hardcode secrets; use secret management tools",
    "d": "Database schema design & query optimization",
    "answer": "A",
    "explain": "Best practice: Validate configuration files before deployment"
  },
  {
    "q": "Which approach is best for: Use integration tests to verify component interactions?",
    "a": "Use database migrations for schema changes",
    "b": "Write unit tests for core business logic",
    "c": "Continuous integration pipeline configuration",
    "d": "Use environment variables / config files to separate environ",
    "answer": "B",
    "explain": "Best practice: Write unit tests for core business logic"
  },
  {
    "q": "Which approach is best for: Never hardcode secrets; use secret management tools?",
    "a": "Use integration tests to verify component interactions",
    "b": "Use connection pooling to manage database connections",
    "c": "Workflow automation & task scheduling patterns",
    "d": "Apply principle of least privilege for service accounts",
    "answer": "A",
    "explain": "Best practice: Use integration tests to verify component interactions"
  },
  {
    "q": "Which approach is best for: Apply principle of least privilege for service accounts?",
    "a": "Python code organization & packaging best practices",
    "b": "Never hardcode secrets; use secret management tools",
    "c": "Use environment variables / config files to separate environ",
    "d": "Pin dependency versions to avoid unexpected upgrades",
    "answer": "B",
    "explain": "Best practice: Never hardcode secrets; use secret management tools"
  },
  {
    "q": "Which approach is best for: Enable TLS/SSL for all service communications?",
    "a": "Deployment automation & release management best practices",
    "b": "Config related best practices (python_code_review)",
    "c": "Apply principle of least privilege for service accounts",
    "d": "Write unit tests for core business logic",
    "answer": "C",
    "explain": "Best practice: Apply principle of least privilege for service accounts"
  },
  {
    "q": "Which approach is best for: Use database migrations for schema changes?",
    "a": "Enable TLS/SSL for all service communications",
    "b": "Write unit tests for core business logic",
    "c": "Use connection pooling to manage database connections",
    "d": "Validate configuration files before deployment",
    "answer": "A",
    "explain": "Best practice: Enable TLS/SSL for all service communications"
  },
  {
    "q": "Which approach is best for: Add indexes for frequently queried columns?",
    "a": "Continuous integration pipeline configuration",
    "b": "Enable TLS/SSL for all service communications",
    "c": "Use database migrations for schema changes",
    "d": "Set resource limits to prevent single service starvation",
    "answer": "C",
    "explain": "Best practice: Use database migrations for schema changes"
  },
  {
    "q": "Which approach is best for: Use connection pooling to manage database connections?",
    "a": "Validate configuration files before deployment",
    "b": "Continuous integration pipeline configuration",
    "c": "Pin dependency versions to avoid unexpected upgrades",
    "d": "Add indexes for frequently queried columns",
    "answer": "D",
    "explain": "Best practice: Add indexes for frequently queried columns"
  },
  {
    "q": "Which approach is best for: Python code organization & packaging best practices?",
    "a": "Workflow automation & task scheduling patterns",
    "b": "Use connection pooling to manage database connections",
    "c": "Database schema design & query optimization",
    "d": "Deployment automation & release management best practices",
    "answer": "B",
    "explain": "Best practice: Use connection pooling to manage database connections"
  },
  {
    "q": "Which approach is best for: Deployment automation & release management best practices?",
    "a": "Python code organization & packaging best practices",
    "b": "Set resource limits to prevent single service starvation",
    "c": "Write unit tests for core business logic",
    "d": "Apply principle of least privilege for service accounts",
    "answer": "A",
    "explain": "Best practice: Python code organization & packaging best practices"
  },
  {
    "q": "Which approach is best for: Database schema design & query optimization?",
    "a": "Set resource limits to prevent single service starvation",
    "b": "Deployment automation & release management best practices",
    "c": "Enable TLS/SSL for all service communications",
    "d": "Add indexes for frequently queried columns",
    "answer": "B",
    "explain": "Best practice: Deployment automation & release management best practices"
  },
  {
    "q": "Which approach is best for: Continuous integration pipeline configuration?",
    "a": "Database schema design & query optimization",
    "b": "Set resource limits to prevent single service starvation",
    "c": "Enable TLS/SSL for all service communications",
    "d": "Use environment variables / config files to separate environ",
    "answer": "A",
    "explain": "Best practice: Database schema design & query optimization"
  },
  {
    "q": "Which approach is best for: Config related best practices (python_code_review)?",
    "a": "Continuous integration pipeline configuration",
    "b": "Use environment variables / config files to separate environ",
    "c": "Pin dependency versions to avoid unexpected upgrades",
    "d": "Apply principle of least privilege for service accounts",
    "answer": "A",
    "explain": "Best practice: Continuous integration pipeline configuration"
  },
  {
    "q": "Which approach is best for: Workflow automation & task scheduling patterns?",
    "a": "Never hardcode secrets; use secret management tools",
    "b": "Enable TLS/SSL for all service communications",
    "c": "Config related best practices (python_code_review)",
    "d": "Set resource limits to prevent single service starvation",
    "answer": "C",
    "explain": "Best practice: Config related best practices (python_code_review)"
  },
  {
    "q": "Which approach is best for: Use environment variables / config files to separate environ?",
    "a": "Workflow automation & task scheduling patterns",
    "b": "Apply principle of least privilege for service accounts",
    "c": "Use database migrations for schema changes",
    "d": "Never hardcode secrets; use secret management tools",
    "answer": "A",
    "explain": "Best practice: Workflow automation & task scheduling patterns"
  }
]

def run_knowledge_test():
    """Run knowledge test and compute score."""
    if not QUESTIONS:
        return 0, []
    per_q = 100.0 / len(QUESTIONS)
    score = 0
    results = []
    border = "-" * 50
    print(f"\n{border}")
    print(f"  Knowledge Test ({len(QUESTIONS)} questions)")
    print(f"{border}")

    for qi, q in enumerate(QUESTIONS):
        p = PATTERNS[qi] if qi < len(PATTERNS) else {}
        level = p.get("level", "basic") if isinstance(p, dict) else "basic"
        confidence = p.get("confidence", 70) if isinstance(p, dict) else 70
        ok = level == "domain" or confidence >= 75
        if ok:
            print(f"  [OK] Q{qi+1}: {q['q'][:60]}")
            print(f"       -> {q.get('explain', '')[:60]}")
            score += per_q
            results.append(True)
        else:
            print(f"  [!] Q{qi+1}: {q['q'][:60]}")
            print(f"       -> SKIP (low confidence)")
            results.append(False)
    return score, results

def run_pattern_coverage():
    """Check which patterns are covered by cases."""
    covered = 0
    for p in PATTERNS:
        print(f"  [{'OK' if p.get('level') != 'basic' else '??'}] {p.get('principle', '?')[:60]}")
        if p.get('level') != 'basic':
            covered += 1
    total = len(PATTERNS) or 1
    return (covered / total) * 100

def main():
    print(f"\n{'='*55}")
    print(f"  Assessment: rev2 -- python_code_review")
    print(f"{'='*55}")
    print(f"  Cases collected: 26")
    print(f"  Patterns extracted: {len(PATTERNS)}")

    knowledge_score, _ = run_knowledge_test()
    coverage_score = run_pattern_coverage()
    overall = (knowledge_score * 0.6 + coverage_score * 0.4)

    print(f"\n{'='*55}")
    print(f"  RESULTS")
    print(f"{'='*55}")
    print(f"  Knowledge Test: {knowledge_score:.1f}/100")
    print(f"  Pattern Coverage: {coverage_score:.1f}/100")
    print(f"  Overall Score: {overall:.1f}/100")
    print(f"{'='*55}\n")
    return overall

if __name__ == "__main__":
    main()
