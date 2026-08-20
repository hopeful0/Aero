import json
import pathlib

import pytest

from app.services.block_parser import (
    ParsedBlock,
    compute_block_id,
    compute_migration_status,
    parse_blocks,
)

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures" / "block_anchor"


def _load_fixture(name: str) -> tuple[str, dict]:
    md_path = FIXTURES_DIR / name
    json_path = md_path.with_suffix(".json")
    content = md_path.read_text()
    expected = json.loads(json_path.read_text())
    return content, expected


@pytest.mark.parametrize(
    "md_name",
    sorted(p.name for p in FIXTURES_DIR.glob("*.md")),
)
def test_parse_blocks_matches_fixture(md_name):
    content, expected = _load_fixture(md_name)
    blocks = parse_blocks(content)
    assert len(blocks) == expected["block_count"]
    for block, exp in zip(blocks, expected["blocks"], strict=True):
        assert block.block_index == exp["block_index"]
        assert block.block_id == exp["block_id"]
        assert block.block_path == exp["block_path"]
        assert block.block_text == exp["block_text"]
        assert block.content_preview == exp["content_preview"]
        assert block.source_start_line == exp["source_start_line"]
        assert block.source_end_line == exp["source_end_line"]


def test_block_id_is_sha256_prefix_of_normalized_text():
    text = "  Hello\nWorld  "
    assert compute_block_id(text) == compute_block_id("Hello\nWorld")
    assert len(compute_block_id(text)) == 16


def test_block_id_stable_across_reordering():
    content = "## Section A\n\nPara A.\n\n## Section B\n\nPara B.\n"
    blocks = parse_blocks(content)
    # 段落重排（内容不变换位置）—— hash 应与内容唯一对应，重排后 block_id 不变。
    reordered = "## Section B\n\nPara B.\n\n## Section A\n\nPara A.\n"
    reordered_blocks = parse_blocks(reordered)
    reordered_by_text = {b.block_text: b.block_id for b in reordered_blocks}
    for b in blocks:
        assert b.block_id == reordered_by_text[b.block_text]


def test_inline_code_strips_backticks():
    blocks = parse_blocks("Use `code` here.\n")
    assert blocks[0].block_text == "Use code here."


def test_fence_excludes_lang_from_hash():
    py_block = parse_blocks("```python\nx = 1\n```\n")[0]
    plain_block = parse_blocks("```\nx = 1\n```\n")[0]
    assert py_block.block_id == plain_block.block_id
    assert py_block.block_text == "x = 1"


def test_tasklist_strips_checkbox_marker():
    blocks = parse_blocks("- [ ] todo\n- [x] done\n")
    assert blocks[0].block_text == "todo\ndone"


def test_softbreak_preserved_hardbreak_dropped():
    blocks = parse_blocks("soft  \nbreak\n")  # 硬换行（两空格+换行）
    assert blocks[0].block_text == "softbreak"
    soft_only = parse_blocks("line one\nline two\n")
    assert soft_only[0].block_text == "line one\nline two"


def test_html_block_raw_content():
    blocks = parse_blocks("<div class=\"x\">raw</div>\n")
    assert blocks[0].block_text == '<div class="x">raw</div>'


def test_nested_list_flattened():
    blocks = parse_blocks("- a\n  - b\n  - c\n- d\n")
    assert blocks[0].block_text == "a\nb\nc\nd"


def test_table_cell_join():
    blocks = parse_blocks("| h1 | h2 |\n|----|----|\n| 1  | 2  |\n")
    assert blocks[0].block_text == "h1 | h2\n1 | 2"


def test_block_path_resets_counter_on_new_heading():
    blocks = parse_blocks("## A\n\ntext.\n\n## B\n\ntext.\n")
    paths = [b.block_path for b in blocks]
    assert paths == ["h2:A", "h2:A > p[0]", "h2:B", "h2:B > p[0]"]


def test_migration_status_exact():
    old = parse_blocks("## A\n\nhello world\n")[1]
    new_blocks = parse_blocks("## A\n\nhello world\n")
    assert (
        compute_migration_status(old.block_id, old.block_path, old.block_text, new_blocks)
        == "exact"
    )


def test_migration_status_stale_on_deletion():
    old = parse_blocks("## A\n\nhello world\n")[1]
    new_blocks = parse_blocks("## A\n\ntotally different content here\n")
    # block_path 相同但内容相似度低 -> stale
    assert (
        compute_migration_status(old.block_id, old.block_path, old.block_text, new_blocks)
        == "stale"
    )


def test_migration_status_fuzzy_on_minor_edit():
    old = parse_blocks("## A\n\nhello world this is a longer paragraph\n")[1]
    new_blocks = parse_blocks("## A\n\nhello world this is a longer paragraph edited\n")
    status = compute_migration_status(
        old.block_id, old.block_path, old.block_text, new_blocks
    )
    assert status == "fuzzy"


def test_migration_status_stale_on_path_mismatch():
    old = parse_blocks("## A\n\nhello\n")[1]
    # 不同 heading + 不同内容：block_id 失配，block_path 也失配 -> stale。
    new_blocks = parse_blocks("## B\n\nworld\n")
    assert (
        compute_migration_status(old.block_id, old.block_path, old.block_text, new_blocks)
        == "stale"
    )


def test_migration_status_exact_when_content_unchanged_across_heading():
    # 内容不变换到不同 heading 下：block_id 命中 -> exact（hash 与位置无关）。
    old = parse_blocks("## A\n\nhello\n")[1]
    new_blocks = parse_blocks("## B\n\nhello\n")
    assert (
        compute_migration_status(old.block_id, old.block_path, old.block_text, new_blocks)
        == "exact"
    )


def test_parsed_block_preview_truncates():
    long_text = "x" * 200
    block = ParsedBlock(
        block_id="abc",
        block_path="p[0]",
        block_index=0,
        block_text=long_text,
        source_start_line=1,
        source_end_line=1,
    )
    assert len(block.content_preview) == 80
