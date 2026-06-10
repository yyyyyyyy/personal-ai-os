"""Belief Runtime — Projection-Driven Reflection.

Phase 1B per Cognitive Architecture:
    Pattern → Reflection → Belief

BeliefEngine consumes projections (pattern, goals, memories) — never raw events.
All output flows through BeliefFormed → projector → memories table.
"""

from .belief_engine import BeliefEngine, ReflectionContext, belief_engine

__all__ = ["BeliefEngine", "belief_engine", "ReflectionContext"]
