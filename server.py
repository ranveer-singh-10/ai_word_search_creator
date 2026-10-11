import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from wordsearch.generate import generate_populated_wordsearch
from wordsearch.grid import check_word_in_grid
from wordsearch.directions import DIRECTIONS, ALLOWED_DIRECTIONS

logger = logging.getLogger("uvicorn.error")

BASE_DIR = Path(__file__).resolve().parent

# Grid size and word count per difficulty. Tune these as you play-test.
GRID_SIZE = {"easy": 8, "medium": 10, "hard": 12}
WORD_COUNT = {"easy": 8, "medium": 10, "hard": 12}

app = FastAPI()


class PuzzleRequest(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    dynamic: bool = False


@app.post("/api/puzzle")
def create_puzzle(req: PuzzleRequest):
    if req.dynamic:
        raise HTTPException(status_code=501, detail="Dynamic mode isn't available yet.")

    difficulty = req.difficulty

    # Ask Claude for words, place them and fill the grid.
    try:
        result = generate_populated_wordsearch(
            req.category, GRID_SIZE[difficulty], difficulty, WORD_COUNT[difficulty]
        )
    except Exception:
        logger.exception("Puzzle generation failed")
        raise HTTPException(status_code=502, detail="Couldn't generate the puzzle. Please try again.")

    # Log token usage on the server (useful for cost tracking; not sent to the browser).
    usage = result["llm_response"]["usage"]
    logger.info("Tokens used: %s in, %s out", usage.input_tokens, usage.output_tokens)

    # Only return words that really made it into the grid, so the puzzle is always solvable.
    grid = result["grid"]
    directions = [DIRECTIONS[d] for d in ALLOWED_DIRECTIONS[difficulty]]
    words = [
        item for item in result["llm_response"]["words"]
        if check_word_in_grid(grid, item["word"], directions)
    ]
    if not words:
        raise HTTPException(status_code=500, detail="Couldn't fit the words into the grid. Please try again.")

    return {"grid": grid, "words": words}


# Serves the web page. Must come after the API routes, because "/" matches everything.
app.mount("/", StaticFiles(directory=BASE_DIR / "web", html=True), name="web")