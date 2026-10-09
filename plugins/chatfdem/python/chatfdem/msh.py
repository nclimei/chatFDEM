from __future__ import annotations

import json
import shlex
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ELEMENT_NODE_COUNTS = {
    1: 2,
    2: 3,
    3: 4,
    4: 4,
    5: 8,
    6: 6,
    7: 5,
    8: 3,
    9: 6,
    10: 9,
    11: 10,
    15: 1,
    16: 8,
    17: 20,
    18: 15,
    19: 13,
    21: 10,
    23: 15,
    26: 4,
    29: 20,
    30: 35,
    31: 56,
}

ELEMENT_TYPE_NAMES = {
    1: "line2",
    2: "triangle3",
    3: "quad4",
    4: "tetra4",
    5: "hex8",
    6: "prism6",
    7: "pyramid5",
    8: "line3",
    9: "triangle6",
    10: "quad9",
    11: "tetra10",
    15: "point1",
    16: "quad8",
    17: "hex20",
    18: "prism15",
    19: "pyramid13",
    21: "triangle10",
    23: "triangle15",
    26: "line4",
    29: "tetra20",
    30: "tetra35",
    31: "tetra56",
}

SURFACE_ELEMENT_TYPES = {2, 3, 9, 10, 16, 21, 23}
LINE_ELEMENT_TYPES = {1, 8, 26}


@dataclass(frozen=True)
class PhysicalName:
    dim: int
    tag: int
    name: str


@dataclass(frozen=True)
class Element:
    tag: int
    entity_dim: int
    entity_tag: int
    element_type: int
    node_tags: tuple[int, ...]
    physical_tags: tuple[int, ...]


@dataclass(frozen=True)
class MshMesh:
    path: Path
    version: str
    physical_names: tuple[PhysicalName, ...]
    entity_physical_tags: dict[tuple[int, int], tuple[int, ...]]
    nodes: dict[int, tuple[float, float, float]]
    elements: tuple[Element, ...]

    def summary(self) -> dict[str, object]:
        element_type_counts = Counter(element.element_type for element in self.elements)
        element_dim_counts = Counter(element.entity_dim for element in self.elements)
        physical_counts: dict[tuple[int, int], int] = Counter()
        for element in self.elements:
            for physical_tag in element.physical_tags:
                physical_counts[(element.entity_dim, physical_tag)] += 1

        physical_name_by_key = {
            (physical.dim, physical.tag): physical.name for physical in self.physical_names
        }
        bbox = self.bounding_box()
        physical_groups = []
        for key in sorted(set(physical_name_by_key) | set(physical_counts)):
            dim, tag = key
            physical_groups.append(
                {
                    "dim": dim,
                    "tag": tag,
                    "name": physical_name_by_key.get(key, ""),
                    "elements": physical_counts.get(key, 0),
                }
            )
        boundary_node_sets = self.boundary_node_sets()

        return {
            "path": str(self.path),
            "format": "msh",
            "msh_version": self.version,
            "nodes": len(self.nodes),
            "elements": len(self.elements),
            "bounding_box": bbox,
            "elements_by_dimension": {str(key): value for key, value in sorted(element_dim_counts.items())},
            "elements_by_type": {
                ELEMENT_TYPE_NAMES.get(key, str(key)): value for key, value in sorted(element_type_counts.items())
            },
            "physical_groups": physical_groups,
            "boundary_node_sets": {
                name: len(nodes) for name, nodes in sorted(boundary_node_sets.items())
            },
            "warnings": self.validation_warnings(),
        }

    def validation_warnings(self) -> list[str]:
        warnings: list[str] = []
        if not self.nodes:
            warnings.append("mesh contains no nodes")
        if not self.elements:
            warnings.append("mesh contains no elements")
        if not self.physical_names:
            warnings.append("mesh has no named physical groups")
        unnamed_entities = [
            (element.entity_dim, element.entity_tag)
            for element in self.elements
            if not element.physical_tags
        ]
        if unnamed_entities:
            warnings.append("some elements are not assigned to physical groups")
        return warnings

    def bounding_box(self) -> dict[str, list[float]] | None:
        if not self.nodes:
            return None
        xs = [point[0] for point in self.nodes.values()]
        ys = [point[1] for point in self.nodes.values()]
        zs = [point[2] for point in self.nodes.values()]
        return {
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
        }

    def to_json(self) -> str:
        return json.dumps(self.summary(), indent=2, sort_keys=True)

    def physical_name_by_key(self) -> dict[tuple[int, int], str]:
        return {(physical.dim, physical.tag): physical.name for physical in self.physical_names}

    def max_element_dimension(self) -> int:
        return max((element.entity_dim for element in self.elements), default=0)

    def physical_node_sets(
        self,
        *,
        dimensions: Iterable[int] | None = None,
    ) -> dict[str, tuple[int, ...]]:
        allowed_dimensions = set(dimensions) if dimensions is not None else None
        physical_names = self.physical_name_by_key()
        name_counts = Counter(physical_names.values())
        nodes_by_name: dict[str, set[int]] = {}
        for element in self.elements:
            if allowed_dimensions is not None and element.entity_dim not in allowed_dimensions:
                continue
            for physical_tag in element.physical_tags:
                key = (element.entity_dim, physical_tag)
                raw_name = physical_names.get(key)
                if not raw_name:
                    continue
                name = raw_name if name_counts[raw_name] == 1 else f"{raw_name}_dim{element.entity_dim}"
                nodes_by_name.setdefault(name, set()).update(element.node_tags)
        return {name: tuple(sorted(nodes)) for name, nodes in sorted(nodes_by_name.items())}

    def boundary_node_sets(self) -> dict[str, tuple[int, ...]]:
        max_dimension = self.max_element_dimension()
        if max_dimension <= 0:
            return {}
        return self.physical_node_sets(dimensions=range(0, max_dimension))


def read_msh(path: str | Path) -> MshMesh:
    msh_path = Path(path).expanduser().resolve()
    text = msh_path.read_text(encoding="utf-8", errors="replace")
    sections = _read_sections(text.splitlines())
    version = _read_mesh_version(sections.get("MeshFormat", []))
    if not version.startswith("4."):
        raise ValueError(f"Only Gmsh MSH 4.x ASCII files are supported, got version {version}")

    physical_names = _read_physical_names(sections.get("PhysicalNames", []))
    entity_physical_tags = _read_entities(sections.get("Entities", []))
    nodes = _read_nodes(sections.get("Nodes", []))
    elements = _read_elements(sections.get("Elements", []), entity_physical_tags)
    return MshMesh(
        path=msh_path,
        version=version,
        physical_names=tuple(physical_names),
        entity_physical_tags=entity_physical_tags,
        nodes=nodes,
        elements=tuple(elements),
    )


def _read_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line.startswith("$") or line.startswith("$End"):
            index += 1
            continue
        name = line[1:]
        end_marker = f"$End{name}"
        index += 1
        body: list[str] = []
        while index < len(lines) and lines[index].strip() != end_marker:
            body.append(lines[index])
            index += 1
        sections[name] = body
        index += 1
    return sections


def _read_mesh_version(lines: list[str]) -> str:
    if not lines:
        raise ValueError("MSH file is missing $MeshFormat")
    fields = lines[0].split()
    if len(fields) < 3:
        raise ValueError("Invalid $MeshFormat section")
    if fields[1] != "0":
        raise ValueError("Binary MSH files are not supported by the MVP parser")
    return fields[0]


def _read_physical_names(lines: list[str]) -> list[PhysicalName]:
    if not lines:
        return []
    count = int(lines[0].strip())
    names: list[PhysicalName] = []
    for line in lines[1 : count + 1]:
        fields = shlex.split(line)
        if len(fields) < 3:
            raise ValueError(f"Invalid PhysicalNames line: {line}")
        names.append(PhysicalName(dim=int(fields[0]), tag=int(fields[1]), name=fields[2]))
    return names


def _tokens(lines: list[str]) -> list[str]:
    return " ".join(line.strip() for line in lines if line.strip()).split()


def _read_entities(lines: list[str]) -> dict[tuple[int, int], tuple[int, ...]]:
    if not lines:
        return {}
    tokens = _tokens(lines)
    cursor = 0

    def take() -> str:
        nonlocal cursor
        if cursor >= len(tokens):
            raise ValueError("Unexpected end of $Entities section")
        value = tokens[cursor]
        cursor += 1
        return value

    counts = [int(take()) for _ in range(4)]
    entity_physical_tags: dict[tuple[int, int], tuple[int, ...]] = {}

    for dim, count in enumerate(counts):
        for _ in range(count):
            tag = int(take())
            if dim == 0:
                for _axis in range(3):
                    float(take())
            else:
                for _axis in range(6):
                    float(take())
            physical_count = int(take())
            physical_tags = tuple(int(take()) for _tag in range(physical_count))
            entity_physical_tags[(dim, tag)] = physical_tags
            bounding_count = int(take()) if dim > 0 else 0
            for _bound in range(bounding_count):
                int(take())

    return entity_physical_tags


def _read_nodes(lines: list[str]) -> dict[int, tuple[float, float, float]]:
    if not lines:
        return {}
    tokens = _tokens(lines)
    cursor = 0

    def take() -> str:
        nonlocal cursor
        if cursor >= len(tokens):
            raise ValueError("Unexpected end of $Nodes section")
        value = tokens[cursor]
        cursor += 1
        return value

    entity_blocks = int(take())
    int(take())  # numNodes
    int(take())  # minNodeTag
    int(take())  # maxNodeTag
    nodes: dict[int, tuple[float, float, float]] = {}

    for _block in range(entity_blocks):
        entity_dim = int(take())
        int(take())  # entityTag
        parametric = int(take())
        block_count = int(take())
        tags = [int(take()) for _node in range(block_count)]
        for tag in tags:
            x = float(take())
            y = float(take())
            z = float(take())
            if parametric:
                for _param in range(entity_dim):
                    float(take())
            nodes[tag] = (x, y, z)

    return nodes


def _read_elements(
    lines: list[str],
    entity_physical_tags: dict[tuple[int, int], tuple[int, ...]],
) -> list[Element]:
    if not lines:
        return []
    tokens = _tokens(lines)
    cursor = 0

    def take() -> str:
        nonlocal cursor
        if cursor >= len(tokens):
            raise ValueError("Unexpected end of $Elements section")
        value = tokens[cursor]
        cursor += 1
        return value

    entity_blocks = int(take())
    int(take())  # numElements
    int(take())  # minElementTag
    int(take())  # maxElementTag
    elements: list[Element] = []

    for _block in range(entity_blocks):
        entity_dim = int(take())
        entity_tag = int(take())
        element_type = int(take())
        block_count = int(take())
        node_count = ELEMENT_NODE_COUNTS.get(element_type)
        if node_count is None:
            raise ValueError(f"Unsupported Gmsh element type in MVP parser: {element_type}")
        physical_tags = entity_physical_tags.get((entity_dim, entity_tag), ())
        for _element in range(block_count):
            tag = int(take())
            node_tags = tuple(int(take()) for _node in range(node_count))
            elements.append(
                Element(
                    tag=tag,
                    entity_dim=entity_dim,
                    entity_tag=entity_tag,
                    element_type=element_type,
                    node_tags=node_tags,
                    physical_tags=physical_tags,
                )
            )

    return elements
