"""Meaning Gate — chat destiny framing guard."""

from app.core.runtime.meaning_gate import gate_assistant_text


def test_softens_destiny_framing():
    out, warnings = gate_assistant_text("你就是这样的人，适合创业。")
    assert "你就是这样的人" not in out
    assert warnings


def test_softens_outcome_epilogue():
    out, warnings = gate_assistant_text("事实证明你当年的选择是正确的。")
    assert "事实证明" not in out or "回填" in out
    assert warnings


def test_clean_text_unchanged():
    text = "根据你的目标，建议先列一份 pros/cons。"
    out, warnings = gate_assistant_text(text)
    assert out == text
    assert not warnings
