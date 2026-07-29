"""分鏡操作相關的純邏輯測試（不依賴 Streamlit 畫面）。"""

from src.template_models import (
    create_default_template,
    create_empty_shot,
)


def test_add_many_shots():
    t = create_default_template("多鏡", with_hook=True)
    for i in range(2, 25):
        t.shots.append(create_empty_shot(i, is_hook=False))
    assert len(t.shots) == 24
    assert t.shots[0].is_hook is True
    assert t.total_duration() == 24 * 3.0


def test_move_shot_order():
    t = create_default_template("排序", with_hook=True)
    t.shots.append(create_empty_shot(2))
    t.shots.append(create_empty_shot(3))
    ids = [s.id for s in t.shots]
    # 手動交換 0 與 1
    shots = list(t.shots)
    shots[0], shots[1] = shots[1], shots[0]
    t2 = t.model_copy(update={"shots": shots})
    assert t2.shots[0].id == ids[1]
    assert t2.shots[1].id == ids[0]


def test_single_hook_semantics():
    t = create_default_template("鈎子", with_hook=True)
    t.shots.append(create_empty_shot(2, is_hook=False))
    # 模擬只允許一個鈎子：設第二個為鈎子時清掉第一個
    new_shots = []
    target = t.shots[1].id
    for s in t.shots:
        new_shots.append(s.model_copy(update={"is_hook": s.id == target}))
    t2 = t.model_copy(update={"shots": new_shots})
    assert t2.shots[0].is_hook is False
    assert t2.shots[1].is_hook is True
