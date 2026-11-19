import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from sipl import (
    SIPLSyntaxError,
    build_parse_tree,
    visualize_parse_tree,
)
from sipl.cli import main as cli_main

SAMPLE_CODE = """begin
    R := 1;
    while Y > 0 do
    begin
        R := R * X;
        Y := Y - 1
    end
end"""


def _collect_leaves(node) -> list[str]:
    if not node.children:
        return [node.label]
    result: list[str] = []
    for child in node.children:
        result.extend(_collect_leaves(child))
    return result


def test_parse_tree_links_to_source_fragments():
    tree = build_parse_tree("begin R := 1 end")
    assert tree.label == "program"
    assert tree.source_fragment == "begin R := 1 end"
    assert tree.span == {"line": 1, "column": 1, "end_line": 1, "end_column": 17}

    # Перевірка обходу листків зліва направо (як у Практичній роботі 1)
    leaves = _collect_leaves(tree)
    assert leaves == ["begin", "R", ":=", "1", "end"]


def test_parse_tree_text_format():
    text_out = visualize_parse_tree(SAMPLE_CODE, fmt="text")
    assert "<program>" in text_out
    assert "<while_stmt>" in text_out
    assert "TOKEN(VAR): 'R'" in text_out
    assert "[1:1-8:4]" in text_out


def test_parse_tree_json_format():
    json_out = visualize_parse_tree(SAMPLE_CODE, fmt="json")
    data = json.loads(json_out)

    assert data["node_id"] == "pt_0"
    assert data["kind"] == "rule"
    assert data["label"] == "program"
    assert data["source_fragment"] == SAMPLE_CODE
    assert len(data["children"]) == 3


def test_parse_tree_dot_format():
    dot_out = visualize_parse_tree(SAMPLE_CODE, fmt="dot")
    assert dot_out.startswith("digraph ParseTree {")
    assert dot_out.endswith("}")
    assert "pt_0 -> pt_1;" in dot_out
    assert "<assign_stmt>" in dot_out


def test_parse_tree_svg_format_is_valid_xml():
    svg_out = visualize_parse_tree(SAMPLE_CODE, fmt="svg")
    root = ET.fromstring(svg_out)
    assert root.tag.endswith("svg")
    assert int(root.attrib["width"]) > 0
    assert int(root.attrib["height"]) > 0


def test_parse_tree_syntax_error():
    with pytest.raises(SIPLSyntaxError):
        visualize_parse_tree("begin X = 1 end", fmt="dot")


def test_cli_parse_tree_export(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    sipl_file = tmp_path / "simple.sipl"
    sipl_file.write_text("begin X := 42 end", encoding="utf-8")

    exit_code = cli_main([str(sipl_file), "--parse-tree", "dot"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "digraph ParseTree" in captured.out