"""Meaning Boundary G2 — origin projection and authorship-aware rendering."""

import os

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.agents.memory_engine import memory_engine
from app.core.runtime.kernel import Kernel
from app.core.runtime.kernel.projectors import origin_from_actor
from app.store.database import Database


def _kernel(tmp_path):
    return Kernel(db=Database(db_path=str(tmp_path / "meaning_boundary.db")))


class TestOriginProjection:
    def test_origin_from_actor_mapping(self):
        assert origin_from_actor("user") == "self_report"
        assert origin_from_actor("kernel") == "claim"
        assert origin_from_actor("extractor") == "claim"
        assert origin_from_actor("import") == "claim"
        assert origin_from_actor("agent:brain") == "claim"

    def test_memory_derived_projects_origin(self, tmp_path):
        k = _kernel(tmp_path)
        k.emit_event(
            "MemoryDerived",
            "memory",
            "m-user",
            {"category": "fact", "content": "我喜欢早起", "confidence": 0.8},
            actor="user",
        )
        k.emit_event(
            "MemoryDerived",
            "memory",
            "m-sys",
            {"category": "fact", "content": "用户可能偏好夜猫子作息", "confidence": 0.6},
            actor="extractor",
        )
        user_row = k.query_state("memories", id="m-user")[0]
        sys_row = k.query_state("memories", id="m-sys")[0]
        assert user_row["origin"] == "self_report"
        assert sys_row["origin"] == "claim"

    def test_belief_formed_projects_claim_origin(self, tmp_path):
        k = _kernel(tmp_path)
        k.emit_event(
            "BeliefFormed",
            "memory",
            "blf-1",
            {
                "category": "belief",
                "content": "你重视自主性",
                "confidence": 0.65,
                "source": "reflection",
            },
            actor="kernel",
        )
        row = k.query_state("memories", id="blf-1")[0]
        assert row["origin"] == "claim"

    def test_origin_survives_rebuild(self, tmp_path):
        k = _kernel(tmp_path)
        k.emit_event(
            "MemoryDerived",
            "memory",
            "m1",
            {"category": "fact", "content": "自述内容", "confidence": 0.9},
            actor="user",
        )
        k.emit_event(
            "BeliefFormed",
            "memory",
            "m2",
            {"category": "belief", "content": "系统推断", "confidence": 0.5},
            actor="kernel",
        )
        before = {
            r["id"]: r["origin"]
            for r in k.query_state("memories", limit=10)
        }
        k.rebuild("memory")
        after = {
            r["id"]: r["origin"]
            for r in k.query_state("memories", limit=10)
        }
        assert before == after


class TestAuthorshipRendering:
    def test_format_memory_context_sections_and_order(self):
        rendered = memory_engine.format_memory_context([
            {
                "id": "c1",
                "content": "你倾向在困难时放弃项目",
                "confidence": 0.73,
                "origin": "claim",
            },
            {
                "id": "s1",
                "content": "我更重视家庭",
                "confidence": 0.9,
                "origin": "self_report",
            },
        ])
        assert "你告诉过我的（你的自述）" in rendered
        assert "系统推测（假设，非定论）" in rendered
        assert "我更重视家庭" in rendered
        assert "[推测，置信度 0.73]" in rendered
        assert "系统认为可能：你倾向在困难时放弃项目" in rendered
        assert rendered.index("你告诉过我的") < rendered.index("系统推测")

    def test_self_report_not_wrapped_as_hypothesis(self):
        rendered = memory_engine.format_memory_context([
            {
                "id": "s1",
                "content": "我是内向的人",
                "confidence": 0.9,
                "origin": "self_report",
            },
        ])
        assert "系统认为可能" not in rendered
        assert "[推测" not in rendered

    def test_unknown_origin_defaults_to_claim_framing(self):
        rendered = memory_engine.format_memory_context([
            {
                "id": "x1",
                "content": "某种推断",
                "confidence": 0.4,
                "origin": "claim",
            },
        ])
        assert "系统推测（假设，非定论）" in rendered
        assert "系统认为可能" in rendered
