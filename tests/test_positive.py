import pytest
from sipl.syntax import parse_sipl

VALID_PROGRAMS = [
    "begin skip end",

    "begin R := 1 end",

    "begin X := 5; Y := 10 end",

    "begin if X > 0 then R := 1 else R := 0 end",

    "begin while Y > 0 do Y := Y - 1 end",

    "begin begin X := 1 end end",

    "begin R := (X + Y) * 2 - 1 end",

    "begin if not (X = Y) or X > Y then skip else skip end",

    "begin Z := -10 end",

    """
    begin
        R := 1;
        while Y > 0 do
        begin
            R := R * X;
            Y := Y - 1
        end
    end
    """
]


@pytest.mark.parametrize("code", VALID_PROGRAMS)
def test_valid_sipl_syntax(code):
    tree = parse_sipl(code)
    assert tree is not None