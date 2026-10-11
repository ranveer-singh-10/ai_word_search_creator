import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from wordsearch.generate import generate_populated_wordsearch
from wordsearch.grid import word_fits_from
from wordsearch.directions import DIRECTIONS, ALLOWED_DIRECTIONS

logger = logging.getLogger("uvicorn.error")

BASE_DIR = Path(__file__).resolve().parent

# Grid size and word count per difficulty. Tune these as you play-test.
GRID_SIZE = {"easy": 8, "medium": 10, "hard": 12}
WORD_COUNT = {"easy": 8, "medium": 10, "hard": 12}

app = FastAPI()


def find_word(grid, word, directions):
    """Return the [row, col] start and end cells of word in grid, or None if it isn't there."""
    for row in range(len(grid)):
        for col in range(len(grid[0])):
            for row_step, col_step in directions:
                if word_fits_from(grid, word, (row, col), (row_step, col_step)):
                    last = len(word) - 1
                    return {"start": [row, col], "end": [row + row_step * last, col + col_step * last]}
    return None


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
    # Each word carries its start and end cells so the page can check the player's selection.
    grid = result["grid"]
    directions = [DIRECTIONS[d] for d in ALLOWED_DIRECTIONS[difficulty]]
    words = []
    for item in result["words"]:
        placement = find_word(grid, item["word"], directions)
        if placement:
            words.append({**item, **placement})
    if not words:
        raise HTTPException(status_code=500, detail="Couldn't fit the words into the grid. Please try again.")

    return {"grid": grid, "words": words}


# Serves the web page. Must come after the API routes, because "/" matches everything.
app.mount("/", StaticFiles(directory=BASE_DIR / "web", html=True), name="web")