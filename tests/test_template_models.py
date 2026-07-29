"""模板資料結構單元測試（Streamlit UI 用）。"""

from src.template_models import (
    AnimIn,
    GlobalSettings,
    MediaType,
    PositionPreset,
    ProjectTemplate,
    Transform2D,
    create_default_template,
    create_empty_shot,
    template_from_dict,
    template_to_dict,
)


def test_default_template_has_hook():
    t = create_default_template("單元測試", with_hook=True)
    assert t.global_settings.project_name == "單元測試"
    assert t.global_settings.width == 1080
    assert t.global_settings.height == 1920
    assert len(t.shots) == 1
    assert t.shots[0].is_hook is True
    assert t.shots[0].media[0].media_type == MediaType.image
    assert t.total_duration() == 3.0


def test_roundtrip_dict_json():
    t = create_default_template("往返", with_hook=True)
    d = template_to_dict(t)
    t2 = template_from_dict(d)
    assert t2.global_settings.project_name == "往返"
    j = t2.model_dump_json_pretty()
    t3 = ProjectTemplate.model_validate_json(j)
    assert t3.shots[0].name == "開頭鈎子"


def test_transform_apply_preset():
    tr = Transform2D(position_preset=PositionPreset.top_right, x=0, y=0)
    applied = tr.apply_preset()
    assert applied.x > 0
    assert applied.y > 0


def test_empty_shot_not_hook():
    s = create_empty_shot(2, is_hook=False)
    assert s.is_hook is False
    assert "2" in s.name or s.name.startswith("分鏡")


def test_global_settings_resolution_label():
    g = GlobalSettings(width=1080, height=1920)
    assert "1080" in g.resolution_label
    g2 = GlobalSettings(width=999, height=888)
    assert g2.resolution_label == "自訂"


def test_media_anim_defaults():
    t = create_default_template(with_hook=True)
    media = t.shots[0].media[0]
    assert media.anim_in == AnimIn.zoom_in
