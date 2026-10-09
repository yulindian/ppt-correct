import importlib.util
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "scripts" / "audit_ppt_layout_contract.py"
SPEC = importlib.util.spec_from_file_location("audit_ppt_layout_contract", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LayoutContractTests(unittest.TestCase):
    def test_automatic_wrap_risk_without_explicit_newline_is_rejected(self):
        label = shape(16, 10, "国内", 26, 0, 0, 200000, 500000)
        label["format"].update(wrap=True, autoFit="shape")
        report = MODULE.audit({"results": [label]}, {"textConstraints": [{
            "slide": 16, "shapeId": 10, "singleLine": True,
            "minWidth": "65pt", "minHeight": "30pt",
            "sizePtRange": [25, 27], "referenceEvidence": "Two characters on one horizontal line in PDF tab."
        }]})
        codes = {issue["code"] for issue in report["issues"]}
        self.assertIn("single_line_wrap_enabled_or_unresolved", codes)
        self.assertIn("single_line_autofit", codes)
        self.assertIn("text_width_below_reference", codes)

    def test_equal_but_undersized_peers_fail_reference_size(self):
        peers = [shape(16, n, "说明", 14, 0, 0, 1000000, 500000) for n in (11, 16)]
        contract = {"peerGroups": [{"slide": 16, "shapeIds": [11, 16], "equal": ["size"]}],
                    "textConstraints": [{"slide": 16, "shapeId": n, "sizePtRange": [20, 22],
                                         "referenceEvidence": "PDF-verified body tier."} for n in (11, 16)]}
        report = MODULE.audit({"results": peers}, contract)
        self.assertEqual(2, sum(issue["code"] == "text_size_outside_reference" for issue in report["issues"]))

    def test_fixed_single_line_with_reference_geometry_passes(self):
        label = shape(16, 10, "国内", 26, 0, 0, 900000, 500000)
        label["format"]["wrap"] = False
        report = MODULE.audit({"results": [label]}, {"textConstraints": [{
            "slide": 16, "shapeId": 10, "singleLine": True, "minWidth": "65pt",
            "minHeight": "30pt", "sizePtRange": [25, 27], "referenceEvidence": "PDF horizontal tab."
        }]})
        self.assertTrue(report["passed"], report)

    def test_unresolved_wrap_and_missing_reference_cannot_pass(self):
        report = MODULE.audit({"results": [shape(1, 1, "国内", 26, 0, 0, 900000, 500000)]},
                              {"textConstraints": [{"slide": 1, "shapeId": 1, "singleLine": True}]})
        codes = {issue["code"] for issue in report["issues"]}
        self.assertIn("text_reference_missing", codes)
        self.assertIn("single_line_width_target_missing", codes)
        self.assertIn("single_line_wrap_enabled_or_unresolved", codes)

    def test_rejects_mismatched_peers_and_unsafe_answer_overlay(self):
        query = {
            "results": [
                shape(4, 14, "法律规范着\n我们的行为", 20, 100, 100, 300, 120),
                shape(4, 18, "法律保护着\n我们的权利", 20, 500, 100, 300, 120),
                shape(4, 22, "法律协调\n人与人之间的\n关系", 24, 900, 100, 300, 120),
                shape(22, 19, "判断题干（）", 29, 100, 300, 500, 80),
                shape(22, 9201, "（✔）", 29, 650, 300, 100, 80),
            ]
        }
        contract = {
            "slideSize": {"width": 1000, "height": 600},
            "peerGroups": [
                {
                    "slide": 4,
                    "name": "three-law-functions",
                    "shapeIds": [14, 18, 22],
                    "expectedCount": 3,
                    "equal": ["font", "size", "bold", "align", "autoFit"],
                    "maxLines": 2,
                }
            ],
            "answerOverlays": [
                {
                    "slide": 22,
                    "stemShapeId": 19,
                    "answerShapeId": 9201,
                    "answerGlyph": "✔",
                    "stemPlaceholder": "（）",
                    "requireInsideStem": True,
                }
            ],
        }

        report = MODULE.audit(query, contract)

        self.assertFalse(report["passed"])
        codes = {issue["code"] for issue in report["issues"]}
        self.assertIn("peer_size_mismatch", codes)
        self.assertIn("peer_line_count", codes)
        self.assertIn("answer_not_glyph_only", codes)
        self.assertIn("answer_outside_stem", codes)

    def test_accepts_equal_peers_and_glyph_only_answer_inside_stem(self):
        query = {
            "results": [
                shape(4, 14, "法律规范着\n我们的行为", 22, 100, 100, 300, 120),
                shape(4, 18, "法律保护着\n我们的权利", 22, 500, 100, 300, 120),
                shape(4, 22, "法律协调着\n人与人关系", 22, 900, 100, 300, 120),
                shape(22, 19, "判断题干（）", 29, 100, 300, 600, 80),
                shape(22, 9201, "✔", 29, 580, 300, 60, 80),
            ]
        }
        contract = {
            "slideSize": {"width": 1300, "height": 600},
            "peerGroups": [
                {
                    "slide": 4,
                    "name": "three-law-functions",
                    "shapeIds": [14, 18, 22],
                    "expectedCount": 3,
                    "equal": ["font", "size", "bold", "align", "autoFit"],
                    "maxLines": 2,
                }
            ],
            "answerOverlays": [
                {
                    "slide": 22,
                    "stemShapeId": 19,
                    "answerShapeId": 9201,
                    "answerGlyph": "✔",
                    "stemPlaceholder": "（）",
                    "requireInsideStem": True,
                }
            ],
        }

        report = MODULE.audit(query, contract)

        self.assertTrue(report["passed"], report)


def shape(slide, shape_id, text, size, x, y, width, height):
    return {
        "path": f"/slide[{slide}]/shape[@id={shape_id}]",
        "text": text,
        "format": {
            "font": "Noto Sans SC",
            "size": f"{size}pt",
            "bold": True,
            "align": "left",
            "autoFit": "none",
            "x": f"{x}emu",
            "y": f"{y}emu",
            "width": f"{width}emu",
            "height": f"{height}emu",
        },
    }


if __name__ == "__main__":
    unittest.main()
