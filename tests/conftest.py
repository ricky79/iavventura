import pytest


@pytest.fixture
def world_data() -> dict:
    """A small but complete world; each test mutates a fresh copy to provoke one error."""
    return {
        "game": {
            "title": "Prova",
            "summary": "Un mondo di prova.",
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
                "gender": "f",
                "description": "Una leva arrugginita.",
                "location": "atrio",
                "scenery": True,
            },
            "moneta": {
                "name": "moneta",
                "gender": "f",
                "aliases": ["soldo"],
                "description": "Una moneta consumata.",
                "location": "inventory",
            },
            "chiave": {
                "name": "chiave",
                "gender": "f",
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


@pytest.fixture
def keeper_world(world_data) -> dict:
    """The test world with a character in the atrium, for the tests on talking."""
    world_data["characters"] = {
        "custode": {
            "name": "custode",
            "gender": "m",
            "aliases": ["guardiano", "vecchio"],
            "description": "Un vecchio custode.",
            "variants": [{"when": {"flag": "porta_aperta"}, "text": "Un vecchio custode, a bocca aperta."}],
            "location": "atrio",
            "greeting": "«Buongiorno», dice il custode.",
            "unknown": "Il custode scuote la testa.",
            "topics": {
                "cella": {"name": "cella", "gender": "f", "aliases": ["prigione"], "text": "«La cella è a nord.»"},
                "leva": {
                    "name": "leva",
                    "gender": "f",
                    "text": "«Prova a tirarla.»",
                    "variants": [{"when": {"flag": "porta_aperta"}, "text": "«L'hai tirata, eh?»"}],
                },
                # Known only once the player has the key.
                "chiave": {
                    "name": "chiave",
                    "gender": "f",
                    "when": {"has": "chiave"},
                    "text": "«Quella chiave apre il forziere.»",
                    "effects": [{"set_flag": "forziere_noto"}],
                },
            },
        }
    }
    return world_data


@pytest.fixture
def acts_world(world_data) -> dict:
    """The test world in two acts: pulling the lever begins the second; jumping on the lever kills."""
    world_data["game"]["acts"] = [{"name": "secondo atto", "when": {"flag": "porta_aperta"}}]
    world_data["game"]["endings"].insert(0, {"when": {"flag": "caduta"}, "death": True, "text": "Sei morta."})
    world_data["rules"]["salta_leva"] = {
        "trigger": {"verb": "salta", "target": "leva"},
        "effects": [{"set_flag": "caduta"}],
        "text": "Salti sulla leva e scivoli.",
    }
    return world_data
