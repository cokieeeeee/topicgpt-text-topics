---
name: TopicGPT文本主题
description: 用 TopicGPT（Pham et al. 2024, prompt-based LLM 主题建模）对中文政策/标准/长文稿做**段落级主题建模**，并可选映射到外部框架（OAIS 六功能或自定义治理模型）。覆盖完整管线：预处理去噪（元数据头/页码页眉/目录TOC/套语/碎片）→ 迭代主题生成 → 段落级主题赋值 → 层级归纳（L1/L2 主题树）→ 框架映射 → 覆盖率缺口分析。适用于"跑一遍 TopicGPT""做文本主题建模""给政策/标准语料提主题""把主题映射到 OAIS/治理模型""主题树""LLM 主题生成与赋值""BERTopic 三角验证"等场景。含 `--mock` 离线自检（无 API key 也能跑通全管线）。
agent_created: true
---

# TopicGPT 文本主题建模

## 核心理念（先记住这三条，否则方向就错）

1. **TopicGPT 是"LLM 语义理解"框架，不是词频/词袋方法。主流程不做词级停用词删除**——LLM 自会忽略无信息词，删词只会丢信息。停用词表**仅**在跑 BERTopic 的 c-TF-IDF 表征时才用。
2. **Pham et al. 2024 的原管线只有三步**：主题生成 → 主题精修（合并近义+剔低频）→ 主题赋值。它**不映射任何外部框架**。把主题映射到 OAIS/治理模型是**方法之外、你论文论点所需的分析层**（见下 §4）。
3. **分析单元建议段落级**：政策/标准文本一篇常含多主题，段落级粒度更细、更利于映射到治理模型各层。

## 何时用

- 有一批**已清洗的中文正文**（政策、标准、法规、长报告），需要析出"潜藏主题"并给每段打主题标签。
- 需要**主题树（层级）**而非扁平关键词。
- 需要把主题**映射到理论框架**（OAIS 六功能、自定义治理模型 4 层等）以做"覆盖率/缺口"论证。
- 需要**可复现、可留痕**的主题建模（冻结模型版本 + prompt 版本化 + seed + 稳定性复跑）。

## 管线总览

```
语料(段落级) → prep_corpus.py(预处理5规则) → generate.py(主题生成)
            → assign.py(段落赋值) → induce.py(层级归纳) → map.py(框架映射+覆盖率)
                      ↑ mock 自检：self_check.py 全链路假数据跑通
```

## §1 预处理（`scripts/prep_corpus.py`）

**5 条规则**：① 元数据头部行兜底剥离；② 页码与页眉页脚（分页标记/孤立页码/标准号+页码页眉）；③ 目录(TOC)剔除；④ 套语废段；⑤ 段落基础过滤。

**关键校准（踩过的坑，别改错）**：
- **TOC 检测必须排除"第X条"**——法条正文满是"第X条"，那是正文不是目录。只用 `第[一二三…\d]+[章节编篇]`（无"条"）计数：**≥3 个即判 TOC，或 ≥2 且含"目录/目次"**。法律"沿革段"内嵌的目录（"…修正 … 目 录 第一章 总则 第二章…"）会命中此规则，属正确丢弃。
- **`too_short` 阈值取 12，不要用 20**——中文法条/标准里 12–19 字的常是**完整实质性条款**（如"电子文件应当实行备份制度"），设 20 会误删核心供给内容。
- **`few_cjk`（中文<5）** 丢弃的多是噪声：XML/METS 碎片、标准号（`GB/T 18894`）、页码标记（`PAGE2 / NUMPAGES17`）、电话。抽样确认即可，一般无误删。
- 运行后**抽查** `toc` / `too_short` / `few_cjk` 三类样例，确认没删正文再进模型。

```bash
cd scripts
python prep_corpus.py          # 读 config.json 的 prep 源，写 prep_paragraphs.jsonl + prep_stats.json
```

## §2 TopicGPT 四阶段

| 阶段 | 脚本 | 产物 |
|---|---|---|
| 主题生成 | `generate.py` | `topics.json`（叶子主题表） |
| 段落赋值 | `assign.py` | `paragraph_topic.jsonl`（每段→主题+置信度） |
| 层级归纳 | `induce.py` | `topic_tree.json`（L1→L2 主题树） |
| 框架映射 | `map.py` | `topic_oais_mapping.csv`＋`oais_coverage.csv` |

- prompt 模板在 `scripts/prompts/`（gen/assign/induce/map），全部版本化。
- **赋值支持批量**（`assign_batch`，默认 10 段/次）降调用量；解析失败重试+标记 `unparsed`。
- **`para_id` 一律按字符串处理**（源里可能是整数，模型可能回字符串，需 `str()` 归一，否则赋值全 missing）。

## §3 离线自检（不用 key 也能验证管线）

`llm_client.py` 内置 **mock 客户端**，返回确定性假 JSON：

```bash
cd scripts
python self_check.py           # 生成→赋值→归纳→映射 全链路跑通（假数据）
```

预期输出：`生成(2主题) → 赋值(25/25 ok) → 归纳(2 L1) → 映射(2)`。任何一步文件 I/O 或 JSON 解析报错都在此暴露。

## §4 框架映射（方法之外的分析层）

**映射不是 TopicGPT 的一部分**，是产出主题树后的**后置分析**：
- 映射到 **OAIS 六功能**（Ingest / ArchivalStorage / DataManagement / PreservationPlanning / Access / Administration）→ 输出各功能覆盖率，暴露供给缺口（如"保存规划"常最低）。
- 映射到**自定义治理模型**（如 4 层：目标承诺/治理配置/行动工具/评估反馈）→ 支撑论文模型章节。**同一主题树换映射表即可，无需重跑生成/赋值**。

改 `scripts/prompts/map.txt` 的"目标框架"段即可切换框架。映射含主观判断，**须在方法章报告指派规则并保证可复核**（补"编码信度未报告"的缺口）。

## §5 可复现性与 Model 规定

- **无模型品牌强制**：TopicGPT 是模型无关框架（论文用"LLM"泛指）。**国内模型可用且对中文语料更优**（合规、可私有化）。
- **本管线默认 DeepSeek**（OpenAI 兼容）。真跑需：
  - 获取 key：登录 `https://platform.deepseek.com/`（手机/微信）→ 左侧「API keys」→「Create new API key」→ **立即复制**（只显示一次）→ 在「充值」充几元。
  - 环境变量：`export DEEPSEEK_API_KEY=sk-xxxx`（**不落盘、不进版本库**）。
  - `config.json`：`model=deepseek-v4-flash`、`base_url=https://api.deepseek.com`。
- **必报项**：冻结模型+版本、temperature（生成 0.3 / 赋值 0）、prompt 模板、抽样 seed、迭代轮次、**稳定性复跑**（200 段跑 2 次比主题重合度）。
- **坑**：LLM 迭代生成有 **anchoring bias**（被首轮主题锚定）→ 多轮/多次运行取稳定结构并在方法章说明。

## §6 BERTopic 三角验证（可选，独立于 API）

同类语料跑 BERTopic（bge 嵌入→UMAP→HDBSCAN→c-TF-IDF），与 TopicGPT 主题对齐（ARI/NMI + 人工对齐表）。两种独立方法析出相似结构 → 强化"透明/可复现"论证。**此步才用词级停用词表**（c-TF-IDF 表征）。需 `pip install bertopic sentence-transformers`。

## 配置

编辑 `scripts/config.json` 的 `paths`（语料源、输出目录）与 `model`。脚本从**自身所在目录**读取 `config.json` 与 `prompts/`，故运行前 `cd` 到 `scripts/`（或设 `PYTHONPATH`）。
