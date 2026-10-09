from __future__ import annotations

import html
import json
from collections import Counter
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

SURFACE_TRIANGLES = {
    2: ((0, 1, 2),),
    3: ((0, 1, 2), (0, 2, 3)),
    9: ((0, 1, 2),),
    10: ((0, 1, 2), (0, 2, 3)),
    16: ((0, 1, 2), (0, 2, 3)),
    21: ((0, 1, 2),),
    23: ((0, 1, 2),),
}

VOLUME_FACES = {
    4: ((0, 1, 2), (0, 1, 3), (1, 2, 3), (2, 0, 3)),
    5: (
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ),
    6: ((0, 1, 2), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)),
    7: ((0, 1, 2, 3), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)),
    11: ((0, 1, 2), (0, 1, 3), (1, 2, 3), (2, 0, 3)),
    17: (
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ),
    18: ((0, 1, 2), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)),
    19: ((0, 1, 2, 3), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)),
    29: ((0, 1, 2), (0, 1, 3), (1, 2, 3), (2, 0, 3)),
    30: ((0, 1, 2), (0, 1, 3), (1, 2, 3), (2, 0, 3)),
    31: ((0, 1, 2), (0, 1, 3), (1, 2, 3), (2, 0, 3)),
}

VIEWER_SCRIPT = r"""
(() => {
  const root = document.querySelector(".mesh-preview-3d");
  const canvas = document.getElementById("mesh-preview-canvas");
  const source = document.getElementById("mesh-preview-data");
  if (!root || !canvas || !source) return;

  const data = JSON.parse(source.textContent);
  const context = canvas.getContext("2d");
  const boundsMin = data.bbox.min;
  const boundsMax = data.bbox.max;
  const center = [
    (boundsMin[0] + boundsMax[0]) / 2,
    (boundsMin[1] + boundsMax[1]) / 2,
    (boundsMin[2] + boundsMax[2]) / 2,
  ];
  const span = Math.max(
    boundsMax[0] - boundsMin[0],
    boundsMax[1] - boundsMin[1],
    boundsMax[2] - boundsMin[2],
    1e-9
  );
  const state = {
    yaw: -0.72,
    pitch: 0.58,
    zoom: 1,
    panX: 0,
    panY: 0,
    dragging: false,
    dragMode: "rotate",
    lastX: 0,
    lastY: 0,
  };

  function resize() {
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.floor(canvas.clientWidth));
    const height = Math.max(1, Math.floor(canvas.clientHeight));
    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    render();
  }

  function project(point, width, height) {
    const x = (point[0] - center[0]) / span;
    const y = (point[1] - center[1]) / span;
    const z = (point[2] - center[2]) / span;
    const yawCos = Math.cos(state.yaw);
    const yawSin = Math.sin(state.yaw);
    const rotatedX = x * yawCos + z * yawSin;
    const rotatedZ = -x * yawSin + z * yawCos;
    const pitchCos = Math.cos(state.pitch);
    const pitchSin = Math.sin(state.pitch);
    const rotatedY = y * pitchCos - rotatedZ * pitchSin;
    const depth = y * pitchSin + rotatedZ * pitchCos;
    const scale = Math.min(width, height) * 0.72 * state.zoom;
    return {
      x: width / 2 + state.panX + rotatedX * scale,
      y: height / 2 + state.panY - rotatedY * scale,
      depth,
    };
  }

  function render() {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    const projected = data.nodes.map((node) => project(node, width, height));
    context.clearRect(0, 0, width, height);
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, width, height);

    const triangles = data.triangles.map((triangle) => ({
      a: projected[triangle[0]],
      b: projected[triangle[1]],
      c: projected[triangle[2]],
      color: triangle[3],
      depth: (projected[triangle[0]].depth + projected[triangle[1]].depth + projected[triangle[2]].depth) / 3,
    }));
    triangles.sort((left, right) => left.depth - right.depth);

    for (const triangle of triangles) {
      context.beginPath();
      context.moveTo(triangle.a.x, triangle.a.y);
      context.lineTo(triangle.b.x, triangle.b.y);
      context.lineTo(triangle.c.x, triangle.c.y);
      context.closePath();
      context.globalAlpha = 0.78;
      context.fillStyle = triangle.color;
      context.fill();
      context.globalAlpha = 1;
      context.strokeStyle = "#26313f";
      context.lineWidth = 0.75;
      context.stroke();
    }

    context.lineWidth = 1.4;
    for (const line of data.lines) {
      const points = line[0].map((index) => projected[index]).filter(Boolean);
      if (points.length < 2) continue;
      context.beginPath();
      context.moveTo(points[0].x, points[0].y);
      for (const point of points.slice(1)) context.lineTo(point.x, point.y);
      context.strokeStyle = line[1];
      context.stroke();
    }
  }

  function resetView() {
    state.yaw = -0.72;
    state.pitch = 0.58;
    state.zoom = 1;
    state.panX = 0;
    state.panY = 0;
    render();
  }

  canvas.addEventListener("pointerdown", (event) => {
    state.dragging = true;
    state.dragMode = event.shiftKey ? "pan" : "rotate";
    state.lastX = event.clientX;
    state.lastY = event.clientY;
    canvas.classList.add("is-dragging");
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener("pointermove", (event) => {
    if (!state.dragging) return;
    const dx = event.clientX - state.lastX;
    const dy = event.clientY - state.lastY;
    state.lastX = event.clientX;
    state.lastY = event.clientY;
    if (state.dragMode === "pan") {
      state.panX += dx;
      state.panY += dy;
    } else {
      state.yaw += dx * 0.01;
      state.pitch = Math.max(-1.45, Math.min(1.45, state.pitch + dy * 0.01));
    }
    render();
  });

  function stopDrag(event) {
    state.dragging = false;
    canvas.classList.remove("is-dragging");
    if (event.pointerId !== undefined) canvas.releasePointerCapture(event.pointerId);
  }

  canvas.addEventListener("pointerup", stopDrag);
  canvas.addEventListener("pointercancel", stopDrag);
  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    state.zoom = Math.max(0.18, Math.min(8, state.zoom * Math.exp(-event.deltaY * 0.001)));
    render();
  }, { passive: false });
  canvas.addEventListener("dblclick", resetView);

  const resetButton = root.querySelector("[data-reset-view]");
  if (resetButton) resetButton.addEventListener("click", resetView);
  if ("ResizeObserver" in window) {
    new ResizeObserver(resize).observe(root);
  } else {
    window.addEventListener("resize", resize);
  }
  resize();
})();
"""


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
    elif mesh.max_element_dimension() >= 3:
        body = _canvas_3d(mesh, bbox)
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
      position: relative;
    }}
    .mesh-preview-3d {{
      min-height: calc(100vh - 34px);
      height: 100%;
      position: relative;
    }}
    .mesh-preview-3d canvas {{
      display: block;
      width: 100%;
      height: calc(100vh - 34px);
      min-height: 460px;
      cursor: grab;
      touch-action: none;
    }}
    .mesh-preview-3d canvas.is-dragging {{
      cursor: grabbing;
    }}
    .viewer-toolbar {{
      position: absolute;
      left: 12px;
      top: 12px;
      display: flex;
      gap: 10px;
      align-items: center;
      max-width: calc(100% - 24px);
      padding: 8px 10px;
      border: 1px solid rgba(38, 49, 63, 0.18);
      background: rgba(255, 255, 255, 0.88);
      color: #26313f;
      font-size: 12px;
      box-shadow: 0 8px 24px rgba(38, 49, 63, 0.10);
    }}
    .viewer-toolbar button {{
      border: 1px solid #b9c2d0;
      background: #ffffff;
      color: #26313f;
      padding: 5px 8px;
      font: inherit;
      cursor: pointer;
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
    @media (max-width: 760px) {{
      main {{
        grid-template-columns: 1fr;
      }}
      .mesh-preview-3d canvas {{
        height: 65vh;
      }}
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


def _canvas_3d(mesh: MshMesh, bbox: dict[str, list[float]]) -> str:
    data = _canvas_3d_data(mesh, bbox)
    if not data["triangles"] and not data["lines"]:
        return _svg(mesh, bbox)
    payload = _json_script_payload(data)
    return (
        '<div class="mesh-preview-3d">'
        '<canvas id="mesh-preview-canvas" aria-label="Interactive 3D mesh preview"></canvas>'
        '<div class="viewer-toolbar">'
        '<button type="button" data-reset-view>Reset</button>'
        "<span>Drag rotate. Wheel zoom. Shift-drag pan.</span>"
        "</div>"
        f'<script type="application/json" id="mesh-preview-data">{payload}</script>'
        f"<script>{VIEWER_SCRIPT}</script>"
        "</div>"
    )


def _canvas_3d_data(mesh: MshMesh, bbox: dict[str, list[float]]) -> dict[str, object]:
    node_tags = sorted(mesh.nodes)
    node_index_by_tag = {tag: index for index, tag in enumerate(node_tags)}
    nodes = [list(mesh.nodes[tag]) for tag in node_tags]
    color_by_key = _color_by_physical_key(mesh)
    triangles = _surface_canvas_triangles(mesh, node_index_by_tag, color_by_key)
    if not triangles:
        triangles = _volume_boundary_canvas_triangles(mesh, node_index_by_tag, color_by_key)
    return {
        "bbox": bbox,
        "nodes": nodes,
        "triangles": triangles,
        "lines": _canvas_lines(mesh, node_index_by_tag, color_by_key),
    }


def _surface_canvas_triangles(
    mesh: MshMesh,
    node_index_by_tag: dict[int, int],
    color_by_key: dict[tuple[int, int] | None, str],
) -> list[list[int | str]]:
    triangles: list[list[int | str]] = []
    for element in mesh.elements:
        if element.entity_dim != 2 or element.element_type not in SURFACE_TRIANGLES:
            continue
        color = color_by_key.get(_element_physical_key(element), "#8f98a8")
        for triangle in SURFACE_TRIANGLES[element.element_type]:
            node_indices = _node_indices(element.node_tags, triangle, node_index_by_tag)
            if node_indices is not None:
                triangles.append([node_indices[0], node_indices[1], node_indices[2], color])
    return triangles


def _volume_boundary_canvas_triangles(
    mesh: MshMesh,
    node_index_by_tag: dict[int, int],
    color_by_key: dict[tuple[int, int] | None, str],
) -> list[list[int | str]]:
    face_counts: Counter[tuple[int, ...]] = Counter()
    face_records: list[tuple[tuple[int, ...], tuple[int, ...], Element]] = []
    for element in mesh.elements:
        if element.entity_dim != 3 or element.element_type not in VOLUME_FACES:
            continue
        for face in VOLUME_FACES[element.element_type]:
            if max(face) >= len(element.node_tags):
                continue
            face_node_tags = tuple(element.node_tags[index] for index in face)
            key = tuple(sorted(face_node_tags))
            face_counts[key] += 1
            face_records.append((key, face_node_tags, element))

    triangles: list[list[int | str]] = []
    for key, face_node_tags, element in face_records:
        if face_counts[key] != 1:
            continue
        color = color_by_key.get(_element_physical_key(element), "#8f98a8")
        for triangle_tags in _triangulate_face(face_node_tags):
            node_indices = _node_indices(triangle_tags, range(len(triangle_tags)), node_index_by_tag)
            if node_indices is not None:
                triangles.append([node_indices[0], node_indices[1], node_indices[2], color])
    return triangles


def _canvas_lines(
    mesh: MshMesh,
    node_index_by_tag: dict[int, int],
    color_by_key: dict[tuple[int, int] | None, str],
) -> list[list[object]]:
    lines: list[list[object]] = []
    for element in mesh.elements:
        if element.element_type not in LINE_ELEMENT_TYPES:
            continue
        node_indices = [node_index_by_tag[tag] for tag in element.node_tags if tag in node_index_by_tag]
        if len(node_indices) >= 2:
            lines.append([node_indices, color_by_key.get(_element_physical_key(element), "#26313f")])
    return lines


def _triangulate_face(node_tags: tuple[int, ...]) -> tuple[tuple[int, int, int], ...]:
    if len(node_tags) == 3:
        return (node_tags,)
    if len(node_tags) == 4:
        return ((node_tags[0], node_tags[1], node_tags[2]), (node_tags[0], node_tags[2], node_tags[3]))
    return ()


def _node_indices(
    node_tags: tuple[int, ...],
    indices: tuple[int, ...] | range,
    node_index_by_tag: dict[int, int],
) -> tuple[int, ...] | None:
    result = []
    for index in indices:
        if index >= len(node_tags):
            return None
        node_tag = node_tags[index]
        if node_tag not in node_index_by_tag:
            return None
        result.append(node_index_by_tag[node_tag])
    return tuple(result)


def _json_script_payload(payload: dict[str, object]) -> str:
    text = json.dumps(payload, separators=(",", ":"))
    return text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


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
