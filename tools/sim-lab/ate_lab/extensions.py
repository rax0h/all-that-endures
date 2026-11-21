"""Navigation registry. Views the interface does not implement stay marked unbuilt."""

MODULES = [
    {"id": "control", "label": "Control", "group": "Run", "implemented": True},
    {"id": "observatory", "label": "Observatory", "group": "World", "implemented": True},
    {"id": "inspector", "label": "Inspector", "group": "World", "implemented": True},
    {"id": "timeline", "label": "Timeline", "group": "World", "implemented": True},
    {"id": "performance", "label": "Performance", "group": "Engineering", "implemented": True},
    {"id": "checkpoints", "label": "Checkpoints", "group": "Engineering", "implemented": True},
    {"id": "settings", "label": "Settings", "group": "Application", "implemented": True},
]

FUTURE = [
    {"id": "world-map", "label": "World map", "implemented": False,
     "note": "Cell fields and settlement coordinates are already in the observatory."},
    {"id": "family-tree", "label": "Family tree", "implemented": False,
     "note": "Genealogy links are already on the person inspector."},
    {"id": "economy-flow", "label": "Economic flow", "implemented": False,
     "note": "Current stocks and minted coin are shown; flow over time is not retained."},
    {"id": "progression", "label": "Progression analysis", "implemented": False,
     "note": "Essence paths and ranks are on the inspector and in rank totals."},
    {"id": "replay", "label": "Historical replay", "implemented": False,
     "note": "The event ledger can be filtered by year. There is no visual replay."},
]
