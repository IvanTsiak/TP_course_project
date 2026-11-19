import html
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from lark import Lark, Token, Tree
from lark.exceptions import UnexpectedCharacters, UnexpectedInput, UnexpectedToken

from sipl.parser import GRAMMAR_PATH, SIPLSyntaxError

OutputFormat = Literal["text", "json", "dot", "svg"]

@dataclass
class ParseTreeNode:
    node_id: str
    kind: Literal["rule", "token"]
    label: str
    span: dict[str, int] | None
    source_fragment: str
    token_type: str | None = None
    children: list["ParseTreeNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_parse_tree_parser() -> Lark:
    grammar_content = GRAMMAR_PATH.read_text(encoding="utf-8")
    return Lark(
        grammar_content,
        start="program",
        parser="lalr",
        propagate_positions=True,
        keep_all_tokens=True,
    )


def build_parse_tree(code: str) -> ParseTreeNode:
    parser = get_parse_tree_parser()
    try:
        raw_tree = parser.parse(code)
    except UnexpectedToken as e:
        expected = ", ".join(e.expected)
        msg = f"Unexpected token '{e.token.value}'. Expected one of: {expected}"
        raise SIPLSyntaxError(msg, e.line, e.column) from e
    except UnexpectedCharacters as e:
        msg = f"Unexpected character '{e.char}'"
        raise SIPLSyntaxError(msg, e.line, e.column) from e
    except UnexpectedInput as e:
        raise SIPLSyntaxError(str(e).split("\n")[0], e.line, e.column) from e

    counter = 0

    def _convert(node: Tree[Any] | Token) -> ParseTreeNode:
        nonlocal counter
        current_id = f"pt_{counter}"
        counter += 1

        if isinstance(node, Token):
            span: dict[str, int] | None = None
            if node.line is not None and node.column is not None:
                span = {
                    "line": node.line,
                    "column": node.column,
                    "end_line": node.end_line or node.line,
                    "end_column": node.end_column or node.column,
                }
            fragment = (
                code[node.start_pos : node.end_pos]
                if node.start_pos is not None and node.end_pos is not None
                else str(node.value)
            )
            return ParseTreeNode(
                node_id=current_id,
                kind="token",
                label=str(node.value),
                span=span,
                source_fragment=fragment,
                token_type=str(node.type),
                children=[],
            )

        rule_name = str(node.data)
        rule_span: dict[str, int] | None = None
        rule_fragment = ""
        if not getattr(node.meta, "empty", True):
            rule_span = {
                "line": node.meta.line,
                "column": node.meta.column,
                "end_line": node.meta.end_line,
                "end_column": node.meta.end_column,
            }
            if node.meta.start_pos is not None and node.meta.end_pos is not None:
                rule_fragment = code[node.meta.start_pos : node.meta.end_pos]

        children = [_convert(child) for child in node.children]
        return ParseTreeNode(
            node_id=current_id,
            kind="rule",
            label=rule_name,
            span=rule_span,
            source_fragment=rule_fragment,
            token_type=None,
            children=children,
        )

    return _convert(raw_tree)


def _compact_snippet(text: str, max_len: int = 32) -> str:
    single_line = " ".join(text.split())
    if len(single_line) <= max_len:
        return single_line
    return f"{single_line[: max_len - 3]}..."


def _format_span_tag(span: dict[str, int] | None) -> str:
    if span is None:
        return ""
    return f"[{span['line']}:{span['column']}-{span['end_line']}:{span['end_column']}]"


def format_parse_tree_text(root: ParseTreeNode) -> str:
    lines: list[str] = []

    def _walk(node: ParseTreeNode, prefix: str, is_last: bool, is_root: bool) -> None:
        connector = "" if is_root else ("└── " if is_last else "├── ")
        span_tag = _format_span_tag(node.span)
        snippet = _compact_snippet(node.source_fragment)

        if node.kind == "token":
            desc = f"TOKEN({node.token_type}): {node.label!r} {span_tag}"
        else:
            desc = f"<{node.label}> {span_tag} -> {snippet!r}"

        lines.append(f"{prefix}{connector}{desc}")
        child_prefix = "" if is_root else prefix + ("    " if is_last else "│   ")
        for idx, child in enumerate(node.children):
            _walk(child, child_prefix, idx == len(node.children) - 1, False)

    _walk(root, "", True, True)
    return "\n".join(lines)


def format_parse_tree_json(root: ParseTreeNode, indent: int | None = 2) -> str:
    return json.dumps(root.to_dict(), indent=indent, ensure_ascii=False)


def _escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def format_parse_tree_dot(root: ParseTreeNode) -> str:
    lines: list[str] = [
        "digraph ParseTree {",
        '  rankdir="TB";',
        '  node [fontname="Consolas,monospace", fontsize=10];',
        '  edge [color="#64748b"];',
    ]

    def _walk(node: ParseTreeNode) -> None:
        span_tag = _format_span_tag(node.span)
        snippet = _compact_snippet(node.source_fragment, max_len=24)

        if node.kind == "token":
            raw_label = f"{node.label}\\n({node.token_type}) {span_tag}"
            lines.append(
                f'  {node.node_id} [label="{_escape_dot(raw_label)}", '
                'shape=box, style="rounded,filled", fillcolor="#dcfce7", color="#16a34a"];'
            )
        else:
            raw_label = f"<{node.label}>\\n{span_tag}\\n{snippet}"
            lines.append(
                f'  {node.node_id} [label="{_escape_dot(raw_label)}", '
                'shape=ellipse, style="filled", fillcolor="#e0f2fe", color="#0284c7"];'
            )

        for child in node.children:
            lines.append(f"  {node.node_id} -> {child.node_id};")
            _walk(child)

    _walk(root)
    lines.append("}")
    return "\n".join(lines)


def format_parse_tree_svg(root: ParseTreeNode) -> str:
    box_w = 136
    box_h = 46
    h_gap = 18
    v_gap = 74
    margin = 24

    positions: dict[str, tuple[float, float]] = {}
    leaf_cursor = 0

    def _assign_coords(node: ParseTreeNode, depth: int) -> float:
        nonlocal leaf_cursor
        y = float(margin + depth * v_gap)
        if not node.children:
            x = float(margin + leaf_cursor * (box_w + h_gap))
            leaf_cursor += 1
            positions[node.node_id] = (x, y)
            return x

        child_xs = [_assign_coords(child, depth + 1) for child in node.children]
        x = (child_xs[0] + child_xs[-1]) / 2.0
        positions[node.node_id] = (x, y)
        return x

    _assign_coords(root, 0)

    max_x = max((pos[0] for pos in positions.values()), default=0.0)
    max_y = max((pos[1] for pos in positions.values()), default=0.0)
    width = int(max_x + box_w + margin)
    height = int(max_y + box_h + margin)

    svg_parts: list[str] = [
        (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'),
        "  <style>",
        "    .edge { stroke: #64748b; stroke-width: 1.5; fill: none; }",
        "    .rule-box { fill: #e0f2fe; stroke: #0284c7; stroke-width: 1.5; }",
        "    .token-box { fill: #dcfce7; stroke: #16a34a; stroke-width: 1.5; }",
        "    .title { font: bold 11px monospace; fill: #0f172a; text-anchor: middle; }",
        "    .meta { font: 9px monospace; fill: #475569; text-anchor: middle; }",
        "  </style>",
    ]

    def _render_edges(node: ParseTreeNode) -> None:
        px, py = positions[node.node_id]
        start_x = px + box_w / 2.0
        start_y = py + box_h
        for child in node.children:
            cx, cy = positions[child.node_id]
            end_x = cx + box_w / 2.0
            end_y = cy
            svg_parts.append(
                f'  <line class="edge" x1="{start_x:.1f}" y1="{start_y:.1f}" '
                f'x2="{end_x:.1f}" y2="{end_y:.1f}" />'
            )
            _render_edges(child)

    def _render_nodes(node: ParseTreeNode) -> None:
        x, y = positions[node.node_id]
        cx = x + box_w / 2.0
        box_class = "token-box" if node.kind == "token" else "rule-box"
        rx = 4 if node.kind == "token" else 14

        title_text = (
            html.escape(_compact_snippet(node.label, max_len=16))
            if node.kind == "token"
            else html.escape(f"<{node.label}>")
        )
        span_tag = _format_span_tag(node.span)
        meta_text = html.escape(
            f"{node.token_type} {span_tag}".strip() if node.kind == "token" else span_tag
        )

        svg_parts.append(
            f'  <g id="{node.node_id}">'
            f'<rect class="{box_class}" x="{x:.1f}" y="{y:.1f}" '
            f'width="{box_w}" height="{box_h}" rx="{rx}" />'
            f'<text class="title" x="{cx:.1f}" y="{y + 19:.1f}">{title_text}</text>'
            f'<text class="meta" x="{cx:.1f}" y="{y + 35:.1f}">{meta_text}</text>'
            "</g>"
        )
        for child in node.children:
            _render_nodes(child)

    _render_edges(root)
    _render_nodes(root)
    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def visualize_parse_tree(code: str, fmt: OutputFormat = "text") -> str:
    tree = build_parse_tree(code)
    if fmt == "text":
        return format_parse_tree_text(tree)
    if fmt == "json":
        return format_parse_tree_json(tree)
    if fmt == "dot":
        return format_parse_tree_dot(tree)
    if fmt == "svg":
        return format_parse_tree_svg(tree)
    raise ValueError(f"Unsupported visualization format: {fmt}")