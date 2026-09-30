#!/usr/bin/env python3
# llm_client.py — LLM 客户端封装（DeepSeek，支持 mock 离线自检）
import json, os, re, random


class LLMClient:
    """真实模式调用 DeepSeek；mock 模式返回确定性假 JSON，仅供离线自检。"""

    def __init__(self, config: dict, mock: bool = False):
        self.cfg = config
        self.mock = mock
        self._real = None
        if not mock:
            try:
                import openai
            except ImportError:
                raise RuntimeError("未安装 openai 库且非 mock 模式")
            key = os.environ.get(config["api_key_env"])
            if not key:
                raise RuntimeError(f"环境变量 {config['api_key_env']} 未设置")
            self._real = openai.OpenAI(api_key=key, base_url=config["base_url"])

    def complete(self, system_prompt: str, user_prompt: str,
                 temperature: float = 0.0, max_tokens: int = 3000,
                 stage: str = "gen") -> str:
        if self.mock:
            return self._mock(system_prompt, user_prompt, stage)
        resp = self._real.chat.completions.create(
            model=self.cfg["model"],
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}],
            temperature=temperature, max_tokens=max_tokens)
        return resp.choices[0].message.content

    # ---------- mock ----------
    def _mock(self, system: str, user: str, stage: str) -> str:
        if stage == "gen":
            return json.dumps([
                {"name": "长期保存技术策略", "desc": "格式迁移、仿真、保存规划等技术性长期保存措施",
                 "keywords": ["迁移", "仿真", "保存规划"]},
                {"name": "元数据与封装", "desc": "元数据方案、信息包封装与著录规则",
                 "keywords": ["元数据", "封装", "著录"]}
            ], ensure_ascii=False)
        if stage == "assign":
            ids = re.findall(r'para_id[\'"]?\s*:\s*[\'"]?([^\'",\s}]+)', user)
            if not ids:
                ids = re.findall(r'para_id["\s:]+([A-Za-z0-9_\-]+)', user)
            out = []
            for i, pid in enumerate(ids):
                out.append({"para_id": pid,
                             "topics": [{"topic_id": f"t{ (i % 3) + 1:02d}",
                                         "confidence": round(0.6 + 0.3 * ((i % 3) / 3), 2)}]})
            return json.dumps(out, ensure_ascii=False)
        if stage == "induce":
            leaf = re.findall(r'"id":\s*"([^"]+)"', user)
            if not leaf:
                leaf = ["t01", "t02", "t03"]
            half = max(1, len(leaf) // 2)
            return json.dumps({
                "L1": [
                    {"name": "技术供给", "desc": "长期保存技术相关制度",
                     "children": leaf[:half]},
                    {"name": "管理供给", "desc": "职责与监管相关制度",
                     "children": leaf[half:]}
                ]}, ensure_ascii=False)
        if stage == "map":
            ids = re.findall(r'"id":\s*"([^"]+)"', user)
            funcs = ["Ingest", "ArchivalStorage", "DataManagement",
                     "PreservationPlanning", "Access", "Administration"]
            out = [{"topic_id": i, "oais_func": funcs[k % len(funcs)],
                    "rationale": "离线自检占位理由"} for k, i in enumerate(ids)]
            return json.dumps(out, ensure_ascii=False)
        return "[]"
