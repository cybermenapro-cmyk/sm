#!/usr/bin/env python3
"""SM Beta 0.1.0 - a small, sandboxed Storage Management language interpreter.

This is a reference interpreter written with Python's standard library.
It does not execute shell commands and does not request operating-system root.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import operator
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERSION = "0.1.0-beta"
UNITS = {
    "B": 1,
    "KB": 1_000,
    "MB": 1_000**2,
    "GB": 1_000**3,
    "TB": 1_000**4,
    "KiB": 1_024,
    "MiB": 1_024**2,
    "GiB": 1_024**3,
    "TiB": 1_024**4,
}


class SMError(Exception):
    """An error intended to be shown to an SM programmer."""


@dataclass(frozen=True)
class Size:
    bytes: int

    def __post_init__(self) -> None:
        if self.bytes < 0:
            raise SMError("storage sizes cannot be negative")

    def __add__(self, other: Any) -> "Size":
        if not isinstance(other, Size):
            raise SMError("SIZE can only be added to SIZE")
        return Size(self.bytes + other.bytes)

    def __sub__(self, other: Any) -> "Size":
        if not isinstance(other, Size):
            raise SMError("SIZE can only be subtracted from SIZE")
        return Size(self.bytes - other.bytes)

    def __str__(self) -> str:
        # Prefer readable decimal units; internal arithmetic always uses bytes.
        for unit in ("TB", "GB", "MB", "KB"):
            factor = UNITS[unit]
            if self.bytes >= factor:
                amount = self.bytes / factor
                rendered = f"{amount:.2f}".rstrip("0").rstrip(".")
                return f"{rendered} {unit}"
        return f"{self.bytes} B"


@dataclass
class FixedArray:
    items: list[Any]


@dataclass
class DataBlock:
    kind: str
    values: dict[str, Any]


def pretty(value: Any) -> str:
    if isinstance(value, Size):
        return str(value)
    if isinstance(value, FixedArray):
        return "[" + ", ".join(pretty(v) for v in value.items) + "]"
    if isinstance(value, list):
        return "[" + ", ".join(pretty(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {pretty(v)}" for k, v in value.items()) + "}"
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    if value is None:
        return "NULL"
    return str(value)


def encode_value(value: Any) -> Any:
    if isinstance(value, Size):
        return {"__sm_type__": "SIZE", "bytes": value.bytes}
    if isinstance(value, FixedArray):
        return {"__sm_type__": "ARRAY", "items": [encode_value(x) for x in value.items]}
    if isinstance(value, list):
        return [encode_value(x) for x in value]
    if isinstance(value, dict):
        return {str(k): encode_value(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise SMError(f"value of type {type(value).__name__} cannot be persisted")


def decode_value(value: Any) -> Any:
    if isinstance(value, dict) and value.get("__sm_type__") == "SIZE":
        return Size(int(value["bytes"]))
    if isinstance(value, dict) and value.get("__sm_type__") == "ARRAY":
        return FixedArray([decode_value(x) for x in value["items"]])
    if isinstance(value, list):
        return [decode_value(x) for x in value]
    if isinstance(value, dict):
        return {k: decode_value(v) for k, v in value.items()}
    return value


_SIZE_LITERAL = re.compile(r"(?<![\w\"])(\d+(?:\.\d+)?)\s+(B|KB|MB|GB|TB|KiB|MiB|GiB|TiB)\b")


def prepare_expression(source: str) -> str:
    def replace_size(match: re.Match[str]) -> str:
        number, unit = match.groups()
        return f'SIZE({number}, "{unit}")'
    return _SIZE_LITERAL.sub(replace_size, source.strip())


_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}
_CMPOPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}


class ExpressionEvaluator:
    def __init__(self, env: dict[str, Any]):
        self.env = env

    def parse(self, source: str) -> Any:
        try:
            node = ast.parse(prepare_expression(source), mode="eval").body
        except SyntaxError as exc:
            raise SMError(f"invalid expression: {source}") from exc
        return self.visit(node)

    def visit(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            names = {"TRUE": True, "FALSE": False, "NULL": None}
            if node.id in names:
                return names[node.id]
            if node.id in self.env:
                return self.env[node.id]
            raise SMError(f"unknown variable: {node.id}")
        if isinstance(node, ast.List):
            return [self.visit(x) for x in node.elts]
        if isinstance(node, ast.Tuple):
            return [self.visit(x) for x in node.elts]
        if isinstance(node, ast.Dict):
            return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd, ast.Not)):
            value = self.visit(node.operand)
            if isinstance(node.op, ast.USub):
                return -value
            if isinstance(node.op, ast.UAdd):
                return +value
            return not value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            try:
                return _BINOPS[type(node.op)](self.visit(node.left), self.visit(node.right))
            except (TypeError, ZeroDivisionError) as exc:
                raise SMError(f"invalid operation: {exc}") from exc
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _CMPOPS:
            try:
                return _CMPOPS[type(node.ops[0])](self.visit(node.left), self.visit(node.comparators[0]))
            except TypeError as exc:
                raise SMError("these values cannot be compared") from exc
        if isinstance(node, ast.Subscript):
            target = self.visit(node.value)
            index = self.visit(node.slice)
            try:
                if isinstance(target, FixedArray):
                    return target.items[index]
                return target[index]
            except (IndexError, KeyError, TypeError) as exc:
                raise SMError("invalid index or field access") from exc
        if isinstance(node, ast.Attribute):
            target = self.visit(node.value)
            if isinstance(target, dict) and node.attr in target:
                return target[node.attr]
            raise SMError(f"object has no field '{node.attr}'")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "SIZE":
            if len(node.args) != 2:
                raise SMError('SIZE expects a number and a unit, e.g. SIZE(512, "MB")')
            number = self.visit(node.args[0])
            unit = self.visit(node.args[1])
            if unit not in UNITS or not isinstance(number, (int, float)):
                raise SMError("invalid SIZE value or unit")
            byte_count = number * UNITS[unit]
            if int(byte_count) != byte_count:
                raise SMError("SIZE must resolve to a whole number of bytes")
            return Size(int(byte_count))
        raise SMError(f"unsupported expression feature: {type(node).__name__}")


class Interpreter:
    def __init__(self, workspace: Path, auto_yes: bool = False):
        self.workspace = workspace.expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.auto_yes = auto_yes
        self.env: dict[str, Any] = {}
        self.data_blocks: dict[str, DataBlock] = {}
        self.active_data: str | None = None
        self.plans: dict[str, list[tuple[int, str]]] = {}
        self.program_name = "Untitled"
        self.su_scope: str | None = None
        self.output: list[str] = []

    def say(self, message: str) -> None:
        print(message)
        self.output.append(message)

    def path(self, raw: str, allow_root: bool = False, internal: bool = False) -> Path:
        raw_path = Path(raw).expanduser()
        if raw_path.is_absolute():
            raise SMError("absolute paths are disabled in Beta; use a path inside the SM workspace")
        if not internal and raw_path.parts and raw_path.parts[0] in {".sm-trash", ".sm-data"}:
            raise SMError("SM internal directories are reserved")
        candidate = (self.workspace / raw_path).resolve()
        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise SMError("path escapes the SM workspace") from exc
        if not allow_root and candidate == self.workspace:
            raise SMError("operation on the workspace root itself is not allowed")
        return candidate

    def env_for_read(self) -> dict[str, Any]:
        merged = dict(self.env)
        if self.active_data:
            merged.update(self.data_blocks[self.active_data].values)
        return merged

    def assign(self, name: str, value: Any) -> None:
        if self.active_data:
            self.data_blocks[self.active_data].values[name] = value
        else:
            self.env[name] = value

    def expression(self, source: str) -> Any:
        return ExpressionEvaluator(self.env_for_read()).parse(source)

    @staticmethod
    def quoted(text: str) -> str:
        try:
            value = ast.literal_eval(text.strip())
        except (ValueError, SyntaxError) as exc:
            raise SMError("expected a quoted string") from exc
        if not isinstance(value, str):
            raise SMError("expected a string")
        return value

    def execute_file(self, script: Path) -> None:
        try:
            lines = script.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise SMError(f"cannot read program: {exc}") from exc
        self.run_lines(lines)

    def run_lines(self, lines: list[str]) -> None:
        i = 0
        while i < len(lines):
            original = lines[i]
            line_no = i + 1
            line = original.strip()
            i += 1
            if not line or line.startswith("#"):
                continue
            try:
                if line.upper().startswith("PROGRAM "):
                    self.program_name = self.quoted(line.split(None, 1)[1])
                    self.say(f"SM {VERSION} | PROGRAM {self.program_name}")
                elif line.upper() == "END":
                    self.say("PROGRAM END")
                    break
                elif line.upper().startswith("PLAN "):
                    name = self.quoted(line.split(None, 1)[1])
                    block: list[tuple[int, str]] = []
                    while i < len(lines) and lines[i].strip().upper() != "END_PLAN":
                        candidate = lines[i].strip()
                        if candidate and not candidate.startswith("#"):
                            block.append((i + 1, candidate))
                        i += 1
                    if i >= len(lines):
                        raise SMError("PLAN block is missing END_PLAN")
                    i += 1
                    self.plans[name] = block
                    self.say(f"PLAN '{name}' prepared ({len(block)} operation(s)); nothing changed.")
                    for n, (_, op) in enumerate(block, 1):
                        self.say(f"  {n}. {op}")
                elif line.upper().startswith("APPLY "):
                    name = self.quoted(line.split(None, 1)[1])
                    if name not in self.plans:
                        raise SMError(f"unknown plan: {name}")
                    self.say(f"Review plan '{name}' containing {len(self.plans[name])} operation(s).")
                    accepted = self.auto_yes or input("Apply this plan inside the SM workspace? [y/N] ").strip().lower() == "y"
                    if not accepted:
                        self.say("PLAN CANCELLED")
                    else:
                        for plan_line, operation_line in self.plans[name]:
                            self.execute_line(operation_line, plan_line)
                elif line.upper().startswith("DATA TEMP ") or line.upper().startswith("DATA PERSIST "):
                    parts = line.split(None, 2)
                    kind, name = parts[1].upper(), parts[2]
                    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                        raise SMError("invalid DATA block name")
                    if name in self.data_blocks:
                        raise SMError(f"DATA block already exists: {name}")
                    self.data_blocks[name] = DataBlock(kind, {})
                    self.active_data = name
                    self.say(f"DATA {kind} '{name}' opened")
                elif line.upper() == "END_DATA":
                    if not self.active_data:
                        raise SMError("END_DATA without an active DATA block")
                    closed_name = self.active_data
                    self.env[closed_name] = self.data_blocks[closed_name].values
                    self.say(f"DATA '{closed_name}' closed")
                    self.active_data = None
                elif line.upper().startswith("SU "):
                    self.handle_su(line)
                elif line.upper() == "END_SU":
                    self.su_scope = None
                    self.say("SU scope ended; no host privileges were changed.")
                else:
                    self.execute_line(line, line_no)
            except (SMError, OSError, ValueError, TypeError, IndexError) as exc:
                raise SMError(f"line {line_no}: {exc}") from exc
        if self.active_data:
            raise SMError(f"DATA block '{self.active_data}' is missing END_DATA")

    def handle_su(self, line: str) -> None:
        parts = line.split(None, 2)
        mode = parts[1].upper()
        if mode not in {"SESSION", "BLOCK", "OPERATION"}:
            raise SMError("SU syntax: SU SESSION, SU BLOCK, or SU OPERATION <command>")
        if mode == "OPERATION":
            if len(parts) < 3:
                raise SMError("SU OPERATION requires one operation")
            self.say(f"SU request recorded for one operation: {parts[2]}")
            self.say("Root elevation adapter is not included in Beta; no privilege escalation was attempted.")
        else:
            self.su_scope = mode
            self.say(f"SU {mode} request recorded")
            self.say("Root elevation adapter is not included in Beta; no privilege escalation was attempted.")

    def execute_line(self, line: str, line_no: int) -> None:
        upper = line.upper()
        match = re.match(r"^(VAR|LIST|OBJECT)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", line, re.I)
        if match:
            kind, name, expr = match.groups()
            value = self.expression(expr)
            if kind.upper() == "LIST" and not isinstance(value, list):
                raise SMError("LIST requires a list value")
            if kind.upper() == "OBJECT" and not isinstance(value, dict):
                raise SMError("OBJECT requires an object value")
            self.assign(name, value)
            self.say(f"{kind.upper()} {name} = {pretty(value)}")
            return
        match = re.match(r"^ARRAY\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*ARRAY\((\d+)\)$", line, re.I)
        if match:
            name, count = match.groups()
            count_int = int(count)
            if count_int > 1_000_000:
                raise SMError("ARRAY length exceeds Beta safety limit (1,000,000)")
            self.assign(name, FixedArray([None] * count_int))
            self.say(f"ARRAY {name} created with {count_int} slot(s)")
            return
        match = re.match(r"^SET\s+([A-Za-z_][A-Za-z0-9_]*)(?:\.([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\])?\s*=\s*(.+)$", line, re.I)
        if match:
            name, field, index, expr = match.groups()
            value = self.expression(expr)
            target = self.env_for_read().get(name)
            if field is not None:
                if not isinstance(target, dict):
                    raise SMError(f"'{name}' is not an OBJECT or DATA record")
                target[field] = value
            elif index is not None:
                if not isinstance(target, FixedArray):
                    raise SMError(f"'{name}' is not an ARRAY")
                idx = int(index)
                if idx < 0 or idx >= len(target.items):
                    raise SMError("ARRAY index out of range")
                target.items[idx] = value
            else:
                if target is None and name not in self.env and not (self.active_data and name in self.data_blocks[self.active_data].values):
                    raise SMError(f"cannot SET unknown variable '{name}'; declare it with VAR first")
                if self.active_data and name in self.data_blocks[self.active_data].values:
                    self.data_blocks[self.active_data].values[name] = value
                else:
                    self.env[name] = value
            suffix = '.' + field if field is not None else ('[' + index + ']' if index is not None else '')
            self.say(f"SET {name}{suffix} = {pretty(value)}")
            return
        if upper.startswith("SHOW "):
            self.say(pretty(self.expression(line[5:].strip())))
            return
        if upper.startswith("SAVE "):
            self.save_data(line.split(None, 1)[1].strip())
            return
        if upper.startswith("LOAD "):
            self.load_data(line.split(None, 1)[1].strip())
            return
        if upper.startswith("FILE "):
            self.file_command(line)
            return
        if upper.startswith("DIRECTORY "):
            self.directory_command(line)
            return
        if upper.startswith("COPY ") or upper.startswith("MOVE "):
            self.transfer_command(line)
            return
        if upper.startswith("VERIFY "):
            self.verify_command(line)
            return
        if upper.startswith("TRASH "):
            self.trash_command(line)
            return
        if upper.startswith("RESTORE "):
            self.restore_command(line)
            return
        if upper.startswith("QUOTA CHECK "):
            self.quota_command(line)
            return
        if upper.startswith("DEVICE LIST") or upper.startswith("DEVICE INFO") or upper.startswith("DEVICE STATUS"):
            self.device_command(line)
            return
        if upper in {"HELP", "SM HELP"}:
            self.say("SM Beta supports VAR, LIST, ARRAY, OBJECT, DATA, FILE, DIRECTORY, COPY, MOVE, VERIFY, TRASH, RESTORE, QUOTA, DEVICE, PLAN, APPLY and SU.")
            return
        raise SMError(f"unknown instruction: {line}")

    def file_command(self, line: str) -> None:
        match = re.match(r'^FILE\s+(WRITE|APPEND)\s+(".*?")\s+(.+)$', line, re.I)
        if match:
            action, raw_path, raw_value = match.groups()
            target = self.path(self.quoted(raw_path))
            value = self.expression(raw_value)
            if not isinstance(value, str):
                raise SMError("FILE WRITE/APPEND expects a STRING value")
            target.parent.mkdir(parents=True, exist_ok=True)
            mode = "w" if action.upper() == "WRITE" else "a"
            with target.open(mode, encoding="utf-8") as handle:
                handle.write(value)
            self.say(f"FILE {action.upper()}: {self.quoted(raw_path)} ({len(value.encode('utf-8'))} bytes)")
            return
        match = re.match(r'^FILE\s+(READ|INFO|EXISTS|SIZE|CREATE|DELETE)\s+(".*")$', line, re.I)
        if match:
            action, raw_path = match.groups()
            name = self.quoted(raw_path)
            target = self.path(name)
            action = action.upper()
            if action == "READ":
                if not target.is_file():
                    raise SMError("file does not exist")
                self.say(target.read_text(encoding="utf-8"))
            elif action == "INFO":
                if not target.exists():
                    raise SMError("path does not exist")
                self.say(f"PATH: {name}\nTYPE: {'DIRECTORY' if target.is_dir() else 'FILE'}\nSIZE: {target.stat().st_size} B")
            elif action == "EXISTS":
                self.say("TRUE" if target.exists() else "FALSE")
            elif action == "SIZE":
                if not target.is_file():
                    raise SMError("file does not exist")
                self.say(str(Size(target.stat().st_size)))
            elif action == "CREATE":
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch(exist_ok=False)
                self.say(f"FILE CREATED: {name}")
            elif action == "DELETE":
                self.trash_path(target, name)
            return
        raise SMError("invalid FILE syntax")

    def directory_command(self, line: str) -> None:
        match = re.match(r'^DIRECTORY\s+(CREATE|LIST|INFO)\s+(".*")$', line, re.I)
        if not match:
            raise SMError("DIRECTORY syntax: CREATE, LIST, or INFO followed by a quoted path")
        action, raw_path = match.groups()
        name = self.quoted(raw_path)
        target = self.path(name)
        action = action.upper()
        if action == "CREATE":
            target.mkdir(parents=True, exist_ok=False)
            self.say(f"DIRECTORY CREATED: {name}")
        elif action == "LIST":
            if not target.is_dir():
                raise SMError("directory does not exist")
            items = sorted(p.name + ("/" if p.is_dir() else "") for p in target.iterdir())
            self.say("\n".join(items) if items else "(empty)")
        else:
            if not target.is_dir():
                raise SMError("directory does not exist")
            count = sum(1 for p in target.rglob("*") if p.is_file())
            used = sum(p.stat().st_size for p in target.rglob("*") if p.is_file())
            self.say(f"DIRECTORY: {name}\nFILES: {count}\nSIZE: {Size(used)}")

    def transfer_command(self, line: str) -> None:
        match = re.match(r'^(COPY|MOVE)\s+(".*?")\s+TO\s+(".*")$', line, re.I)
        if not match:
            raise SMError("syntax: COPY/MOVE \"source\" TO \"destination\"")
        action, raw_source, raw_destination = match.groups()
        source_name, destination_name = self.quoted(raw_source), self.quoted(raw_destination)
        source, destination = self.path(source_name), self.path(destination_name)
        if not source.exists():
            raise SMError("source does not exist")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise SMError("destination already exists; Beta never overwrites during COPY/MOVE")
        if action.upper() == "COPY":
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
        else:
            shutil.move(str(source), str(destination))
        self.say(f"{action.upper()}: {source_name} -> {destination_name}")

    def verify_command(self, line: str) -> None:
        match = re.match(r'^VERIFY\s+(".*?")\s+AGAINST\s+(".*?")\s+WITH\s+SHA256$', line, re.I)
        if not match:
            raise SMError('syntax: VERIFY "source" AGAINST "destination" WITH SHA256')
        a_name, b_name = self.quoted(match.group(1)), self.quoted(match.group(2))
        a, b = self.path(a_name), self.path(b_name)
        if not a.is_file() or not b.is_file():
            raise SMError("VERIFY currently supports files only")
        def digest(path: Path) -> str:
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()
        same = digest(a) == digest(b)
        self.say(f"SHA256: {'MATCH' if same else 'MISMATCH'}")

    def trash_path(self, target: Path, display_name: str) -> None:
        if not target.exists():
            raise SMError("path does not exist")
        relative = target.relative_to(self.workspace)
        trash_root = self.workspace / ".sm-trash"
        destination = trash_root / relative
        if destination.exists():
            raise SMError("an item with this original path is already in Trash")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(destination))
        self.say(f"TRASHED: {display_name} (recoverable)")

    def trash_command(self, line: str) -> None:
        raw = line[len("TRASH "):].strip()
        name = self.quoted(raw)
        self.trash_path(self.path(name), name)

    def restore_command(self, line: str) -> None:
        name = self.quoted(line[len("RESTORE "):].strip())
        original = self.path(name)
        trashed = self.path(".sm-trash/" + name, internal=True)
        if not trashed.exists():
            raise SMError("no trashed item found for this path")
        if original.exists():
            raise SMError("cannot restore: original path already exists")
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(trashed), str(original))
        self.say(f"RESTORED: {name}")

    def quota_command(self, line: str) -> None:
        match = re.match(r'^QUOTA\s+CHECK\s+(".*?")\s+LIMIT\s+(.+)$', line, re.I)
        if not match:
            raise SMError('syntax: QUOTA CHECK "folder" LIMIT 100 MB')
        name, raw_limit = self.quoted(match.group(1)), match.group(2)
        limit = self.expression(raw_limit)
        if not isinstance(limit, Size):
            raise SMError("QUOTA LIMIT must be a SIZE, e.g. 100 MB")
        target = self.path(name)
        if not target.is_dir():
            raise SMError("quota target must be an existing directory")
        used = sum(p.stat().st_size for p in target.rglob("*") if p.is_file())
        self.say(f"QUOTA {name}: USED {Size(used)} / LIMIT {limit} | {'WITHIN LIMIT' if used <= limit.bytes else 'OVER LIMIT'}")

    def device_command(self, line: str) -> None:
        upper = line.upper()
        if upper == "DEVICE LIST":
            total, used, free = self.device_usage(self.workspace)
            self.say(f"DEVICE: workspace-volume\nTOTAL: {Size(total)}\nUSED: {Size(used)}\nFREE: {Size(free)}\nACCESS: READ-ONLY")
            return
        match = re.match(r'^DEVICE\s+(INFO|STATUS)\s+(".*"|[.])$', line, re.I)
        if not match:
            raise SMError('DEVICE syntax: LIST, INFO "path", or STATUS "path"')
        action, raw_path = match.groups()
        name = self.quoted(raw_path) if raw_path.startswith('"') else raw_path
        target = self.path(name, allow_root=True)
        if not target.exists():
            raise SMError("device inspection path does not exist")
        total, used, free = self.device_usage(target)
        self.say(f"DEVICE {action.upper()}: {name}\nTOTAL: {Size(total)}\nUSED: {Size(used)}\nFREE: {Size(free)}\nACCESS: READ-ONLY")

    @staticmethod
    def device_usage(path: Path) -> tuple[int, int, int]:
        usage = shutil.disk_usage(path)
        return usage.total, usage.used, usage.free

    def save_data(self, name: str) -> None:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise SMError("invalid DATA block name")
        if name not in self.data_blocks:
            raise SMError(f"unknown DATA block: {name}")
        block = self.data_blocks[name]
        if block.kind != "PERSIST":
            raise SMError("SAVE is only allowed for DATA PERSIST blocks")
        store = self.workspace / ".sm-data"
        store.mkdir(parents=True, exist_ok=True)
        destination = store / f"{name}.json"
        payload = {"format": "SM-DATA-1", "name": name, "values": encode_value(block.values)}
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(destination)
        self.say(f"DATA SAVED: {name}")

    def load_data(self, name: str) -> None:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise SMError("invalid DATA block name")
        source = self.workspace / ".sm-data" / f"{name}.json"
        if not source.is_file():
            raise SMError(f"persistent DATA not found: {name}")
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SMError("cannot read persistent DATA") from exc
        if payload.get("format") != "SM-DATA-1":
            raise SMError("unsupported persistent DATA format")
        values = decode_value(payload.get("values", {}))
        self.data_blocks[name] = DataBlock("PERSIST", values)
        self.env[name] = values
        self.say(f"DATA LOADED: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SM Beta - Storage Management language interpreter")
    parser.add_argument("program", nargs="?", help="path to an .sm program")
    parser.add_argument("--version", action="version", version=f"SM {VERSION}")
    parser.add_argument("--workspace", default=".sm-workspace", help="workspace directory (default: .sm-workspace)")
    parser.add_argument("--yes", action="store_true", help="approve APPLY plans without an interactive prompt")
    parser.add_argument("--check", action="store_true", help="check basic program structure without running it")
    args = parser.parse_args(argv)
    if not args.program:
        parser.print_help()
        return 0
    script = Path(args.program).expanduser().resolve()
    if script.suffix.lower() != ".sm":
        print("SM error: source files must use the .sm extension", file=sys.stderr)
        return 2
    if not script.is_file():
        print(f"SM error: file not found: {script}", file=sys.stderr)
        return 2
    try:
        if args.check:
            lines = script.read_text(encoding="utf-8").splitlines()
            joined = "\n".join(lines)
            if joined.count("PLAN ") != joined.count("END_PLAN"):
                raise SMError("PLAN / END_PLAN block count mismatch")
            if joined.count("DATA TEMP ") + joined.count("DATA PERSIST ") != joined.count("END_DATA"):
                raise SMError("DATA / END_DATA block count mismatch")
            print(f"SM CHECK OK: {script.name} ({len(lines)} line(s))")
            return 0
        runtime = Interpreter(Path(args.workspace), auto_yes=args.yes)
        runtime.execute_file(script)
        return 0
    except (SMError, OSError) as exc:
        print(f"SM ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
