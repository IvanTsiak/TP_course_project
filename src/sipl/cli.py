import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sipl.interpreter import SIPLInterpreter, SIPLRuntimeError
from sipl.parser import SIPLSyntaxError, parse_sipl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sipl", description="SIPL execution & trace CLI")
    parser.add_argument("file", type=Path, help="Path to .sipl source file")
    parser.add_argument(
        "--state",
        type=str,
        default="{}",
        help='Initial state as JSON object, e.g. \'{"X": 5, "Y": 2}\'',
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10_000,
        help="Maximum execution steps before halting",
    )
    parser.add_argument(
        "--trace-only",
        action="store_true",
        help="Output only the JSON array of trace events",
    )
    args = parser.parse_args(argv)

    if not args.file.exists():
        print(f"Error: file '{args.file}' not found", file=sys.stderr)
        return 2

    try:
        initial_state = json.loads(args.state)
        if not isinstance(initial_state, dict) or not all(
            isinstance(k, str) and isinstance(v, int) for k, v in initial_state.items()
        ):
            raise ValueError("State must be a JSON object mapping variable names to integers")
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Invalid --state argument: {exc}", file=sys.stderr)
        return 2

    code = args.file.read_text(encoding="utf-8")
    interpreter = SIPLInterpreter(max_steps=args.max_steps)

    try:
        program = parse_sipl(code)
        final_state = interpreter.execute(program, initial_state)
    except (SIPLSyntaxError, SIPLRuntimeError) as exc:
        error_payload: dict[str, Any] = {
            "status": "error",
            "error": str(exc),
            "trace": [e.to_dict() for e in interpreter.trace],
        }
        print(json.dumps(error_payload, indent=2, ensure_ascii=False))
        return 1

    if args.trace_only:
        print(interpreter.trace_to_json(indent=2))
    else:
        payload: dict[str, Any] = {
            "status": "ok",
            "final_state": final_state,
            "steps": interpreter.steps,
            "trace": [e.to_dict() for e in interpreter.trace],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0