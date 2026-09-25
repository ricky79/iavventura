"""The game in the browser.

    python -m app.main          then open http://localhost:8000

The server keeps no game: the browser holds the state (in localStorage) and sends it with every
line; the server checks it against the world, plays the turn with Game and sends the new state back.
No database, no sessions, and a restart of the server loses nothing.
"""

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import LOGS_DIR, Settings, make_client, start_llm_log
from app.engine.engine import Engine, StateError
from app.engine.loader import load_world
from app.engine.models import GameState
from app.game import Game
from app.llm.client import LLMClient

PAGE = Path(__file__).resolve().parents[1] / "static" / "index.html"
WORLD_CHANGED = "Il mondo è cambiato dall'ultimo salvataggio: la partita ricomincia."
MAX_LINE = 500

_log = logging.getLogger("app.llm")


class NewGameReply(BaseModel):
    text: str
    state: GameState
    room: str  # name of the current room, for the status line
    # Set when the LLM can't be used: only simple commands are understood.
    notice: str | None = None


class TurnRequest(BaseModel):
    line: str = Field(max_length=MAX_LINE)
    # Checked by the engine, not here: a state that doesn't fit restarts the game instead of an error.
    state: Any = None


class TurnReply(BaseModel):
    text: str
    state: GameState
    room: str
    finished: bool
    # True when the saved state didn't fit the world and a new game started.
    restarted: bool = False


def create_app(engine: Engine, llm: LLMClient | None) -> FastAPI:
    app = FastAPI(title="Avventura nel castello", docs_url=None, redoc_url=None)

    @app.get("/", include_in_schema=False)
    def page() -> FileResponse:
        return FileResponse(PAGE, media_type="text/html")

    @app.post("/api/new")
    def new_game() -> NewGameReply:
        # Checked at every new game: Ollama may have been started after the server.
        reason = llm.unavailable_reason() if llm is not None else None
        _log.info("--- nuova partita (web) ---")
        game = Game(engine, llm)
        notice = f"{reason} Si gioca con i soli comandi semplici." if reason else None
        return NewGameReply(text=game.opening(), state=game.state, room=room_of(game), notice=notice)

    @app.post("/api/turn")
    def turn(request: TurnRequest) -> TurnReply:
        try:
            state = engine.restore(request.state)
        except StateError:
            game = Game(engine, llm)
            text = f"{WORLD_CHANGED}\n\n{game.opening()}"
            return TurnReply(text=text, state=game.state, room=room_of(game), finished=False, restarted=True)
        game = Game(engine, llm, state=state)
        text = game.turn(request.line)
        return TurnReply(text=text, state=game.state, room=room_of(game), finished=game.finished)

    def room_of(game: Game) -> str:
        return engine.world.rooms[game.state.current_room].name

    return app


def create_app_from_env() -> FastAPI:
    """The real app: settings from the environment, LLM log in logs/llm-web.log."""
    settings = Settings.from_env(default_llm_log=LOGS_DIR / "llm-web.log")
    start_llm_log(settings.llm_log)
    return create_app(Engine(load_world()), make_client(settings))


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:create_app_from_env", factory=True, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
