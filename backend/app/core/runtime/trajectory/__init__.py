"""Trajectory layer — continuity interpretations (see docs/rfc/TRAJECTORY_RFC.md)."""

from app.core.runtime.trajectory import identity_authority, link_authority
from app.core.runtime.trajectory.engine import (
    link_event,
    list_trajectories,
    load_merged_registry,
    query_trajectory,
    register_trajectory,
    verify_competing_symmetry,
)
from app.core.runtime.trajectory.suggester import trajectory_suggester

__all__ = [
    "identity_authority",
    "link_authority",
    "trajectory_suggester",
    "link_event",
    "list_trajectories",
    "load_merged_registry",
    "query_trajectory",
    "register_trajectory",
    "verify_competing_symmetry",
]
