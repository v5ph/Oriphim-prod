from __future__ import annotations

from pathlib import Path

from oriphim.core.render.bundle import render_bundle, write_bundle
from oriphim.core.render.demo import demo_data
from oriphim.core.render.link import validate_scene_against_data
from oriphim.core.render.scene import Scene
from oriphim.domains.plasma.scene import default_plasma_scene


def test_bundle_is_self_contained_html() -> None:
    data = demo_data(frames=8, elements=40)
    scene = default_plasma_scene(None, data)
    html = render_bundle(scene, data)

    assert "<!DOCTYPE html>" in html
    assert 'id="stage"' in html
    assert 'id="oriphim-scene"' in html
    assert 'id="oriphim-data"' in html
    assert "window.Oriphim" in html  # the vendored renderer is inlined
    assert "1.0.0" in html
    assert "field_energy" in html  # the demo scalar made it into the embedded DATA


def test_default_plasma_scene_matches_its_data() -> None:
    data = demo_data(frames=8, elements=40)
    scene = default_plasma_scene(None, data)
    validate_scene_against_data(scene, data)  # no raise

    assert scene.camera.interactive is False  # report figure
    assert scene.world.fit == "once"
    assert [o.track for o in scene.objects] == ["field"]


def test_write_bundle_writes_a_file(tmp_path: Path) -> None:
    data = demo_data(frames=6, elements=30)
    scene = default_plasma_scene(None, data)
    out = write_bundle(tmp_path / "figure.html", scene, data)
    assert out.exists()
    assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_embedded_json_neutralises_a_closing_script_tag() -> None:
    data = demo_data(frames=4, elements=10)
    scene = Scene.model_validate(
        {
            "objects": [{"id": "field", "type": "particles", "track": "field"}],
            "provenance": {"figure": "</script><b>x"},
        }
    )
    doc = render_bundle(scene, data)
    scene_block = doc.split('id="oriphim-scene">')[1].split("</script>")[0]
    assert "</script" not in scene_block  # the "</" was escaped to "<\/"
    title = doc.split("<title>")[1].split("</title>")[0]
    assert "<" not in title  # the figure string was html-escaped
