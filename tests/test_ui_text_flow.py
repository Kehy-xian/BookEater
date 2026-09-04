from bookeater.ui_text_flow import TYPEWRITER_DELAY_MS, space_can_advance, typewriter_prefix


def test_story_text_runs_at_deliberate_shared_speed():
    assert TYPEWRITER_DELAY_MS == 84


def test_authored_line_breaks_get_more_visual_space():
    assert typewriter_prefix('첫 줄\n둘째 줄', 20) == '첫 줄\n\n둘째 줄'


def test_space_advances_story_but_never_steals_input_spaces():
    assert space_can_advance('TButton') is True
    assert space_can_advance('TEntry') is False
    assert space_can_advance('Entry') is False
    assert space_can_advance('Text') is False
