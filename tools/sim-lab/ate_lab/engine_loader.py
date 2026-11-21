"""Load ``ate_sim`` from this install and nothing else."""

from __future__ import annotations

from .paths import ensure_engine_path


def import_engine():
    ensure_engine_path()
    import ate_sim.checkpoint as checkpoint
    import ate_sim.core as core
    import ate_sim.engine as engine
    import ate_sim.query as query
    import ate_sim.worldgen as worldgen
    from ate_sim.advancement import RANKS
    from ate_sim.personhood import from_person

    return {
        "checkpoint": checkpoint,
        "core": core,
        "engine": engine,
        "query": query,
        "worldgen": worldgen,
        "RANKS": RANKS,
        "from_person": from_person,
    }
