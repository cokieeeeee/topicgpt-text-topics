#!/usr/bin/env python3
# map.py — Stage 4: OAIS 六功能映射（分析层，TopicGPT 方法之外）
import json, csv
from util import load_config, load_prompt, safe_json
from llm_client import LLMClient

PROMPT = load_prompt("map.txt")


def fmt_topics(topics):
    return "\n".join(f'- {{"id":"{t["topic_id"]}","name":"{t["name"]}","desc":"{t["desc"]}"}}' for t in topics)


def run(client: LLMClient, topics, args):
    cfg = load_config()
    user = PROMPT.replace("{TOPICS}", fmt_topics(topics))
    resp = client.complete(
        "你是数字保存评估助手。", user,
        temperature=cfg["map_temperature"], stage="map")
    mapping = safe_json(resp)
    # 写映射 CSV
    with open(cfg["paths"]["oais_map"], "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["topic_id", "oais_func", "rationale"])
        for m in mapping:
            w.writerow([m["topic_id"], m["oais_func"], m.get("rationale", "")])
    # 聚合覆盖率：按主题命中的段数（来自 assignments）
    assign = {}
    try:
        with open(cfg["paths"]["assignments"], encoding="utf-8") as f:
            for line in f:
                o = json.loads(line)
                assign[o["para_id"]] = o.get("topics", [])
    except FileNotFoundError:
        assign = {}
    func_paras = {}
    for m in mapping:
        tid = m["topic_id"]
        func = m["oais_func"]
        n = sum(1 for pid, ts in assign.items() if tid in ts)
        func_paras.setdefault(func, 0)
        func_paras[func] += n
    total = len(assign) or 1
    with open(cfg["paths"]["oais_cov"], "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["oais_func", "covered_paras", "share"])
        for fn in cfg["oais_functions"]:
            key = fn.split("(")[0]
            n = func_paras.get(key, 0)
            w.writerow([fn, n, f"{n/total:.3f}"])
    print(f"OAIS 映射完成 → {cfg['paths']['oais_map']} 与 {cfg['paths']['oais_cov']}")
    return mapping


if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("--mock", action="store_true")
    ns = a.parse_args()
    cfg = load_config()
    client = LLMClient(cfg, mock=ns.mock)
    topics = json.load(open(cfg["paths"]["topics"], encoding="utf-8"))
    run(client, topics, ns)
