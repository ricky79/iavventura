import pytest


@pytest.fixture
def world_data() -> dict:
    """A small but complete world; each test mutates a fresh copy to provoke one error."""
    return {
        "game": {
            "title": "Prova",
            "intro": "Inizio.",
            "start_room": "atrio",
            "endings": [{"when": {"player_in": "cella"}, "text": "Fine."}],
        },
        "rooms": {
            "atrio": {
                "name": "Atrio",
                "description": "Un atrio spoglio.",
                "exits": {
                    "nord": {
                        "to": "cella",
                        "when": {"flag": "porta_aperta"},
                        "otherwise": "La porta è chiusa.",
                    },
                },
            },
            "cella": {
                "name": "Cella",
                "description": "Una cella umida.",
                "exits": {"sud": {"to": "atrio"}},
            },
        },
        "items": {
            "leva": {
                "name": "leva",
                "description": "Una leva arrugginita.",
                "location": "atrio",
                "scenery": True,
            },
            "moneta": {
                "name": "moneta",
                "aliases": ["soldo"],
                "description": "Una moneta consumata.",
                "location": "inventory",
            },
            "chiave": {
                "name": "chiave",
                "description": "Una chiave piccola.",
                "location": None,
            },
        },
        "rules": {
            "tira_leva": {
                "trigger": {"verb": "tira", "target": "leva"},
                "when": {"not": {"flag": "porta_aperta"}},
                "otherwise": "La leva non si muove più.",
                "effects": [{"set_flag": "porta_aperta"}, {"give": "chiave"}],
                "text": "Clac! Qualcosa cade ai tuoi piedi.",
            },
            "usa_moneta": {
                "trigger": {"verb": "usa", "target": "leva", "with": "moneta"},
                "text": "Non succede niente.",
            },
        },
    }
