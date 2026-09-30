#!/usr/bin/env python3
# assign.py — Stage 2: 段落级主题赋值（批量）
import json
from util import load_config, load_prompt, load_prep, safe_json
from llm_client import LLMClient

PROMPT = load_prompt("assign.txt")


def fmt_table(topics):
    return "\n".join(f"- {t['topic_id']} {t['name']}: {t['desc']}" for t in topics)


def fmt_paras(paras):
    return "\n".join(f"{{'para_id':'{str(p['para_id'])}','text':'{p['text'][:200].replace(chr(39),'')}'}}" for p in paras)


def run(client: LLMClient, prep, topics, args):
    cfg = load_config()
    table = fmt_table(topics)
    out = []
    batch = cfg["assign_batch"]
    for i in range(0, len(prep), batch):
        grp = prep[i:i + batch]
        user = PROMPT
        user = user.replace("{TOPIC_TABLE}", table)
        user = user.replace("{PARAGRAPHS}", fmt_paras(grp))
        resp = client.complete(
            "你是数字保存主题标注助手。", user,
            temperature=cfg["assign_temperature"], stage="assign")
        try:
            rows = safe_json(resp)
        except Exception as e:
            print(f"  [batch {i//batch}] 解析失败: {e}; 标记 unparsed")
            for p in grp:
                out.append({"para_id": p["para_id"], "doc_id": p["doc_id"],
                            "topics": [], "confidences": [], "status": "unparsed"})
            continue
        by_pid = {str(r["para_id"]): r for r in rows}
        for p in grp:
            pid = str(p["para_id"])
            r = by_pid.get(pid)
            if not r:
                out.append({"para_id": pid, "doc_id": p["doc_id"],
                            "topics": [], "confidences": [], "status": "missing"})
                continue
            tids = [t["topic_id"] for t in r.get("topics", [])]
            confs = [t.get("confidence", 0) for t in r.get("topics", [])]
            out.append({"para_id": pid, "doc_id": p["doc_id"],
                        "topics": tids, "confidences": confs, "status": "ok"})
        print(f"  [batch {i//batch}] 处理 {len(grp)} 段")
    with open(cfg["paths"]["assignments"], "w", encoding="utf-8") as f:
        for row in out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"赋值完成，共 {len(out)} 段 → {cfg['paths']['assignments']}")
    return out


if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("--mock", action="store_true")
    a.add_argument("--limit", type=int, default=30, help="仅前 N 段（调试）")
    ns = a.parse_args()
    cfg = load_config()
    client = LLMClient(cfg, mock=ns.mock)
    prep = load_prep(cfg["paths"]["prep"])[:ns.limit]
    topics = json.load(open(cfg["paths"]["topics"], encoding="utf-8"))
    run(client, prep, topics, ns)
