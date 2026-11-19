import pytest
from sipl import (
    run_sipl,
    parse_sipl,
    SIPLInterpreter,
    SIPLSyntaxError,
    UndefinedVariableError,
    StepLimitExceededError,
)


def test_skip_preserves_state():
    state = run_sipl("begin skip end", {"X": 42})
    assert state == {"X": 42}


def test_assignment_and_arithmetic_precedence():
    code = """
    begin
        A := 2 + 3 * 4;
        B := (2 + 3) * 4 - 10;
        C := -5 + A
    end
    """
    state = run_sipl(code)
    assert state == {"A": 14, "B": 10, "C": 9}


def test_if_then_else_and_boolean_ops():
    code = """
    begin
        if not (X = 0) or Y > 10 then
            R := 1
        else
            R := 0
    end
    """
    assert run_sipl(code, {"X": 0, "Y": 5})["R"] == 0
    assert run_sipl(code, {"X": 3, "Y": 5})["R"] == 1
    assert run_sipl(code, {"X": 0, "Y": 15})["R"] == 1


def test_power_program_from_course():
    code = """
    begin
        R := 1;
        while Y > 0 do
        begin
            R := R * X;
            Y := Y - 1
        end
    end
    """
    final_state = run_sipl(code, {"X": 5, "Y": 2})
    assert final_state["R"] == 25
    assert final_state["Y"] == 0
    assert final_state["X"] == 5


def test_parity_check_from_course():
    code = """
    begin
        T := N;
        while T > 1 do
            T := T - 2;
        if T = 0 then
            R := 1
        else
            R := 0
    end
    """
    assert run_sipl(code, {"N": 6})["R"] == 1
    assert run_sipl(code, {"N": 5})["R"] == 0


def test_fibonacci_from_course():
    code = """
    begin
        A := 0;
        B := 1;
        I := 0;
        while N > I do
        begin
            NEXT := A + B;
            A := B;
            B := NEXT;
            I := I + 1
        end;
        R := A
    end
    """
    assert run_sipl(code, {"N": 6})["R"] == 8


def test_undefined_variable_error():
    code = """
    begin
        R := X + 1
    end
    """
    with pytest.raises(UndefinedVariableError) as exc_info:
        run_sipl(code)

    assert exc_info.value.var_name == "X"
    assert exc_info.value.span is not None
    assert exc_info.value.span.line == 3


def test_infinite_loop_step_limit():
    code = """
    begin
        while 1 = 1 do
            skip
    end
    """
    with pytest.raises(StepLimitExceededError) as exc_info:
        run_sipl(code, max_steps=100)

    assert "100" in str(exc_info.value)
    assert exc_info.value.span is not None


def test_invalid_max_steps():
    with pytest.raises(ValueError):
        SIPLInterpreter(max_steps=0)


def test_syntax_error_diagnostics():
    with pytest.raises(SIPLSyntaxError) as exc_info:
        parse_sipl("begin X = 1 end")
    assert exc_info.value.line == 1