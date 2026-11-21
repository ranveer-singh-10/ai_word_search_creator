"""FastAPI app: POST /api/puzzle, plus the web page served from web/."""
import logging
import time
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import DEFAULT_MODEL, GRID_SIZE, WORD_COUNT, PRICE_PER_MILLION, WEB_DIR
from .directions import DIRECTIONS, ALLOWED_DIRECTIONS
from .dynamic import generate_dynamic_wordsearch
from .generate import generate_populated_wordsearch, UnsuitableCategoryError
from .grid import word_fits_from
from .paths import path_spells

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="AI Word Search Creator")


def puzzle_cost(usage, model=DEFAULT_MODEL):
    """Cost in US dollars of one Claude call, from its token usage."""
    input_price, output_price = PRICE_PER_MILLION[model]
    return (usage.input_tokens * input_price + usage.output_tokens * output_price) / 1_000_000


def generation_stats(usage, started):
    """Generation stats for one Claude call, logged and shown on the page."""
    stats = {
        "model": DEFAULT_MODEL,
        "seconds": round(time.perf_counter() - started, 2),
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": puzzle_cost(usage),
    }
    logger.info("Puzzle stats: %s", stats)
    return stats


def error_response(status_code, detail, usage, started):
    """An error response that also carries the cost when Claude was called (and so billed)."""
    if usage is None:
        raise HTTPException(status_code=status_code, detail=detail)
    return JSONResponse(status_code=status_code,
                        content={"detail": detail, "stats": generation_stats(usage, started)})


def find_word(grid, word, directions):
    """Return the [row, col] start and end cells of word in grid, or None if it isn't there."""
    for row in range(len(grid)):
        for col in range(len(grid[0])):
            for row_step, col_step in directions:
                if word_fits_from(grid, word, (row, col), (row_step, col_step)):
                    last = len(word) - 1
                    return {"start": [row, col], "end": [row + row_step * last, col + col_step * last]}
    return None


def straight_placements(grid, items, difficulty):
    """Locate each straight-line word in the finished grid; words that can't be found are dropped."""
    directions = [DIRECTIONS[d] for d in ALLOWED_DIRECTIONS[difficulty]]
    placed = []
    for item in items:
        placement = find_word(grid, item["word"], directions)
        if placement:
            (r0, c0), (r1, c1) = placement["start"], placement["end"]
            last = len(item["word"]) - 1
            step_r, step_c = (r1 - r0) // last, (c1 - c0) // last
            path = [[r0 + step_r * i, c0 + step_c * i] for i in range(last + 1)]
            placed.append({**item, **placement, "path": path})
    return placed


def dynamic_placements(grid, items):
    """Keep dynamic words whose recorded path still spells them in the finished grid."""
    return [
        {**item, "start": item["path"][0], "end": item["path"][-1]}
        for item in items
        if path_spells(grid, item["word"], item["path"])
    ]


class PuzzleRequest(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    dynamic: bool = False


@app.post("/api/puzzle")
def create_puzzle(req: PuzzleRequest):
    difficulty = req.difficulty
    build_puzzle = generate_dynamic_wordsearch if req.dynamic else generate_populated_wordsearch

    # Ask Claude for words, place them and fill the grid.
    started = time.perf_counter()
    try:
        result = build_puzzle(req.category, GRID_SIZE[difficulty], difficulty, WORD_COUNT[difficulty])
    # Errors raised after Claude replied carry its usage, so their cost is still reported.
    except UnsuitableCategoryError as err:
        logger.info("Rejected unsuitable category: %r", req.category)
        return error_response(400, "That category isn't suitable for a word search. Please choose another.",
                              getattr(err, "usage", None), started)
    except Exception as err:
        logger.exception("Puzzle generation failed")
        return error_response(502, "Couldn't generate the puzzle. Please try again.",
                              getattr(err, "usage", None), started)

    stats = generation_stats(result["llm_response"]["usage"], started)

    # Only return words that really made it into the grid, so the puzzle is always solvable.
    # Each word carries its start and end cells and the full path of cells between them.
    grid = result["grid"]
    if req.dynamic:
        words = dynamic_placements(grid, result["words"])
    else:
        words = straight_placements(grid, result["words"], difficulty)
    if not words:
        return JSONResponse(status_code=500, content={
            "detail": "Couldn't fit the words into the grid. Please try again.", "stats": stats,
        })

    return {"grid": grid, "words": words, "stats": stats}


# Serves the web page. Must come after the API routes, because "/" matches everything.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")