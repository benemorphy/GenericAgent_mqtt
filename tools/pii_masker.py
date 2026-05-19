#!/usr/bin/env python3
"""
PII Masker — LLM调用前的私域信息脱敏中间层

功能:
  - 自动检测身份证号、手机号、银行卡号
  - 替换为脱敏标记 [ID_CARD_1] [PHONE_1] [BANK_CARD_1]
  - 本地维护映射表，LLM返回后还原
  - 支持自定义掩码规则

用法:
    masker = PIIMasker()
    safe_text = masker.mask("身份证110101199001011234")
    # -> "身份证[ID_CARD_1]"
    llm_response = call_llm(safe_text)
    restored = masker.unmask(llm_response)
"""

import re, json, time, os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "temp"
MASK_DB = DATA_DIR / "pii_mask_map.json"

_PATTERNS = {
    "ID_CARD": r'(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)',
    "PHONE":   r'(?<!\d)1[3-9]\d{9}(?!\d)',
    "BANK_CARD": r'(?<!\d)[1-9]\d{15,18}(?!\d)',
}


class PIIMasker:
    def __init__(self):
        self._seq = {"ID_CARD": 0, "PHONE": 0, "BANK_CARD": 0}
        self._mapping = {}
        self._reverse = {}
        self._load()

    def _load(self):
        if MASK_DB.exists():
            try:
                data = json.loads(MASK_DB.read_text(encoding='utf-8'))
                self._seq = data.get("seq", self._seq)
                self._mapping = data.get("mapping", {})
                self._reverse = {v: k for k, v in self._mapping.items()}
            except Exception:
                pass

    def _save(self):
        MASK_DB.parent.mkdir(parents=True, exist_ok=True)
        MASK_DB.write_text(json.dumps(
            {"seq": self._seq, "mapping": self._mapping}, ensure_ascii=False), encoding='utf-8')

    def _mask(self, text: str) -> str:
        if len(text) <= 4:
            return text
        return text[:3] + "***" + text[-4:]

    def mask(self, text: str) -> str:
        """将原文中的PII替换为脱敏标记，返回安全文本"""
        for ptype, pattern in _PATTERNS.items():
            for match in re.finditer(pattern, text):
                original = match.group()
                if original not in self._reverse:
                    self._seq[ptype] += 1
                    token = f"[{ptype}_{self._seq[ptype]}]"
                    self._mapping[token] = original
                    self._reverse[original] = token
                else:
                    token = self._reverse[original]
                text = text.replace(original, token, 1)
        self._save()
        return text

    def unmask(self, text: str) -> str:
        """将LLM返回结果中的脱敏标记还原为原文"""
        for token, original in self._mapping.items():
            text = text.replace(token, original)
        return text

    def summary(self) -> str:
        lines = [f"PII掩码映射 ({len(self._mapping)}项):"]
        for token, original in self._mapping.items():
            lines.append(f"  {token} -> {self._mask(original)}")
        return "\n".join(lines)


if __name__ == "__main__":
    m = PIIMasker()
    safe = m.mask("用户身份证110101199001011234，手机13800138000，银行卡6222021234567890123")
    print(f"掩码后: {safe}")
    print(f"还原后: {m.unmask(safe)}")
    print()
    print(m.summary())
