#!/usr/bin/env python3
# induce.py — Stage 3: 层级归纳（上位归纳为 L1 主题树）
import json
from util import load_config, load_prompt, safe_json
from llm_client import LLMClient

PROMPT = load_prompt("induce.txt")


def fmt_leaf(topics):
    return "\n".join(f'- {{"id":"{t["topic_id"]}","name":"{t["name"]}","desc":"{t["desc"]}"}}' for t in topics)


def run(client: LLMClient, topics, args):
    cfg = load_config()
    user = PROMPT.replace("{LEAF_TOPICS}", fmt_leaf(topics))
    resp = client.complete(
        "你是数字保存主题归纳助手。", user,
        temperature=cfg["induce_temperature"], stage="induce")
    tree = safe_json(resp)
    with open(cfg["paths"]["tree"], "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)
    n = len(tree.get("L1", []))
    print(f"层级归纳完成，{n} 个 L1 高层主题 → {cfg['paths']['tree']}")
    return tree


if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("--mock", action="store_true")
    ns = a.parse_args()
    cfg = load_config()
    client = LLMClient(cfg, mock=ns.mock)
    topics = json.load(open(cfg["paths"]["topics"], encoding="utf-8"))
    run(client, topics, ns)
