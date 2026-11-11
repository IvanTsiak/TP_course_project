from pathlib import Path
from lark import Lark

GRAMMAR_PATH = Path(__file__).parent.parent.parent / "grammar" / "sipl.lark"

def get_parser(parser_type: str = "earley") -> Lark:
    with open(GRAMMAR_PATH, "r", encoding="utf-8") as f:
        grammar_content = f.read()
    return Lark(grammar_content, start="program", parser=parser_type)

def parse_sipl(code: str):
    parser = get_parser()
    return parser.parse(code)