#!/usr/bin/env python3
# util.py — 管线共享工具
import json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def load_prompt(name: str) -> str:
    with open(os.path.join(ROOT, "prompts", name), encoding="utf-8") as f:
        return f.read()


def load_prep(path: str):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def extract_json(text: str):
    """容忍模型在 JSON 前后附加说明文字，截取首个 [/{ 到末个 ]/}。"""
    s = text.strip()
    starts = [i for i in (s.find('['), s.find('{')) if i >= 0]
    ends = [i for i in (s.rfind(']'), s.rfind('}')) if i >= 0]
    if not starts or not ends:
        raise ValueError("未在模型输出中定位到 JSON")
    return s[min(starts):max(ends) + 1]


def safe_json(text: str):
    return json.loads(extract_json(text))
