from __future__ import annotations

import html
from pathlib import Path

from .msh import LINE_ELEMENT_TYPES, SURFACE_ELEMENT_TYPES, Element, MshMesh, read_msh


PALETTE = [
    "#4c78a8",
    "#f58518",
    "#54a24b",
    "#e45756",
    "#72b7b2",
    "#b279a2",
    "#ff9da6",
    "#9d755d",
    "#bab0ac",
]


def write_html_preview(msh_path: str | Path, output_path: str | Path | None = None) -> Path:
    mesh = read_msh(msh_path)
    output = Path(output_path).expanduser().resolve() if output_path is not None else mesh.path.with_suffix(".html")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_preview_html(mesh), encoding="utf-8")
    return output


def _preview_html(mesh: MshMesh) -> str:
    bbox = mesh.bounding_box()
    if bbox is None:
        body = "<p>No nodes were found in this mesh.</p>"
    else:
        body = _svg(mesh, bbox)
    title = f"chatFDEM preview: {mesh.path.name}"
    summary = mesh.summary()
    legend = _legend(mesh)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f7f8fa;
      color: #20242a;
    }}
    main {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 300px;
      gap: 16px;
      padding: 16px;
      min-height: 100vh;
      box-sizing: border-box;
    }}
    .viewport {{
      background: #ffffff;
      border: 1px solid #d9dee7;
      min-height: calc(100vh - 32px);
      overflow: auto;
    }}
    aside {{
      background: #ffffff;
      border: 1px solid #d9dee7;
      padding: 14px;
      overflow-wrap: anywhere;
    }}
    h1 {{
      font-size: 16px;
      margin: 0 0 12px;
    }}
    h2 {{
      font-size: 13px;
      margin: 16px 0 8px;
    }}
    .legend-row {{
      display: grid;
      grid-template-columns: 18px minmax(0, 1fr);
      gap: 8px;
      align-items: center;
      margin: 6px 0;
      font-size: 13px;
    }}
    .swatch {{
      width: 16px;
      height: 16px;
      border: 1px solid rgba(0,0,0,0.2);
    }}
    pre {{
      white-space: pre-wrap;
      font-size: 12px;
      line-height: 1.4;
      background: #f2f4f8;
      padding: 10px;
      overflow: auto;
    }}
  </style>
</head>
<body>
  <main>
    <section class="viewport">{body}</section>
    <aside>
      <h1>{html.escape(title)}</h1>
      {legend}
      <h2>Summary</h2>
      <pre>{html.escape(_compact_summary(summary))}</pre>
    </aside>
  </main>
</body>
</html>
"""


def _svg(mesh: MshMesh, bbox: dict[str, list[float]]) -> str:
    min_x, min_y, _ = bbox["min"]
    max_x, max_y, _ = bbox["max"]
    width = max(max_x - min_x, 1e-9)
    height = max(max_y - min_y, 1e-9)
    pad = 0.05 * max(width, height)
    view_box = f"{min_x - pad} {-max_y - pad} {width + 2 * pad} {height + 2 * pad}"
    polygons = []
    lines = []
    color_by_key = _color_by_physical_key(mesh)
    for element in mesh.elements:
        key = _element_physical_key(element)
        color = color_by_key.get(key, "#8f98a8")
        if element.element_type in SURFACE_ELEMENT_TYPES:
            points = _polygon_points(mesh, element)
            if points:
                polygons.append(
                    f'<polygon points="{points}" fill="{color}" fill-opacity="0.34" '
                    f'stroke="#2d3440" stroke-width="{0.0025 * max(width, height):.6g}" />'
                )
        elif element.element_type in LINE_ELEMENT_TYPES:
            points = _polygon_points(mesh, element)
            if points:
                lines.append(
                    f'<polyline points="{points}" fill="none" stroke="{color}" '
                    f'stroke-width="{0.0075 * max(width, height):.6g}" />'
                )
    return (
        f'<svg width="100%" height="100%" viewBox="{view_box}" '
        'xmlns="http://www.w3.org/2000/svg" role="img">'
        '<rect x="-1000000" y="-1000000" width="2000000" height="2000000" fill="#ffffff" />'
        + "\n".join(polygons)
        + "\n".join(lines)
        + "</svg>"
    )


def _polygon_points(mesh: MshMesh, element: Element) -> str:
    if element.element_type in {9, 10, 16, 21, 23}:
        node_tags = element.node_tags[:3] if element.element_type in {9, 21, 23} else element.node_tags[:4]
    else:
        node_tags = element.node_tags
    points = []
    for node_tag in node_tags:
        point = mesh.nodes.get(node_tag)
        if point is None:
            continue
        x, y, _ = point
        points.append(f"{x},{-y}")
    return " ".join(points)


def _physical_name_by_key(mesh: MshMesh) -> dict[tuple[int, int], str]:
    return {(physical.dim, physical.tag): physical.name for physical in mesh.physical_names}


def _element_physical_key(element: Element) -> tuple[int, int] | None:
    return (element.entity_dim, element.physical_tags[0]) if element.physical_tags else None


def _color_by_physical_key(mesh: MshMesh) -> dict[tuple[int, int] | None, str]:
    keys = []
    for element in mesh.elements:
        key = _element_physical_key(element)
        if key not in keys:
            keys.append(key)
    return {key: PALETTE[index % len(PALETTE)] for index, key in enumerate(keys)}


def _legend(mesh: MshMesh) -> str:
    names = _physical_name_by_key(mesh)
    colors = _color_by_physical_key(mesh)
    rows = []
    for key, color in colors.items():
        if key is None:
            label = "unassigned"
        else:
            label = names.get(key, f"dim {key[0]} physical {key[1]}")
        rows.append(
            '<div class="legend-row">'
            f'<span class="swatch" style="background:{color}"></span>'
            f"<span>{html.escape(label)}</span>"
            "</div>"
        )
    if not rows:
        return ""
    return "<h2>Physical Groups</h2>" + "".join(rows)


def _compact_summary(summary: dict[str, object]) -> str:
    lines = [
        f"nodes: {summary.get('nodes')}",
        f"elements: {summary.get('elements')}",
        f"bbox: {summary.get('bounding_box')}",
        f"element types: {summary.get('elements_by_type')}",
    ]
    warnings = summary.get("warnings")
    if warnings:
        lines.append(f"warnings: {warnings}")
    return "\n".join(lines)
