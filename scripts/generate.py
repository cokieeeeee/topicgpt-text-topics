#!/usr/bin/env python3
# generate.py — Stage 1: 迭代式主题生成
import json, os, random
from util import load_config, load_prompt, load_prep, safe_json
from llm_client import LLMClient

PROMPT = load_prompt("gen.txt")


def fmt_existing(topics):
    if not topics:
        return "（暂无，请从头生成）"
    return "\n".join(f"- {t['topic_id']} {t['name']}: {t['desc']}" for t in topics)


def fmt_sample(paras):
    return "\n\n".join(f"[P{i+1}] {p['text']}" for i, p in enumerate(paras))


def run(client: LLMClient, prep, args):
    cfg = load_config()
    random.seed(cfg["seed"])
    topics = []
    n_seen = 0
    for r in range(cfg["gen_rounds"]):
        if n_seen >= len(prep):
            break
        sample = prep[n_seen:n_seen + cfg["gen_sample_per_round"]]
        n_seen += len(sample)
        user = PROMPT
        user = user.replace("{EXISTING_TOPICS}", fmt_existing(topics))
        user = user.replace("{SAMPLE_PARAGRAPHS}", fmt_sample(sample))
        out = client.complete(
            "你是数字保存主题构建助手。", user,
            temperature=cfg["gen_temperature"], stage="gen")
        try:
            new = safe_json(out)
        except Exception as e:
            print(f"  [round {r}] 解析失败: {e}; 跳过")
            continue
        if not new:
            print(f"  [round {r}] 模型返回空（已收敛），停止生成")
            break
        for t in new:
            tid = f"t{len(topics)+1:02d}"
            topics.append({"topic_id": tid, "name": t.get("name", ""),
                           "desc": t.get("desc", ""),
                           "keywords": t.get("keywords", [])})
        print(f"  [round {r}] +{len(new)} 主题，累计 {len(topics)}")

    with open(cfg["paths"]["topics"], "w", encoding="utf-8") as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)
    print(f"主题生成完成，共 {len(topics)} 个 → {cfg['paths']['topics']}")
    return topics


if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("--mock", action="store_true")
    a.add_argument("--limit", type=int, default=None, help="仅用前 N 段（调试）")
    ns = a.parse_args()
    cfg = load_config()
    client = LLMClient(cfg, mock=ns.mock)
    prep = load_prep(cfg["paths"]["prep"])
    if ns.limit:
        prep = prep[:ns.limit]
    run(client, prep, ns)
