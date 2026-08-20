# Block Anchor Spec（块锚定规范）

前后端共享的 Markdown 块切分、归一化、hash、迁移状态规范。后端实现见
`app/services/block_parser.py`，前端 remark-gfm 渲染必须对齐本规范；共享测试
夹具在 `backend/tests/fixtures/block_anchor/`（`.md` 源码 + `.json` 期望块列表）。

## 1. 解析器配置

- 引擎：`markdown-it-py`，preset `commonmark`，启用 `table` 与 `mdit-py-plugins.tasklists`。
- `html=True`：保留原始 HTML（`html_block` / `html_inline`），取 raw 字符串而非渲染 DOM。
- `breaks=False`：源码单个换行是 softbreak（保留为 `\n`），不是 `<br>`。

前端对应：`remark` + `remark-gfm` + `remark-html`（或 react-markdown），`breaks: false`（默认）。

## 2. 块粒度

**顶层块各一块，容器整体拍平。** 按顶层 token 顺序，每个顶层块产出一条
`ParsedBlock`：

| 顶层 token | block_path tag | 文本提取 |
|---|---|---|
| `heading_open` | `h1`/`h2`/...:`<heading 文本>` | inline 文本（见 §3） |
| `paragraph_open` | `p[<n>]` | inline 文本 |
| `fence` / `code_block` | `code[<n>]` | `tok.content`（**不含** lang 信息） |
| `bullet_list_open` / `ordered_list_open` | `list[<n>]` | 递归拍平所有 list_item，item 间 `\n` |
| `blockquote_open` | `quote[<n>]` | 递归拍平容器内块，块间 `\n` |
| `table_open` | `table[<n>]` | 行内 cell 用 ` \| ` 连接，行间 `\n` |
| `hr` | `hr[<n>]` | 固定占位 `"hr"`（markup 不稳定，不参与行内评论） |
| `html_block` | `html[<n>]` | `tok.content`（raw HTML） |

**block_path 命名规则**：
- heading 块：`<tag>:<heading 文本截断 60 字符>`，例如 `h2:Title`、`h1:Title Here`。
- 非 heading 块：`<tag>[<在该 heading 作用域内的序号>]`，序号从 0 起，按 tag 独立计数。
- 若处于某 heading 作用域下：`<heading_path> > <tag>[<n>]`，例如 `h1:Title > p[0]`。
- 遇到新 heading 时，tag 计数器清零。

**容器拍平**：list / blockquote 内的子块不单独成块，整体作为父容器块的一段
文本（子块文本用 `\n` 连接）。例如：

```markdown
- a
  - b
  - c
- d
```

→ 单个 `list[0]` 块，`block_text = "a\nb\nc\nd"`。

**source 行号**：`source_start_line = tok.map[0] + 1`，`source_end_line = tok.map[1]`
（markdown-it map 是 0-based 半开区间 `[start, end)`，转 1-based 闭区间，与 remark
`position.start.line` / `position.end.line` 对齐）。注意：DB 中的
`artifact_version_block` 表当前**不持久化** source 行号，只存 `block_id` /
`block_path` / `block_index` / `block_text`。

## 3. 文本归一化

块的 `block_text` 由其 inline / 容器文本经 `_normalize` 得到：

```python
def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").strip()
```

**inline 文本提取规则**（`_extract_inline_text`）：

| 子 token | 处理 |
|---|---|
| `text` | 取 `content` |
| `softbreak` | 插入 `\n`（保留软换行） |
| `hardbreak` | **丢弃**（两侧文本直接拼接，不插入分隔符） |
| `code_inline` | 取 `content`（去反引号） |
| `html_inline` | 取 `content`（raw）；tasklist checkbox 标记跳过 |
| `image` | 递归提取 alt 文本 |

**代码块**：`fence` / `code_block` 只取 `tok.content`（即代码体），**不含 lang 标识**。
因此 ` ```python\nx=1 ` 与 ` ```\nx=1 ` 产生相同 `block_id`。

**GFM 任务清单**：`mdit-py-plugins.tasklists` 把 `[ ]` / `[x]` 替换为 `<input>`
checkbox 元素。提取文本时跳过带 `task-list-item-checkbox` class 的 `html_inline`，
并对每个 list_item 做 `.strip()`，与前端 `remark-gfm`（剥标记后无前导空格）对齐。

例：`- [ ] todo\n- [x] done` → `block_text = "todo\ndone"`。

## 4. Hash 算法

```python
block_id = sha256(normalize(block_text).encode("utf-8")).hexdigest()[:16]
```

- 输入：归一化后的 `block_text`（`\r\n`→`\n` + `strip()`）。
- 输出：sha256 hex 的前 16 字符。
- `block_id` 与内容唯一对应，与位置无关：相同内容块在不同 heading / 位置下
  `block_id` 相同。

## 5. block_index

`block_index` 是该块在版本块列表中的顺序索引（从 0 起），按源码出现顺序递增。
前端可用 `block_index` 与后端返回的 block 列表按序匹配顶层 DOM 节点。

## 6. migration_status 语义

行内评论锚定到某旧版本的块（`block_id` + `block_path` + `block_text` 快照存于
`feedback.inline_anchor`）。列表评论时，以"当前查看版本"的 block map 为基准，
在线计算迁移状态（不持久化）：

| status | 含义 | 判定 |
|---|---|---|
| `exact` | 块在新版本中完全匹配 | `old_block_id` 出现在新版本 block map 中（hash 命中） |
| `fuzzy` | 块在新版本中位置匹配、内容小幅修改 | `block_id` 未命中，但 `block_path` 命中且文本相似度 `≥ 0.6`（`difflib.SequenceMatcher`） |
| `stale` | 块在新版本中已无法定位 | `block_path` 也未命中，或相似度 `< 0.6` |

- `FUZZY_SIMILARITY_THRESHOLD = 0.6`。
- 旧块文本快照来自 `feedback.inline_anchor.block_text`（创建评论时从 block 记录锁定）。
- 版本级评论（无 `block_id`）不计算 `migration_status`，返回 `null`。

## 7. 前后端对齐

- 后端 `parse_blocks(content)` → `list[ParsedBlock]`，publish / add_version / fork
  时同事务写入 `artifact_version_block` 表。
- 前端加载版本内容后，调用 `GET /artifacts/{artifact_id}/versions/{version_no}/blocks`
  拿到该版本 block 列表（`block_id` / `block_path` / `block_index` / `block_text` /
  `content_preview`），用 `block_index` 按顶层块顺序注入 `data-block-id` 到对应 DOM 节点。
- 共享夹具：`backend/tests/fixtures/block_anchor/*.md` + `*.json`，前端可用相同输入
  验证自身切分逻辑与后端一致（block_count / block_id / block_path / block_text）。
