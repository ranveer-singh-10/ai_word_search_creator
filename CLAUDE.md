# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project rules

- Never put the API key or any Claude calls in the front end; the page only talks to `/api/puzzle`.
- Don't change `wordsearch/generate.py` or `wordsearch/grid.py` without asking, and explain any change.
- Keep the front end as a single `web/index.html` with HTML, CSS and JavaScript.
- Use UK English.
- Puzzles are for children. Never weaken the content rule in `generate_words`' system prompt (no racist, derogatory, sexual or other content harmful to children), and keep unsuitable categories rejected with a 400 via `UnsuitableCategoryError`.

## Commands

Windows / PowerShell, using the project virtualenv in `.venv`.

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn server:app --reload               # serves the page at http://127.0.0.1:8000 and POST /api/puzzle
python check_api.py                       # quick check that the Anthropic API key works
pytest                                    # tests live in tests/ (pythonpath and testpaths set in pyproject.toml)
pytest tests/test_api.py::test_name       # run a single test
```

`ANTHROPIC_API_KEY` is read from `.env` (git-ignored) via `python-dotenv`. `requirements.txt` is a UTF-16 `pip freeze` snapshot; `pyproject.toml` is the source of truth for dependencies.

## Architecture

Claude only chooses the words; all grid placement is plain Python.

1. `web/index.html` posts `{category, difficulty, dynamic}` to `/api/puzzle` (`server.py`). `dynamic=true` currently returns 501.
2. `server.py` maps difficulty to grid size and word count (`GRID_SIZE`, `WORD_COUNT`) and calls `generate_populated_wordsearch` in `wordsearch/generate.py`.
3. `generate.py` asks Claude (`DEFAULT_MODEL`, Haiku) for JSON `{"words": [{"word", "description"}]}` using structured outputs (`WORDS_SCHEMA`), validates the words (A–Z only, length fits the grid, no duplicates), places them with `grid.py`, then fills the remaining cells.
4. `grid.py` places each word at a random start/direction, allowing overlaps only where letters match. Unplaced cells are `"."` until `fill_empty_squares`; on hard, filler is biased towards letters from the hidden words (`HARD_BIAS`) to create decoys.
5. `wordsearch/directions.py` defines the eight `(row_step, col_step)` directions and which ones each difficulty allows (easy: right/down; medium: adds two diagonals; hard: all eight).
6. Back in `server.py`, `find_word` locates each validated word (`result["words"]`) in the finished grid, so only words that are actually findable are returned, each with `start`/`end` `[row, col]` cells. The page uses these to check the player's click-and-drag selection (either end first). Placement can silently fail, so this filter is what guarantees the puzzle is solvable. The response also carries `stats` (generation time, input/output tokens, cost in US dollars from `PRICE_PER_MILLION`), which the page shows; update `PRICE_PER_MILLION` if `DEFAULT_MODEL` changes.

The Anthropic client is created at import time in `generate.py`, so importing `server` or `wordsearch.generate` needs the API key present; tests should mock `wordsearch.generate.client` (or `generate_words`) rather than call the real API.

`server.py` mounts `web/` as static files at `/` **after** the API routes; new API routes must be declared above that mount or they will be shadowed.

`wordsearch/sample_grids.py` holds hand-made 10×10 grids for experimenting; `notebooks/word_generation.ipynb` is for prompt experiments.
