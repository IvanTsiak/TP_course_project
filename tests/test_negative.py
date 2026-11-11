import pytest
from lark.exceptions import LarkError
from sipl.syntax import parse_sipl

INVALID_PROGRAMS = [
    "R := 1; end",

    "begin R := 1",

    "begin R = 1 end",

    "begin end",

    "begin X := 1;; Y := 2 end",

    "begin if X > 0 R := 1 else R := 0 end",

    "begin if X > 0 then R := 1 end",

    "begin while X > 0 R := 1 end",

    "begin X := (1 + 2 end",

    "begin @X := 5 end"
]


@pytest.mark.parametrize("code", INVALID_PROGRAMS)
def test_invalid_sipl_syntax(code):
    with pytest.raises(LarkError):
        parse_sipl(code)