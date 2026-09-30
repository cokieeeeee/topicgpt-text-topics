# TopicGPT 文本主题建模（WorkBuddy Skill）

用 **TopicGPT**（Pham et al., NAACL 2024, *A Prompt-based Topic Modeling Framework*）对**中文政策/标准/长文稿**做**段落级主题建模**，可选映射到外部理论框架做覆盖率/缺口分析。

A prompt-based, LLM-agnostic topic modeling pipeline for Chinese policy & standard corpora, with paragraph-level assignment, hierarchical topic induction, and optional framework mapping. Includes an offline `--mock` self-check so the whole pipeline runs without an API key.

---

## 它做什么

```
语料(段落级) → prep_corpus.py(预处理) → generate.py(主题生成)
            → assign.py(段落赋值) → induce.py(层级归纳) → map.py(框架映射 + 覆盖率)
                        ↑ 离线自检：self_check.py 用假数据跑通全链路
```

- **段落级**分析单元：一篇政策/标准常含多主题，段落粒度更细，也便于映射到模型各层。
- **不做词级停用词删除**：TopicGPT 靠 LLM 语义理解，删词只丢信息。停用词表仅在跑 BERTopic 的 c-TF-IDF 表征时才用。
- **可复现**：冻结模型版本 + prompt 全版本化 + 固定 seed + 稳定性复跑。

## 三条先记住的原则

1. **TopicGPT 是"LLM 语义理解"框架，不是词频/词袋方法**，主流程不删词。
2. **原论文管线只有三步**：主题生成 → 主题精修 → 主题赋值。它**不映射任何外部框架**。
3. **框架映射（`map.py`）是方法之外的分析层**——把主题树挂到 OAIS/治理模型上做缺口论证，属于你论文的论点需求，不属于 TopicGPT 本身。

## 目录结构

```
.
├── SKILL.md                      # 技能说明（含校准踩坑记录）★核心
├── README.md
├── references/
│   └── design-notes.md           # 设计说明与校准依据
└── scripts/
    ├── prep_corpus.py            # §1 预处理（5 条规则）
    ├── generate.py               # §2.1 主题生成
    ├── assign.py                 # §2.2 段落赋值（批量）
    ├── induce.py                 # §2.3 层级归纳（L1/L2 主题树）
    ├── map.py                    # §4 框架映射 + 覆盖率
    ├── llm_client.py             # OpenAI 兼容客户端 + mock
    ├── util.py                   # 配置/IO/JSON 解析
    ├── self_check.py             # 离线自检（全链路假数据）
    ├── config.example.json       # 配置模板（复制为 config.json 后改）
    └── prompts/                  # gen / assign / induce / map 四套 prompt
```

## 快速开始

```bash
# 0) 准备配置（config.json 不入库，含本地路径）
cd scripts
cp config.example.json config.json
#   然后编辑 config.json 的 paths.* 指向你的语料与输出目录

# 1) 预处理：读语料 → 写 prep_paragraphs.jsonl + prep_stats.json
python prep_corpus.py

# 2) 离线自检：不用 API key 也能跑通全链路
python self_check.py
#   预期：生成(2主题) → 赋值(25/25 ok) → 归纳(2 L1) → 映射(2)

# 3) 真实运行（需 API key）
export DEEPSEEK_API_KEY=sk-xxxx        # 只放环境变量，不落盘
python generate.py
python assign.py --limit 30            # 先小样本验证，审阅后再全量
python assign.py
python induce.py
python map.py
```

> 脚本从**自身所在目录**读取 `config.json` 与 `prompts/`，所以运行前 `cd scripts`（或设 `PYTHONPATH`）。

## 配置与模型

- **无模型品牌强制**：TopicGPT 是模型无关框架（原论文用 "LLM" 泛指）。**国内模型可用且对中文语料更优**（合规、可私有化）。
- 默认走 **DeepSeek**（OpenAI 兼容接口）：`model=deepseek-v4-flash`，`base_url=https://api.deepseek.com`。  
  换其他模型只需改 `config.json` 的 `model` / `base_url`（任何 OpenAI 兼容端点均可）。
- **必报项（方法章）**：冻结模型+版本、temperature（生成 0.3 / 赋值 0）、prompt 模板、抽样 seed、迭代轮次、稳定性复跑。
- ⚠️ LLM 迭代生成有 **anchoring bias**（被首轮主题锚定）→ 多轮/多次运行取稳定结构并如实说明。

## 输入语料格式

`prep_corpus.py` 读取 **JSONL**，每行一个段落对象：

```json
{"doc_id": "03_03", "cat": "03", "seq": 3, "std_no": "DA/T 46-2009",
 "title": "文书类电子文件元数据方案", "para_id": 12, "text": "……"}
```

若你的语料是纯文本目录，先转成上述 JSONL 再跑预处理。

## 预处理 5 条规则（详见 SKILL.md §1）

元数据头兜底剥离 → 页码与页眉页脚 → 目录(TOC)剔除 → 套语废段 → 段落基础过滤。

**两个踩过的坑（别改错）**：

- TOC 检测**必须排除"第X条"**（法条正文全是"第X条"），只用"第X章/节/编/篇"计数。
- `too_short` 阈值取 **12**，不要用 20——12–19 字常是完整实质性条款。

## 引用

```bibtex
@inproceedings{pham-etal-2024-topicgpt,
  title     = {{T}opic{GPT}: A Prompt-based Topic Modeling Framework},
  author    = {Pham, Chau Minh and Hoyle, Alexander and Sun, Simeng and Resnik, Philip and Iyyer, Mohit},
  booktitle = {Proceedings of the 2024 Conference of the North American Chapter of the
               Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)},
  year      = {2024},
  pages     = {2956--2984},
  address   = {Mexico City, Mexico},
  publisher = {Association for Computational Linguistics}
}
```

## 许可

未附许可证文件。如需开源授权（如 MIT / CC BY 4.0），请自行添加 `LICENSE`。
