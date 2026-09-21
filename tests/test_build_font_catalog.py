import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "build_font_catalog.py"
SPEC = importlib.util.spec_from_file_location("build_font_catalog", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_font_record_keeps_face_index_and_visual_weight_metadata():
    record = MODULE.make_record(
        path=Path("C:/Windows/Fonts/example.ttc"),
        face_index=2,
        names={"family": "示例字体", "subfamily": "Semibold", "postscript": "Example-Semibold"},
        weight_class=600,
        italic=False,
        codepoints={ord("示"), ord("例")},
    )

    assert record["face_index"] == 2
    assert record["weight_class"] == 600
    assert record["coverage_count"] == 2
    assert record["supports_cjk"] is True
