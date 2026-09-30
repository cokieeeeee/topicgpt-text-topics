#!/usr/bin/env python3
# self_check.py — 离线自检：用 mock 客户端跑通全管线（生成→赋值→归纳→映射）
import json
from util import load_config, load_prep
from llm_client import LLMClient
import generate, assign, induce, map as mapmod


def main():
    cfg = load_config()
    client = LLMClient(cfg, mock=True)
    prep = load_prep(cfg["paths"]["prep"])[:25]   # 仅前 25 段做自检

    print("=== Stage1 生成 ===")
    topics = generate.run(client, prep, None)
    print(f"  → {len(topics)} 个主题:", [t['name'] for t in topics])

    print("=== Stage2 赋值 ===")
    assigns = assign.run(client, prep, topics, None)
    ok = sum(1 for a in assigns if a['status'] == 'ok')
    print(f"  → {len(assigns)} 段，ok={ok}")

    print("=== Stage3 归纳 ===")
    tree = induce.run(client, topics, None)
    print(f"  → L1 数: {len(tree.get('L1', []))}")

    print("=== Stage4 OAIS 映射 ===")
    mp = mapmod.run(client, topics, None)
    print(f"  → 映射条数: {len(mp)}")
    print("=== 自检通过：全管线文件 I/O 与 JSON 解析正常 ===")


if __name__ == "__main__":
    main()
