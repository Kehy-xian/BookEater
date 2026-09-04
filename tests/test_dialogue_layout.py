from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.pet_window_v8 import dialogue_layout


def test_dialogue_layout_never_exceeds_three_lines_or_canvas_height():
    rendered, font_size, height = dialogue_layout('아주 긴 대사가 말풍선 배경을 벗어나거나 아래쪽에서 잘리지 않도록 여러 줄로 안전하게 배치합니다. ' * 3)
    assert len(rendered.splitlines()) <= 3
    assert rendered.endswith('…')
    assert font_size == 7
    assert height <= 60
