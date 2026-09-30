#!/usr/bin/env python3
# prep_corpus.py — Stage 0 预处理（TopicGPT 小论文切片）
# 实现方案 §1 的 5 条预处理规则：
#   1) 元数据头部行兜底剥离
#   2) 页码与页眉页脚（分页标记 / 孤立页码 / 标准号+页码页眉行）
#   3) 目录(TOC) 剔除（法律沿革段内嵌的"第一章 总则 第二章…"）
#   4) 停用词与套语（段落级丢弃明确废段；词级停用词仅用于 BERTopic，此处不做）
#   5) 段落基础过滤（空 / 无中文 / 过短 / 中文字数不足）
# 输出：prep_paragraphs.jsonl（保留 doc_id,cat,seq,std_no,title,para_id,text）+ prep_stats.json
import json, re, os
from collections import Counter

SRC = "/Users/zhouqi/Desktop/政策文件-正文/corpus_paragraphs.jsonl"
OUT = "/Users/zhouqi/.pmc_work/topicgpt/prep_paragraphs.jsonl"
STAT = "/Users/zhouqi/.pmc_work/topicgpt/prep_stats.json"
KEEP_FIELDS = ["doc_id", "cat", "seq", "std_no", "title", "para_id"]

# ---- 规则1: 元数据头部行 ----
YAML_KEY = re.compile(r'^[A-Za-z_]+:')
CN_KEY = re.compile(
    r'^(类别|文号|来源|标准号|发布机构|发布机关|备注|实施日期|法律性质|'
    r'制定机关|公布日期|施行日期|时效性|提出|归口|起草|项目名称|备案号)[:：]')
def is_meta_line(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    if YAML_KEY.match(s):
        return True
    if CN_KEY.match(s):
        return True
    if s.startswith("ICS") or s.startswith("CCS"):
        return True
    return False

# ---- 规则2: 页码与页眉页脚 ----
PAGE_MARK = re.compile(r'={3,}\s*第\s*\d+\s*页\s*={3,}')
ISOLATED_PAGE = re.compile(r'^[\s\-—·•.\u3000]*\d{1,4}[\s\-—·•.\u3000]*$')
# 标准号前缀（行首）。关键：必须"去前缀后中文字数<6"才判页眉，
# 否则正文行（如 "DA/T 47—2009 前 言 本标准由…"）会被误杀。
STD_PREFIX = re.compile(
    r'^(DA[/_]T|GB[/_]T|DA[-_]T|GB[-_]T|WS/T|WH/T|QX/T|CY/T|GY/T|JR/T|CH/T|'
    r'GA/T|DL/T|NB/T|HJ|SB/T|BB/T|HY/T|JT/T|LY/T|NY/T|SN/T|SY/T|TB/T|WB/T|'
    r'YD/T|YZ/T|DA|WS|WH|QX|CY|GY|JR|CH|GA|DL|NB|HJ|SB|BB|HY|JT|LY|NY|SN|SY|TB|WB|YD|YZ)[-_/ ]')
def cjk_count(s: str) -> int:
    return len(re.findall(r'[\u4e00-\u9fff]', s))

# ---- 规则3: 目录(TOC) ----
# 仅用 章/节/编/篇（排除"条"，法条正文满是"第X条"非目录）。
CHAP = re.compile(r'第[一二三四五六七八九十百千\d]+[章节编篇]')
DIR = re.compile(r'目\s*录|目\s*次')
def is_toc(t: str) -> bool:
    n = len(CHAP.findall(t))
    if n >= 3:
        return True
    if n >= 2 and DIR.search(t):
        return True
    return False

# ---- 规则4: 套语(boilerplate) 段落级丢弃（保守，仅明确废段） ----
BOILER = [
    re.compile(r'—{2,}\s*完\s*—{2,}'),   # ——完——
    re.compile(r'（\s*完\s*）'),
    re.compile(r'出版说明'),
    re.compile(r'本标准版权'),
    re.compile(r'本部分版权'),
]
def is_boiler(t: str) -> bool:
    return any(b.search(t) for b in BOILER)

# ---- 规则5: 段落基础过滤 ----
def basic_drop(t: str):
    if not t.strip():
        return "empty"
    if not re.search(r'[\u4e00-\u9fff]', t) and re.match(r'^[\s\W\d]+$', t):
        return "no_cjk"
    # 阈值取 12：标准/法条中 12–19 字常是完整实质性条款
    # （如"电子文件应当实行备份制度"），<12 多为标题/碎片，才丢弃。
    if len(t) < 12:
        return "too_short"
    if cjk_count(t) < 5:
        return "few_cjk"
    return None

def main():
    stats = Counter()
    kept = []
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            o = json.loads(line)
            text = o.get("text", "") or ""

            # 规则1：元数据头部行
            lines = [l for l in text.split("\n") if not is_meta_line(l)]
            text = "\n".join(lines).strip()

            # 规则2：页码与页眉页脚（逐行）
            flines = []
            for l in text.split("\n"):
                s = l.strip()
                if not s:
                    continue
                if PAGE_MARK.search(s):
                    stats["page_mark"] += 1
                    continue
                if ISOLATED_PAGE.match(s):
                    stats["isolated_page"] += 1
                    continue
                if STD_PREFIX.match(s) and cjk_count(s) < 6:
                    stats["header_std"] += 1
                    continue
                flines.append(l)
            text = "\n".join(flines).strip()

            # 规则3：目录(TOC)
            if is_toc(text):
                stats["toc"] += 1
                continue

            # 规则4：套语废段
            if is_boiler(text):
                stats["boiler"] += 1
                continue

            # 规则5：基础过滤
            r = basic_drop(text)
            if r:
                stats[r] += 1
                continue

            rec = {k: o[k] for k in KEEP_FIELDS}
            rec["text"] = text
            kept.append(rec)
            stats["kept"] += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(STAT, "w", encoding="utf-8") as f:
        json.dump(dict(stats), f, ensure_ascii=False, indent=2)

    print("保留段数:", stats["kept"])
    print("丢弃统计(分因):")
    for k in ["kept", "toc", "boiler", "page_mark", "isolated_page",
              "header_std", "empty", "no_cjk", "too_short", "few_cjk"]:
        print(f"  {k}: {stats.get(k, 0)}")

if __name__ == "__main__":
    main()
