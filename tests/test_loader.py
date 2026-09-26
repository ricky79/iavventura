from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from app.engine.loader import INDEX_FILE, WORLDS_DIR, WorldError, load_adventures, load_world, parse_world


def write_yaml(directory: Path, name: str, data: dict) -> None:
    (directory / name).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def write_text(directory: Path, name: str, text: str) -> None:
    (directory / name).write_text(dedent(text), encoding="utf-8")


@pytest.fixture
def world_dir(tmp_path: Path, world_data: dict) -> Path:
    """The minimal world split across two files, as the real one is."""
    write_yaml(tmp_path, "gioco.yaml", {"game": world_data["game"], "rooms": world_data["rooms"]})
    write_yaml(tmp_path, "oggetti.yaml", {"items": world_data["items"], "rules": world_data["rules"]})
    return tmp_path


def test_sections_from_several_files_are_merged(world_dir):
    world = load_world(world_dir)

    assert world.game.start_room == "atrio"
    assert set(world.rooms) == {"atrio", "cella"}
    assert set(world.items) == {"leva", "moneta", "chiave"}
    assert set(world.rules) == {"tira_leva", "usa_moneta"}


def test_same_section_may_continue_in_another_file(world_dir):
    write_text(world_dir, "extra.yaml", """
        items:
          sasso:
            name: sasso
            gender: m
            description: Un sasso.
            location: cella
    """)

    world = load_world(world_dir)

    assert world.items["sasso"].location == "cella"
    assert "moneta" in world.items


def test_empty_directory_is_rejected(tmp_path):
    with pytest.raises(WorldError):
        load_world(tmp_path)


def test_yaml_syntax_error_reports_file_and_line(world_dir):
    write_text(world_dir, "rotto.yaml", """
        rooms:
          sala: [non chiusa
    """)

    with pytest.raises(WorldError) as exc:
        load_world(world_dir)

    assert "rotto.yaml" in str(exc.value)
    assert "line" in str(exc.value)


def test_duplicate_key_in_a_file_is_rejected(world_dir):
    # Plain PyYAML would silently keep only the second definition.
    write_text(world_dir, "doppio.yaml", """
        items:
          sasso:
            name: sasso
            description: Un sasso.
            location: cella
          sasso:
            name: sasso
            description: Un altro sasso.
            location: atrio
    """)

    with pytest.raises(WorldError) as exc:
        load_world(world_dir)

    assert "doppio.yaml" in str(exc.value)
    assert "line 7" in str(exc.value)
    assert "sasso" in str(exc.value)


def test_key_read_as_boolean_is_rejected(world_dir):
    # YAML 1.1 turns an unquoted `on:` key into True.
    write_text(world_dir, "regole.yaml", """
        rules:
          spingi_sasso:
            on: {verb: spingi, target: leva}
            text: Niente.
    """)

    with pytest.raises(WorldError) as exc:
        load_world(world_dir)

    assert "regole.yaml" in str(exc.value)
    assert "line 4" in str(exc.value)


def test_file_that_is_not_a_mapping_is_rejected(world_dir):
    write_text(world_dir, "lista.yaml", """
        - atrio
        - cella
    """)

    with pytest.raises(WorldError) as exc:
        load_world(world_dir)

    assert "lista.yaml" in str(exc.value)


def test_same_id_in_two_files_is_rejected(world_dir):
    write_text(world_dir, "altre_stanze.yaml", """
        rooms:
          atrio:
            name: Atrio bis
            description: Un secondo atrio.
    """)

    with pytest.raises(WorldError) as exc:
        load_world(world_dir)

    problem = next(p for p in exc.value.problems if "rooms.atrio" in p)
    assert "gioco.yaml" in problem
    assert "altre_stanze.yaml" in problem


def test_game_defined_twice_is_rejected(world_dir, world_data):
    write_yaml(world_dir, "secondo_gioco.yaml", {"game": world_data["game"]})

    with pytest.raises(WorldError) as exc:
        load_world(world_dir)

    problem = next(p for p in exc.value.problems if "game" in p)
    assert "gioco.yaml" in problem
    assert "secondo_gioco.yaml" in problem


def test_missing_game_is_rejected(tmp_path, world_data):
    write_yaml(tmp_path, "stanze.yaml", {"rooms": world_data["rooms"]})

    with pytest.raises(WorldError) as exc:
        load_world(tmp_path)

    assert any(problem.startswith("game") for problem in exc.value.problems)


def test_misspelled_section_is_rejected(world_dir):
    write_text(world_dir, "refuso.yaml", """
        itmes:
          sasso:
            name: sasso
            gender: m
    """)

    with pytest.raises(WorldError) as exc:
        load_world(world_dir)

    assert any(problem.startswith("itmes") for problem in exc.value.problems)


def test_structural_errors_are_reported_with_their_path(world_dir):
    write_text(world_dir, "refuso.yaml", """
        items:
          sasso:
            name: sasso
            gender: m
            descripton: Un sasso.
            location: cella
    """)

    with pytest.raises(WorldError) as exc:
        load_world(world_dir)

    assert any(problem.startswith("items.sasso.descripton") for problem in exc.value.problems)


def test_cross_reference_problems_are_reported(world_dir):
    write_text(world_dir, "extra.yaml", """
        items:
          sasso:
            name: sasso
            gender: m
            description: Un sasso.
            location: cantina
    """)

    with pytest.raises(WorldError) as exc:
        load_world(world_dir)

    assert any("items.sasso.location" in problem and "cantina" in problem for problem in exc.value.problems)


# --- Several adventures ------------------------------------------------------------------------------


@pytest.fixture
def worlds_root(tmp_path: Path, world_data: dict) -> Path:
    """Two adventures, listed in the index in the opposite of alphabetical order."""
    for adventure_id in ("zeta", "alfa"):
        directory = tmp_path / adventure_id
        directory.mkdir()
        write_yaml(directory, "gioco.yaml", {**world_data, "game": {**world_data["game"], "title": adventure_id.title()}})
    write_yaml(tmp_path, INDEX_FILE, {"adventures": ["zeta", "alfa"]})
    return tmp_path


def test_adventures_come_in_the_order_of_the_index(worlds_root):
    worlds = load_adventures(worlds_root)

    assert list(worlds) == ["zeta", "alfa"]
    assert worlds["alfa"].game.title == "Alfa"


def test_a_folder_that_is_not_in_the_index_is_not_loaded(worlds_root):
    write_yaml(worlds_root, INDEX_FILE, {"adventures": ["alfa"]})

    assert list(load_adventures(worlds_root)) == ["alfa"]


def test_a_missing_index_is_rejected(worlds_root):
    (worlds_root / INDEX_FILE).unlink()

    with pytest.raises(WorldError) as exc:
        load_adventures(worlds_root)

    assert exc.value.problems == [f"{INDEX_FILE}: not found in {worlds_root}"]


@pytest.mark.parametrize(
    "index",
    [{"adventures": []}, {"adventures": "alfa"}, {"avventure": ["alfa"]}, ["alfa"], {"adventures": ["Alfa!"]}],
    ids=["empty", "not a list", "misspelled key", "not a mapping", "not an id"],
)
def test_a_malformed_index_is_rejected(worlds_root, index):
    write_yaml(worlds_root, INDEX_FILE, index)

    with pytest.raises(WorldError) as exc:
        load_adventures(worlds_root)

    assert all(problem.startswith(f"{INDEX_FILE}: ") for problem in exc.value.problems)


def test_an_adventure_listed_twice_is_rejected(worlds_root):
    write_yaml(worlds_root, INDEX_FILE, {"adventures": ["alfa", "zeta", "alfa"]})

    with pytest.raises(WorldError) as exc:
        load_adventures(worlds_root)

    assert exc.value.problems == [f"{INDEX_FILE}: 'alfa' is listed twice"]


def test_a_listed_adventure_without_its_folder_is_rejected(worlds_root):
    write_yaml(worlds_root, INDEX_FILE, {"adventures": ["alfa", "beta"]})

    with pytest.raises(WorldError) as exc:
        load_adventures(worlds_root)

    assert exc.value.problems == ["beta: folder not found"]


def test_the_problems_of_every_adventure_come_with_its_id(worlds_root):
    write_text(worlds_root / "alfa", "rotto.yaml", """
        rooms:
          sala: [non chiusa
    """)
    write_text(worlds_root / "zeta", "extra.yaml", """
        items:
          sasso:
            name: sasso
            gender: m
            description: Un sasso.
            location: soffitta
    """)

    with pytest.raises(WorldError) as exc:
        load_adventures(worlds_root)

    problems = exc.value.problems
    assert any(problem.startswith("zeta: ") and "soffitta" in problem for problem in problems)
    assert any(problem.startswith("alfa: rotto.yaml, line ") for problem in problems)


def test_the_summary_for_the_menu_is_required(world_data):
    del world_data["game"]["summary"]

    with pytest.raises(WorldError) as exc:
        parse_world(world_data)

    assert "game.summary: Field required" in exc.value.problems


def test_the_real_adventures_load():
    worlds = load_adventures()

    assert list(worlds) == ["rocca"]
    assert worlds["rocca"].game.title == "La Rocca di Serravento"
    assert load_world(WORLDS_DIR / "rocca") == worlds["rocca"]
