from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


HEADER_RE = re.compile(r"^\s*\*(?P<name>[^,\s]+)(?P<rest>.*)$")
GENERATED_NSET_BEGIN = "** chatFDEM boundary node sets: begin"
GENERATED_NSET_END = "** chatFDEM boundary node sets: end"


@dataclass(frozen=True)
class InpSummary:
    path: Path
    nodes: int
    elements: int
    elements_by_type: dict[str, int]
    element_sets: dict[str, int]
    node_sets: dict[str, int]

    def summary(self) -> dict[str, object]:
        warnings: list[str] = []
        if self.nodes == 0:
            warnings.append("inp contains no nodes")
        if self.elements == 0:
            warnings.append("inp contains no elements")
        if not self.element_sets:
            warnings.append("inp contains no element sets")
        return {
            "path": str(self.path),
            "format": "inp",
            "nodes": self.nodes,
            "elements": self.elements,
            "elements_by_type": self.elements_by_type,
            "element_sets": self.element_sets,
            "node_sets": self.node_sets,
            "warnings": warnings,
        }

    def to_json(self) -> str:
        return json.dumps(self.summary(), indent=2, sort_keys=True)


def read_inp(path: str | Path) -> InpSummary:
    inp_path = Path(path).expanduser().resolve()
    node_count = 0
    element_count = 0
    elements_by_type: Counter[str] = Counter()
    element_sets: Counter[str] = Counter()
    node_sets: Counter[str] = Counter()

    active_section = ""
    active_element_type = ""
    active_element_set = ""
    active_set_name = ""

    for raw_line in inp_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("**"):
            continue
        header_match = HEADER_RE.match(line)
        if header_match:
            active_section = header_match.group("name").upper()
            options = _parse_header_options(header_match.group("rest"))
            active_element_type = options.get("TYPE", "")
            active_element_set = options.get("ELSET", "")
            active_set_name = options.get("ELSET", "") or options.get("NSET", "")
            continue

        if active_section == "NODE":
            node_count += 1
        elif active_section == "ELEMENT":
            element_count += 1
            elements_by_type[active_element_type or "unknown"] += 1
            if active_element_set:
                element_sets[active_element_set] += 1
        elif active_section == "ELSET" and active_set_name:
            element_sets[active_set_name] += _count_csv_items(line)
        elif active_section == "NSET" and active_set_name:
            node_sets[active_set_name] += _count_csv_items(line)

    return InpSummary(
        path=inp_path,
        nodes=node_count,
        elements=element_count,
        elements_by_type=dict(sorted(elements_by_type.items())),
        element_sets=dict(sorted(element_sets.items())),
        node_sets=dict(sorted(node_sets.items())),
    )


def append_node_sets(
    inp_path: str | Path,
    node_sets: Mapping[str, tuple[int, ...] | list[int] | set[int]],
    *,
    output_path: str | Path | None = None,
) -> dict[str, int]:
    source_path = Path(inp_path).expanduser().resolve()
    target_path = Path(output_path).expanduser().resolve() if output_path is not None else source_path
    text = source_path.read_text(encoding="utf-8", errors="replace")
    text = _strip_generated_nset_block(text).rstrip()
    sanitized_sets = _sanitize_node_sets(node_sets)
    if sanitized_sets:
        text = text + "\n" + _format_node_set_block(sanitized_sets)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return {name: len(nodes) for name, nodes in sanitized_sets.items()}


def _parse_header_options(rest: str) -> dict[str, str]:
    options: dict[str, str] = {}
    for part in rest.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        options[key.strip().upper()] = value.strip()
    return options


def _count_csv_items(line: str) -> int:
    return len([item for item in line.split(",") if item.strip()])


def _strip_generated_nset_block(text: str) -> str:
    lines = text.splitlines()
    result: list[str] = []
    skipping = False
    for line in lines:
        if line.strip() == GENERATED_NSET_BEGIN:
            skipping = True
            continue
        if line.strip() == GENERATED_NSET_END:
            skipping = False
            continue
        if not skipping:
            result.append(line)
    return "\n".join(result)


def _sanitize_node_sets(
    node_sets: Mapping[str, tuple[int, ...] | list[int] | set[int]],
) -> dict[str, tuple[int, ...]]:
    used: set[str] = set()
    sanitized: dict[str, tuple[int, ...]] = {}
    for raw_name, raw_nodes in sorted(node_sets.items()):
        nodes = tuple(sorted({int(node) for node in raw_nodes if int(node) > 0}))
        if not nodes:
            continue
        base_name = _sanitize_set_name(raw_name)
        name = base_name
        suffix = 2
        while name.upper() in used:
            name = f"{base_name}_{suffix}"
            suffix += 1
        used.add(name.upper())
        sanitized[name] = nodes
    return sanitized


def _sanitize_set_name(name: object) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", str(name or "nset").strip())
    value = value.strip("_") or "nset"
    if not re.match(r"^[A-Za-z_]", value):
        value = f"n_{value}"
    return value[:80]


def _format_node_set_block(node_sets: Mapping[str, tuple[int, ...]]) -> str:
    lines = [GENERATED_NSET_BEGIN]
    for name, nodes in node_sets.items():
        lines.append(f"*NSET, NSET={name}")
        for index in range(0, len(nodes), 16):
            lines.append(", ".join(str(node) for node in nodes[index : index + 16]))
    lines.append(GENERATED_NSET_END)
    return "\n".join(lines)
