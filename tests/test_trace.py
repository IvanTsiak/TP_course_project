import json
from pathlib import Path

import pytest

from sipl import (
    SIPLInterpreter,
    StepLimitExceededError,
    TraceEvent,
    trace_sipl,
    trace_sipl_json,
)
from sipl.cli import main as cli_main


def test_trace_contains_all_event_types():
    code = """
    begin
        X := 2;
        if X > 1 then
            X := X + 3
        else
            skip
    end
    """
    events = trace_sipl(code)
    assert all(isinstance(e, TraceEvent) for e in events)

    event_types = [e.event_type for e in events]
    assert "BeforeStatement" in event_types
    assert "AfterStatement" in event_types
    assert "VariableChange" in event_types
    assert "ConditionCheck" in event_types
    assert event_types[-1] == "Completed"


def test_trace_variable_change_details():
    code = """
    begin
        R := 1;
        R := R * 5
    end
    """
    events = trace_sipl(code)
    var_events = [e for e in events if e.event_type == "VariableChange"]

    assert len(var_events) == 2
    assert var_events[0].data == {"var_name": "R", "old_value": None, "new_value": 1}
    assert var_events[0].state == {"R": 1}

    assert var_events[1].data == {"var_name": "R", "old_value": 1, "new_value": 5}
    assert var_events[1].state == {"R": 5}


def test_trace_while_condition_checks():
    code = """
    begin
        while Y > 0 do
            Y := Y - 1
    end
    """
    events = trace_sipl(code, {"Y": 2})
    cond_events = [e for e in events if e.event_type == "ConditionCheck"]

    # Y=2 (True), Y=1 (True), Y=0 (False)
    assert [e.data["result"] for e in cond_events] == [True, True, False]


def test_trace_records_error_event_on_step_limit():
    code = "begin while 1 = 1 do skip end"
    interpreter = SIPLInterpreter(max_steps=5)
    from sipl import parse_sipl

    program = parse_sipl(code)
    with pytest.raises(StepLimitExceededError):
        interpreter.execute(program)

    assert interpreter.trace[-1].event_type == "Error"
    assert interpreter.trace[-1].data["error_type"] == "StepLimitExceededError"


def test_trace_json_serialization():
    code = "begin A := 10 end"
    raw_json = trace_sipl_json(code)
    parsed = json.loads(raw_json)

    assert isinstance(parsed, list)
    assert parsed[-1]["event_type"] == "Completed"
    assert parsed[-1]["state"] == {"A": 10}
    assert "span" in parsed[0]


def test_cli_json_trace_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    sipl_file = tmp_path / "power.sipl"
    sipl_file.write_text(
        """
        begin
            R := 1;
            while Y > 0 do
            begin
                R := R * X;
                Y := Y - 1
            end
        end
        """,
        encoding="utf-8",
    )

    exit_code = cli_main([str(sipl_file), "--state", '{"X": 5, "Y": 2}'])
    assert exit_code == 0

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["status"] == "ok"
    assert output["final_state"] == {"X": 5, "Y": 0, "R": 25}
    assert len(output["trace"]) > 0