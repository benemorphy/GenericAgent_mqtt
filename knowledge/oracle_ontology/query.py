"""甲骨文本体查询模块 — 基于 rdflib 的 SPARQL 查询接口

用法:
    python query.py                           # 运行示例查询
    python query.py --char 日                 # 查询某个字
    python query.py --component 水             # 按构件查询
    python query.py --era 武丁                # 按时代查询
"""

import sys, pathlib, json
import rdflib
from rdflib import Graph, Namespace
from rdflib.namespace import RDF, RDFS, OWL

OAG = Namespace("http://example.org/oracle-ontology/")

ONTOLOGY_DIR = pathlib.Path(__file__).parent
TTL_PATH = ONTOLOGY_DIR / "oracle_ontology.ttl"

g = Graph()
g.parse(str(TTL_PATH), format="turtle")


def query_char(char):
    """查询某个甲骨文字符的全部信息"""
    q = g.query("""
    PREFIX oag: <http://example.org/oracle-ontology/>
    SELECT ?glyph ?pinyin ?def ?comp ?era ?conf ?variant
    WHERE {
        ?glyph a oag:Glyph ; oag:char \"""" + char + """\"@zh .
        OPTIONAL { ?glyph oag:realizes / oag:pronunciation ?pinyin . }
        OPTIONAL { ?glyph oag:realizes / oag:denotes / oag:definition ?def . }
        OPTIONAL { ?glyph oag:containsComponent / rdfs:label ?comp . }
        OPTIONAL { ?glyph oag:belongsToEra / rdfs:label ?era . }
        OPTIONAL { ?glyph oag:confidence ?conf . }
        OPTIONAL { ?glyph oag:variantOf / oag:char ?variant . }
    }
    """)
    results = []
    for row in q:
        r = {}
        for k in ["pinyin", "def", "comp", "era", "variant"]:
            v = getattr(row, k, None)
            if v is not None:
                r[k] = str(v)
        results.append(r)
    return results


def query_by_component(component):
    """按构件查询所有包含该构件的字"""
    q = g.query("""
    PREFIX oag: <http://example.org/oracle-ontology/>
    SELECT ?char
    WHERE {
        ?comp rdfs:label \"""" + component + """\"@zh .
        ?glyph oag:containsComponent ?comp ;
               oag:char ?char .
    } ORDER BY ?char
    """)
    return [str(getattr(row, "char")) for row in q]


def query_all():
    """列出全部字符"""
    q = g.query("""
    PREFIX oag: <http://example.org/oracle-ontology/>
    SELECT ?char ?pinyin
    WHERE {
        ?glyph a oag:Glyph ; oag:char ?char .
        OPTIONAL { ?glyph oag:realizes / oag:pronunciation ?pinyin . }
    } ORDER BY ?char
    """)
    results = []
    for row in q:
        c = str(getattr(row, "char"))
        p = str(getattr(row, "pinyin", "")) if getattr(row, "pinyin", None) else ""
        results.append({"char": c, "pinyin": p})
    return results


def query_stats():
    """本体统计信息"""
    q = g.query("""
    PREFIX oag: <http://example.org/oracle-ontology/>
    SELECT (COUNT(?g) AS ?glyphs) (COUNT(?c) AS ?comps)
           (COUNT(?s) AS ?senses) (COUNT(?e) AS ?eras)
    WHERE {
        { SELECT (COUNT(*) AS ?g) WHERE { ?x a oag:Glyph } }
        { SELECT (COUNT(*) AS ?c) WHERE { ?x a oag:Component } }
        { SELECT (COUNT(*) AS ?s) WHERE { ?x a oag:Sense } }
        { SELECT (COUNT(*) AS ?e) WHERE { ?x a oag:Era } }
    }
    """)
    for row in q:
        return {
            "glyphs": int(getattr(row, "glyphs")),
            "components": int(getattr(row, "comps")),
            "senses": int(getattr(row, "senses")),
            "eras": int(getattr(row, "eras")),
            "triples": len(g),
        }


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--char":
        char = sys.argv[2]
        results = query_char(char)
        print(f"「{char}」查询结果:")
        if results:
            for r in results:
                for k, v in r.items():
                    print(f"  {k}: {v}")
        else:
            print("  未找到")

    elif len(sys.argv) > 2 and sys.argv[1] == "--component":
        comp = sys.argv[2]
        chars = query_by_component(comp)
        print(f"含有「{comp}」构件的字: {', '.join(chars)}")

    elif len(sys.argv) > 2 and sys.argv[1] == "--era":
        era = sys.argv[2]
        q = g.query("""
        PREFIX oag: <http://example.org/oracle-ontology/>
        SELECT ?char WHERE {
            ?glyph a oag:Glyph ; oag:char ?char ;
                   oag:belongsToEra / rdfs:label \"""" + era + """\"@zh .
        } ORDER BY ?char
        """)
        chars = [str(getattr(row, "char")) for row in q]
        print(f"{era}时期的字: {', '.join(chars)}")

    else:
        stats = query_stats()
        print("甲骨文本体统计:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        print()
        all_chars = query_all()
        print(f"已收录字符 ({len(all_chars)}):")
        for c in all_chars:
            print(f"  {c['char']}: {c['pinyin']}")
