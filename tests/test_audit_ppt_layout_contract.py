import importlib.util
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "scripts" / "audit_ppt_layout_contract.py"
SPEC = importlib.util.spec_from_file_location("audit_ppt_layout_contract", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LayoutContractTests(unittest.TestCase):
    def test_rejects_mismatched_peers_and_unsafe_answer_overlay(self):
        query = {
            "results": [
                shape(4, 14, "法律规范着\n我们的行为", 20, 100, 100, 300, 120),
                shape(4, 18, "法律保护着\n我们的权利", 20, 500, 100, 300, 120),
                shape(4, 22, "法律协调\n人与人之间的\n关系", 24, 900, 100, 300, 120),
                shape(22, 19, "判断题干（）", 29, 100, 300, 500, 80),
                shape(22, 9201, "（√）", 29, 650, 300, 100, 80),
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
                    "answerGlyph": "√",
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
                shape(22, 9201, "√", 29, 580, 300, 60, 80),
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
                    "answerGlyph": "√",
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
