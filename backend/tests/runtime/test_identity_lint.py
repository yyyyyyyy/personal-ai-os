"""Identity RFC N1–N4 narrative lint."""

from app.core.runtime.projection.identity_lint import lint_review_content


def test_n2_detects_destiny_framing():
    issues = lint_review_content("你就是这样的人，适合创业。")
    assert any("N2" in i for i in issues)


def test_n3_detects_outcome_epilogue():
    issues = lint_review_content("事实证明你当年的选择是正确的。")
    assert any("N3" in i for i in issues)


def test_clean_projection_content_passes_n2_n3():
    content = (
        "> 系统投影草稿\n\n## 轨迹视角\n"
        "- a: desc （竞争轨迹: b）\n"
    )
    trajectories = [
        {"id": "a", "competing_with": ["b"]},
        {"id": "b", "competing_with": ["a"]},
    ]
    fails = [i for i in lint_review_content(content, trajectories=trajectories) if i.startswith("FAIL")]
    assert fails == []
