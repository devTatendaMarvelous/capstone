"""Load the small YAML settings file without an extra dependency."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "smartcrop_config.yaml"


def _parse_scalar(raw: str):
    text = raw.strip()
    if text == "" or text.lower() in {"null", "~"}:
        return None
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def load_config(path: Path | None = None) -> dict:
    """Read the project YAML. It uses mappings, lists, and plain scalars only."""
    lines = (path or CONFIG_PATH).read_text(encoding="utf-8").splitlines()
    return _load_with_lists(lines)


def _load_with_lists(lines: list[str]) -> dict:
    root: dict = {}
    stack: list[tuple[int, object]] = [(-1, root)]
    index = 0
    parsed = []
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        parsed.append((indent, line.strip()))
    while index < len(parsed):
        indent, content = parsed[index]
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if content.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"List item outside a list: {content}")
            parent.append(_parse_scalar(content[2:]))
            index += 1
            continue
        key, _, raw = content.partition(":")
        key = key.strip()
        raw = raw.strip()
        if not isinstance(parent, dict):
            raise ValueError(f"Unsupported nesting near {key}")
        if raw == "":
            upcoming = parsed[index + 1][1] if index + 1 < len(parsed) else ""
            child: dict | list = [] if upcoming.startswith("- ") else {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(raw)
        index += 1
    return root


def data_dir() -> Path:
    path = ROOT / "data"
    for name in ("raw", "interim", "processed", "external", "metadata", "logs", "reports"):
        (path / name).mkdir(parents=True, exist_ok=True)
    return path
