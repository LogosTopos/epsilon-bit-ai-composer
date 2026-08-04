"""Out-of-process JSON adapter for heavy or quarantined backends.

Use this when a backend should stay outside the core package: DAW renderers,
effect chains, GPL tools, web-app bridges, or local experiments. The contract is
plain JSON over stdin/stdout, so an Agent can inspect and replace the backend
without changing the composition source of truth.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .base import AdapterResult, JsonDict


@dataclass(frozen=True)
class ExternalToolSpec:
    """Command specification for a JSON-speaking external tool."""

    name: str
    command: tuple[str, ...] | list[str]
    cwd: str | Path | None = None
    timeout: float = 120.0
    env: JsonDict = field(default_factory=dict)
    parse_stdout_json: bool = True


def run_json_tool(spec: ExternalToolSpec, payload: JsonDict) -> AdapterResult:
    """Run an external command with JSON payload on stdin.

    The child process should read one JSON document from stdin. If
    ``parse_stdout_json`` is true, stdout is parsed as JSON; otherwise raw stdout
    is returned under ``{"stdout": ...}``.
    """

    if not spec.command:
        return AdapterResult.failure(["external command is empty"], backend=spec.name)

    env = os.environ.copy()
    env.update({str(key): str(value) for key, value in spec.env.items()})
    try:
        completed = subprocess.run(
            [str(part) for part in spec.command],
            input=json.dumps(payload, ensure_ascii=False),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            cwd=str(spec.cwd) if spec.cwd is not None else None,
            env=env,
            timeout=spec.timeout,
        )
    except FileNotFoundError as exc:
        return AdapterResult.failure([str(exc)], backend=spec.name)
    except subprocess.TimeoutExpired as exc:
        return AdapterResult.failure(
            [f"external tool timed out after {spec.timeout}s"],
            backend=spec.name,
            data={
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
            },
        )

    data: Any
    warnings: list[str] = []
    if spec.parse_stdout_json:
        stdout = completed.stdout.strip()
        if stdout:
            try:
                data = json.loads(stdout)
            except json.JSONDecodeError as exc:
                return AdapterResult.failure(
                    [f"stdout was not valid JSON: {exc}"],
                    backend=spec.name,
                    data={
                        "returncode": completed.returncode,
                        "stdout": completed.stdout,
                        "stderr": completed.stderr,
                    },
                )
        else:
            data = None
    else:
        data = {"stdout": completed.stdout}

    if completed.stderr.strip():
        warnings.append(completed.stderr.strip())

    if completed.returncode != 0:
        return AdapterResult.failure(
            [f"external tool exited with {completed.returncode}"],
            backend=spec.name,
            data={
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "parsed": data,
            },
            warnings=warnings,
        )

    return AdapterResult.success(
        data=data,
        backend=spec.name,
        warnings=warnings,
    )


def run_external_tool(
    command: tuple[str, ...] | list[str],
    payload: JsonDict,
    *,
    name: str = "external",
    cwd: str | Path | None = None,
    timeout: float = 120.0,
    env: JsonDict | None = None,
    parse_stdout_json: bool = True,
) -> AdapterResult:
    """Convenience wrapper around :func:`run_json_tool`."""

    return run_json_tool(
        ExternalToolSpec(
            name=name,
            command=command,
            cwd=cwd,
            timeout=timeout,
            env=env or {},
            parse_stdout_json=parse_stdout_json,
        ),
        payload,
    )
