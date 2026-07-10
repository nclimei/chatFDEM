from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from chatfdem.gmsh_runner import mesh_geo
from chatfdem.inp import read_inp
from chatfdem.msh import read_msh
from chatfdem.preview import write_html_preview
from chatfdem.nl import generate_geo_from_prompt
from chatfdem.workflow import run_prompt_workflow


REPO_ROOT = Path(__file__).resolve().parents[1]


class LlmGeoGenerationTest(unittest.TestCase):
    def test_fixture_provider_returns_geo_payload(self) -> None:
        generation = generate_geo_from_prompt(
            "Create a rectangular rock specimen 100 mm wide and 50 mm high with a centered 10 mm diameter hole.",
            provider="fixture",
        )
        self.assertEqual("fixture", generation.provider)
        self.assertIn("Physical Surface", generation.geo_text)
        self.assertIn("Physical Curve", generation.geo_text)
        self.assertEqual(100.0, generation.brief["width"])
        self.assertEqual("mm", generation.brief["units"])


@unittest.skipIf(shutil.which("gmsh") is None, "gmsh executable is not installed")
class MvpWorkflowTest(unittest.TestCase):
    def test_rect_hole_geo_generates_mesh_inp_and_preview(self) -> None:
        geo_path = REPO_ROOT / "examples" / "geo" / "rect_hole.geo"
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            result = mesh_geo(
                geo_path,
                msh_path=tmp / "rect_hole.msh",
                inp_path=tmp / "rect_hole.inp",
            )
            mesh = read_msh(result.msh_path)
            mesh_summary = mesh.summary()
            self.assertGreater(mesh_summary["nodes"], 0)
            self.assertGreater(mesh_summary["elements"], 0)
            physical_names = {
                group["name"] for group in mesh_summary["physical_groups"] if group["name"]
            }
            self.assertIn("matrix", physical_names)
            self.assertIn("hole", physical_names)
            self.assertIn("left", physical_names)
            self.assertIn("left", mesh_summary["boundary_node_sets"])
            self.assertIn("hole", mesh_summary["boundary_node_sets"])
            self.assertFalse(mesh_summary["warnings"])

            self.assertGreater(result.appended_node_sets["left"], 0)
            self.assertGreater(result.appended_node_sets["hole"], 0)

            inp_summary = read_inp(result.inp_path).summary()
            self.assertGreater(inp_summary["nodes"], 0)
            self.assertGreater(inp_summary["elements"], 0)
            self.assertIn("matrix", inp_summary["element_sets"])
            self.assertIn("left", inp_summary["node_sets"])
            self.assertIn("right", inp_summary["node_sets"])
            self.assertIn("hole", inp_summary["node_sets"])

            preview_path = write_html_preview(result.msh_path, tmp / "rect_hole_preview.html")
            self.assertTrue(preview_path.is_file())
            self.assertIn("Physical Groups", preview_path.read_text(encoding="utf-8"))

    def test_mesh_geo_can_skip_inp_export(self) -> None:
        geo_path = REPO_ROOT / "examples" / "geo" / "rect_hole.geo"
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            result = mesh_geo(
                geo_path,
                msh_path=tmp / "rect_hole.msh",
                export_inp=False,
            )
            self.assertTrue(result.msh_path.is_file())
            self.assertIsNone(result.inp_path)
            self.assertEqual({}, result.appended_node_sets)
            self.assertFalse((tmp / "rect_hole.inp").exists())

    def test_prompt_workflow_generates_artifacts(self) -> None:
        prompt = (
            "Create a 2D rectangular rock specimen 100 mm wide and 50 mm high with a centered "
            "10 mm diameter circular hole. Use finer mesh near the hole."
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            run = run_prompt_workflow(prompt, runs_root=Path(tmp_dir), name="prompt_rect_hole", llm_provider="fixture")
            self.assertTrue(run.geo_path.is_file())
            self.assertTrue(run.msh_path.is_file())
            self.assertTrue(run.inp_path.is_file())
            self.assertTrue(run.preview_path.is_file())
            self.assertTrue(run.report_path.is_file())
            self.assertEqual(100.0, run.generation.brief["width"])
            self.assertIn("matrix", run.inp_summary["element_sets"])
            self.assertIn("hole", run.inp_summary["node_sets"])


if __name__ == "__main__":
    unittest.main()
