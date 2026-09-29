"""The game in the browser.

    python -m app.main          then open http://localhost:8000

The server keeps no game: the browser holds the state of each adventure (in localStorage) and sends
it with every line, with the id of the adventure; the server checks it against that world, plays the
turn with Game and sends the new state back.
No database, no sessions, and a restart of the server loses nothing.
"""

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

from app.config import LOGS_DIR, Settings, make_client, start_command_log, start_llm_log
from app.engine.engine import Engine, StateError
from app.engine.loader import load_adventures
from app.engine.models import Action, GameState
from app.game import Game
from app.llm.client import LLMClient

PAGE = Path(__file__).resolve().parents[1] / "static" / "index.html"
WORLD_CHANGED = "Il mondo è cambiato dall'ultimo salvataggio: la partita ricomincia."
UNKNOWN_ADVENTURE = "Avventura sconosciuta."
MAX_LINE = 500

_log = logging.getLogger("app.llm")


class Adventure(BaseModel):
    """An entry of the menu."""

    id: str
    title: str
    summary: str


class NewGameRequest(BaseModel):
    adventure: str


class NewGameReply(BaseModel):
    text: str
    state: GameState
    room: str  # name of the current room, for the status line
    title: str  # of the adventure, for the top of the page
    # Set when the LLM can't be used: only simple commands are understood.
    notice: str | None = None


class TurnRequest(BaseModel):
    adventure: str
    line: str = Field(max_length=MAX_LINE)
    # Checked by the engine, not here: a state that doesn't fit restarts the game instead of an error.
    state: Any = None
    # The action asked about in the last reply ("Vuoi…?"), sent back as it came; a broken one is ignored.
    pending: Any = None


class TurnReply(BaseModel):
    text: str
    state: GameState
    room: str
    finished: bool
    # True when the saved state didn't fit the world and a new game started.
    restarted: bool = False
    # The action the game is asking about: the browser sends it back with the next line.
    pending: Action | None = None
    # After a death: the act the game can go on from with «riprendi» ("secondo atto").
    resumable: str | None = None


def create_app(engines: dict[str, Engine], llm: LLMClient | None) -> FastAPI:
    """`engines`: one per adventure, keyed by its id, in the order of the menu."""
    app = FastAPI(title="I.A.vventura", docs_url=None, redoc_url=None)

    @app.get("/", include_in_schema=False)
    def page() -> FileResponse:
        # Checked with the server every time: an old page kept by the browser wouldn't fit the API.
        return FileResponse(PAGE, media_type="text/html", headers={"Cache-Control": "no-cache"})

    @app.get("/api/adventures")
    def adventures() -> list[Adventure]:
        return [
            Adventure(id=adventure_id, title=engine.world.game.title, summary=engine.world.game.summary)
            for adventure_id, engine in engines.items()
        ]

    @app.post("/api/new")
    def new_game(request: NewGameRequest) -> NewGameReply:
        engine = engine_of(request.adventure)
        # Checked at every new game: Ollama may have been started after the server.
        reason = llm.unavailable_reason() if llm is not None else None
        _log.info("--- nuova partita (web): %s ---", request.adventure)
        game = Game(engine, llm, adventure=request.adventure)
        notice = f"{reason} Si gioca con i soli comandi semplici." if reason else None
        return NewGameReply(
            text=game.opening(), state=game.state, room=room_of(game), title=engine.world.game.title, notice=notice
        )

    @app.post("/api/turn")
    def turn(request: TurnRequest) -> TurnReply:
        engine = engine_of(request.adventure)
        try:
            state = engine.restore(request.state)
        except StateError:
            game = Game(engine, llm, adventure=request.adventure)
            text = f"{WORLD_CHANGED}\n\n{game.opening()}"
            return TurnReply(text=text, state=game.state, room=room_of(game), finished=False, restarted=True)
        game = Game(engine, llm, state=state, pending=pending_action(request.pending), adventure=request.adventure)
        text = game.turn(request.line)
        return TurnReply(
            text=text,
            state=game.state,
            room=room_of(game),
            finished=game.finished,
            pending=game.pending,
            resumable=game.resumable,
        )

    def engine_of(adventure: str) -> Engine:
        """The page goes back to the menu on a 404: the adventure was taken out of the index."""
        if adventure not in engines:
            raise HTTPException(status_code=404, detail=UNKNOWN_ADVENTURE)
        return engines[adventure]

    def room_of(game: Game) -> str:
        return game.world.rooms[game.state.current_room].name

    def pending_action(data: Any) -> Action | None:
        try:
            return None if data is None else Action.model_validate(data)
        except ValidationError:
            return None

    return app


def create_app_from_env() -> FastAPI:
    """The real app: settings from the environment, LLM log in logs/llm-web.log."""
    settings = Settings.from_env(default_llm_log=LOGS_DIR / "llm-web.log")
    start_llm_log(settings.llm_log, full=settings.llm_log_full)
    start_command_log(settings.command_log, origin="web")
    engines = {adventure_id: Engine(world) for adventure_id, world in load_adventures().items()}
    return create_app(engines, make_client(settings))


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:create_app_from_env", factory=True, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
