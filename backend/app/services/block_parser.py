"""Markdown 块切分与 hash 锚定解析。

块粒度、归一化规则、hash 算法、GFM 任务清单处理见
``backend/docs/block-anchor-spec.md``。前端 remark-gfm 渲染必须对齐本模块的
切分约定，共享测试夹具在 ``backend/tests/fixtures/block_anchor/``。
"""

from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin

# commonmark 不含 table；显式启用 table 与 tasklists，与前端 remark-gfm 对齐。
# breaks=False：源码中的单个换行是 softbreak（保留为 \n），而非 <br>。
# html=True：保留原始 HTML（html_block/html_inline），取 raw 字符串而非渲染 DOM。
_MD = (
    MarkdownIt("commonmark", {"html": True, "breaks": False})
    .use(tasklists_plugin)
    .enable("table")
)

# fuzzy 兜底的内容相似度阈值：block_path 命中后，旧/新块文本相似度不低于此值才算 fuzzy。
FUZZY_SIMILARITY_THRESHOLD = 0.6

# block_path 中 heading 文本截断长度。
HEADING_LABEL_MAX = 60

# content_preview 截断长度。
PREVIEW_MAX = 80

# tasklist 插件注入的 checkbox 元素 class 标记，提取文本时跳过。
_TASKLIST_CHECKBOX_MARK = "task-list-item-checkbox"


@dataclass(frozen=True)
class ParsedBlock:
    block_id: str
    block_path: str
    block_index: int
    block_text: str
    source_start_line: int
    source_end_line: int

    @property
    def content_preview(self) -> str:
        return self.block_text[:PREVIEW_MAX]


def parse_blocks(content: str) -> list[ParsedBlock]:
    """解析 markdown content，返回顶层块列表（含 block_id / block_path / 源码行号）。"""
    tokens = _MD.parse(content)
    blocks: list[ParsedBlock] = []
    last_heading_path: str | None = None
    tag_counters: dict[str, int] = {}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        t = tok.type
        if t == "heading_open":
            text = _extract_inline_text(tokens[i + 1])
            close = _find_close(tokens, i, "heading_close")
            label = text.strip()[:HEADING_LABEL_MAX]
            path = f"{tok.tag}:{label}"
            last_heading_path = path
            tag_counters = {}
            _append_block(blocks, path, text, tok.map)
            i = close + 1
        elif t == "paragraph_open":
            text = _extract_inline_text(tokens[i + 1])
            close = _find_close(tokens, i, "paragraph_close")
            _append_block(blocks, _make_path("p", last_heading_path, tag_counters), text, tok.map)
            i = close + 1
        elif t in ("fence", "code_block"):
            path = _make_path("code", last_heading_path, tag_counters)
            _append_block(blocks, path, tok.content, tok.map)
            i += 1
        elif t in ("bullet_list_open", "ordered_list_open"):
            close = _find_close(tokens, i, t.replace("_open", "_close"))
            text = _extract_list_text(tokens, i + 1, close)
            path = _make_path("list", last_heading_path, tag_counters)
            _append_block(blocks, path, text, tok.map)
            i = close + 1
        elif t == "blockquote_open":
            close = _find_close(tokens, i, "blockquote_close")
            text = _extract_container_text(tokens, i + 1, close)
            path = _make_path("quote", last_heading_path, tag_counters)
            _append_block(blocks, path, text, tok.map)
            i = close + 1
        elif t == "table_open":
            close = _find_close(tokens, i, "table_close")
            text = _extract_table_text(tokens, i + 1, close)
            path = _make_path("table", last_heading_path, tag_counters)
            _append_block(blocks, path, text, tok.map)
            i = close + 1
        elif t == "hr":
            # hr 无文本内容，markup 在 markdown-it-py 下不稳定（`---`→`----`），
            # 用固定占位与前端 remark 对齐；hr 不参与行内评论，block_id 重复可接受。
            _append_block(blocks, _make_path("hr", last_heading_path, tag_counters), "hr", tok.map)
            i += 1
        elif t == "html_block":
            path = _make_path("html", last_heading_path, tag_counters)
            _append_block(blocks, path, tok.content, tok.map)
            i += 1
        else:
            i += 1
    return blocks


def compute_block_id(text: str) -> str:
    return hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()[:16]


def compute_migration_status(
    old_block_id: str,
    old_block_path: str,
    old_block_text: str,
    new_blocks: list[ParsedBlock],
) -> str:
    """在线计算锚点迁移状态：exact / fuzzy / stale。"""
    by_id = {b.block_id: b for b in new_blocks}
    if old_block_id in by_id:
        return "exact"
    by_path: dict[str, ParsedBlock] = {}
    for b in new_blocks:
        by_path.setdefault(b.block_path, b)
    candidate = by_path.get(old_block_path)
    if candidate is None:
        return "stale"
    ratio = difflib.SequenceMatcher(None, old_block_text, candidate.block_text).ratio()
    if ratio >= FUZZY_SIMILARITY_THRESHOLD:
        return "fuzzy"
    return "stale"


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def _compute_id(normalized_text: str) -> str:
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()[:16]


def _make_path(tag: str, last_heading_path: str | None, tag_counters: dict[str, int]) -> str:
    count = tag_counters.get(tag, 0)
    tag_counters[tag] = count + 1
    if last_heading_path:
        return f"{last_heading_path} > {tag}[{count}]"
    return f"{tag}[{count}]"


def _append_block(
    blocks: list[ParsedBlock],
    path: str,
    text: str,
    token_map: list[int] | None,
) -> None:
    normalized = _normalize(text)
    # markdown-it map 是 0-based 半开区间 [start, end)；转 1-based 闭区间行号，
    # 与 remark position.start.line / end.line 对齐：start = map[0]+1, end = map[1]。
    start_line = (token_map[0] + 1) if token_map else 0
    end_line = token_map[1] if token_map else 0
    blocks.append(
        ParsedBlock(
            block_id=_compute_id(normalized),
            block_path=path,
            block_index=len(blocks),
            block_text=normalized,
            source_start_line=start_line,
            source_end_line=end_line,
        )
    )


def _find_close(tokens, open_idx: int, close_type: str) -> int:
    open_type = close_type.replace("_close", "_open")
    depth = 1
    i = open_idx + 1
    while i < len(tokens):
        t = tokens[i].type
        if t == open_type:
            depth += 1
        elif t == close_type:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError(f"unbalanced markdown tokens: {close_type} not found")


def _extract_inline_text(inline_token) -> str:
    parts: list[str] = []
    for child in inline_token.children or []:
        t = child.type
        if t == "text":
            parts.append(child.content)
        elif t == "softbreak":
            parts.append("\n")
        elif t == "hardbreak":
            # 硬换行丢弃：两侧文本直接拼接，不插入分隔符。
            continue
        elif t == "code_inline":
            parts.append(child.content)
        elif t == "html_inline":
            if _TASKLIST_CHECKBOX_MARK in child.content:
                continue
            parts.append(child.content)
        elif t == "image":
            parts.append(_extract_inline_text(child))
    return "".join(parts)


def _extract_list_text(tokens, start: int, end: int) -> str:
    items: list[str] = []
    i = start
    while i < end:
        if tokens[i].type == "list_item_open":
            item_end = _find_close(tokens, i, "list_item_close")
            # tasklist 插件把 `[ ]`/`[x]` 替换为 <input>，留下前导空格；
            # strip 每个 item 与前端 remark-gfm（剥标记后无前导空格）对齐。
            items.append(_extract_container_text(tokens, i + 1, item_end).strip())
            i = item_end + 1
        else:
            i += 1
    return "\n".join(items)


def _extract_container_text(tokens, start: int, end: int) -> str:
    """递归拍平容器（list_item / blockquote）内的块文本，块间用 \\n 连接。"""
    parts: list[str] = []
    i = start
    while i < end:
        tok = tokens[i]
        t = tok.type
        if t == "paragraph_open":
            parts.append(_extract_inline_text(tokens[i + 1]))
            i = _find_close(tokens, i, "paragraph_close") + 1
        elif t == "heading_open":
            parts.append(_extract_inline_text(tokens[i + 1]))
            i = _find_close(tokens, i, "heading_close") + 1
        elif t in ("fence", "code_block"):
            parts.append(tok.content)
            i += 1
        elif t in ("bullet_list_open", "ordered_list_open"):
            close = _find_close(tokens, i, t.replace("_open", "_close"))
            parts.append(_extract_list_text(tokens, i + 1, close))
            i = close + 1
        elif t == "blockquote_open":
            close = _find_close(tokens, i, "blockquote_close")
            parts.append(_extract_container_text(tokens, i + 1, close))
            i = close + 1
        elif t == "table_open":
            close = _find_close(tokens, i, "table_close")
            parts.append(_extract_table_text(tokens, i + 1, close))
            i = close + 1
        elif t == "hr":
            parts.append("hr")
            i += 1
        elif t == "html_block":
            parts.append(tok.content)
            i += 1
        else:
            i += 1
    return "\n".join(parts)


def _extract_table_text(tokens, start: int, end: int) -> str:
    rows: list[str] = []
    i = start
    while i < end:
        if tokens[i].type == "tr_open":
            tr_end = _find_close(tokens, i, "tr_close")
            cells: list[str] = []
            j = i + 1
            while j < tr_end:
                cell_tok = tokens[j]
                if cell_tok.type in ("th_open", "td_open"):
                    close_type = "th_close" if cell_tok.type == "th_open" else "td_close"
                    cells.append(_extract_inline_text(tokens[j + 1]))
                    j = _find_close(tokens, j, close_type) + 1
                else:
                    j += 1
            rows.append(" | ".join(cells))
            i = tr_end + 1
        else:
            i += 1
    return "\n".join(rows)
