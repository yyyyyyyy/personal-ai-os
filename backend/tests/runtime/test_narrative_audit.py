"""Narrative audit builder — Identity RFC §3.3."""

from app.core.runtime.projection.narrative_audit import build_narrative_audit

_TRAJECTORIES = [
    {
        "id": "career-entrepreneurship-2026",
        "description": "entrepreneurship impulse",
        "domain": "career",
        "competing_with": ["career-corporate-stability-2026"],
    },
    {
        "id": "career-corporate-stability-2026",
        "description": "corporate stability",
        "domain": "career",
        "competing_with": ["career-entrepreneurship-2026"],
    },
]


def test_build_audit_cites_trajectories_and_beliefs():
    content = (
        "## 轨迹视角\n"
        "- career-entrepreneurship-2026: entrepreneurship\n"
        "- career-corporate-stability-2026: corporate\n"
        "系统认为可能：用户倾向创业\n"
    )
    memories = [
        {
            "id": "blf-audit",
            "origin": "claim",
            "claim_status": "proposed",
            "content": "用户倾向创业",
        },
    ]
    audit = build_narrative_audit(
        content,
        _TRAJECTORIES,
        memories=memories,
        events=[{"type": "outcome", "seq": 500, "payload": {"evidence_type": "outcome"}}],
        trajectory_link_seqs={"career-entrepreneurship-2026": [10, 11]},
    )
    assert "career-entrepreneurship-2026" in audit["cited_trajectory_ids"]
    assert len(audit["cited_beliefs"]) == 1
    assert audit["cited_beliefs"][0]["memory_id"] == "blf-audit"
    assert 500 in audit["outcome_event_seqs"]
    assert audit["identity_claims"]
    ent_claim = next(
        c for c in audit["identity_claims"]
        if "entrepreneurship" in c["text"]
    )
    assert 10 in ent_claim["evidence_event_seqs"]
