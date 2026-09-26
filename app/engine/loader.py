"""Loads the adventures from data/worlds/ and validates them.

Each adventure is a folder of YAML files (its id is the folder's name); data/worlds/avventure.yaml
lists the ones to load, in the order of the menu. Every file of a folder may contain any of the
top-level sections (game, rooms, items, rules, characters): the sections are merged, so how a world
is split across files is only a convention.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.engine.models import Id, World
from app.engine.validation import find_problems

WORLDS_DIR = Path(__file__).resolve().parents[2] / "data" / "worlds"
INDEX_FILE = "avventure.yaml"


class WorldError(Exception):
    """The world can't be loaded; `problems` lists every reason, one per line."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("invalid world:\n" + "\n".join(f"  - {problem}" for problem in problems))


def load_world(directory: Path) -> World:
    files = sorted(directory.glob("*.yaml"))
    if not files:
        raise WorldError([f"{directory}: no .yaml files found"])

    merged: dict[str, Any] = {}
    defined_in: dict[str, str] = {}  # "game" or "section.id" -> file name
    problems: list[str] = []

    for path in files:
        try:
            content = _read_yaml(path)
        except yaml.YAMLError as exc:
            problems.append(_describe_yaml_error(path, exc))
            continue
        if content is None:
            continue
        if not isinstance(content, dict):
            problems.append(f"{path.name}: expected a mapping of sections (game, rooms, items, rules, characters)")
            continue

        for section, value in content.items():
            if section == "game":
                if "game" in defined_in:
                    problems.append(f"game: defined both in {defined_in['game']} and in {path.name}")
                else:
                    merged["game"] = value
                    defined_in["game"] = path.name
                continue
            if not isinstance(value, dict):
                problems.append(f"{section}: in {path.name} it must be a mapping of id -> definition")
                continue
            entries = merged.setdefault(section, {})
            for key, definition in value.items():
                where = f"{section}.{key}"
                if where in defined_in:
                    problems.append(f"{where}: defined both in {defined_in[where]} and in {path.name}")
                else:
                    entries[key] = definition
                    defined_in[where] = path.name

    if problems:
        raise WorldError(problems)
    return parse_world(merged)


def load_adventures(root: Path = WORLDS_DIR) -> dict[str, World]:
    """Every adventure listed in the index, keyed by its folder, in the order of the menu.

    The problems of all the adventures are reported together, each one after the id of its adventure.
    """
    worlds: dict[str, World] = {}
    problems: list[str] = []
    for adventure_id in _adventure_ids(root):
        directory = root / adventure_id
        if not directory.is_dir():
            problems.append(f"{adventure_id}: folder not found")
            continue
        try:
            worlds[adventure_id] = load_world(directory)
        except WorldError as exc:
            problems += [f"{adventure_id}: {problem}" for problem in exc.problems]
    if problems:
        raise WorldError(problems)
    return worlds


class _Index(BaseModel):
    """avventure.yaml: the folders of the adventures, in the order of the menu."""

    model_config = ConfigDict(extra="forbid")

    adventures: list[Id] = Field(min_length=1)


def _adventure_ids(root: Path) -> list[str]:
    path = root / INDEX_FILE
    if not path.is_file():
        raise WorldError([f"{INDEX_FILE}: not found in {root}"])
    try:
        index = _Index.model_validate(_read_yaml(path))
    except yaml.YAMLError as exc:
        raise WorldError([_describe_yaml_error(path, exc)]) from None
    except ValidationError as exc:
        raise WorldError([f"{INDEX_FILE}: {_describe_validation_error(err)}" for err in exc.errors()]) from None
    repeated = sorted({adventure_id for adventure_id in index.adventures if index.adventures.count(adventure_id) > 1})
    if repeated:
        raise WorldError([f"{INDEX_FILE}: '{adventure_id}' is listed twice" for adventure_id in repeated])
    return index.adventures


def parse_world(data: Any) -> World:
    """Structural validation (Pydantic) followed by the cross-reference checks."""
    try:
        world = World.model_validate(data)
    except ValidationError as exc:
        raise WorldError([_describe_validation_error(err) for err in exc.errors()]) from None
    problems = find_problems(world)
    if problems:
        raise WorldError(problems)
    return world


def _describe_validation_error(error: Any) -> str:
    path = ".".join(str(part) for part in error["loc"])
    return f"{path}: {error['msg']}" if path else error["msg"]


def _describe_yaml_error(path: Path, exc: yaml.YAMLError) -> str:
    if isinstance(exc, yaml.MarkedYAMLError) and exc.problem_mark is not None:
        details = ", ".join(part for part in (exc.context, exc.problem) if part)
        return f"{path.name}, line {exc.problem_mark.line + 1}: {details}"
    return f"{path.name}: {exc}"


def _read_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return yaml.load(stream, Loader=_StrictLoader)


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate keys and keys that aren't text."""


def _construct_strict_mapping(loader: _StrictLoader, node: yaml.MappingNode) -> dict:
    loader.flatten_mapping(node)
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(
                None,
                None,
                f"key {key!r} is not text: quote it (YAML reads on/off/yes/no as booleans)",
                key_node.start_mark,
            )
        if key in mapping:
            raise yaml.constructor.ConstructorError(None, None, f"duplicate key '{key}'", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_strict_mapping)
