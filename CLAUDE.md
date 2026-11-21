# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project rules

- Never put the API key or any Claude calls in the front end; the page only talks to `/api/puzzle`.
- Don't change `src/wordsearch/generate.py` or `src/wordsearch/grid.py` without asking, and explain any change.
- Keep the front end as a single `web/index.html` with HTML, CSS and JavaScript.
- Use UK English.
- Puzzles are for children. Never weaken the content rule in `generate_words`' system prompt (no racist, derogatory, sexual or other content harmful to children), and keep unsuitable categories rejected with a 400 via `UnsuitableCategoryError`.

## Commands

Windows / PowerShell, using the project virtualenv in `.venv`.

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"                   # src layout: the package must be installed (editable) to import
python -m wordsearch --reload             # or `wordsearch`; serves http://127.0.0.1:8000 and POST /api/puzzle
python scripts/check_api.py               # quick check that the Anthropic API key works
pytest                                    # tests live in tests/ (pythonpath and testpaths set in pyproject.toml)
pytest tests/test_api.py::test_name       # run a single test
```

`ANTHROPIC_API_KEY` is read from `.env` (git-ignored; template in `.env.example`) via `python-dotenv`, loaded when `wordsearch.config` is imported. `pyproject.toml` is the only dependency list.

## Layout

`src/wordsearch/`: `api.py` (FastAPI app), `generate.py` (Claude call + straight puzzle assembly), `validate.py` (word filtering), `grid.py` (straight placement/filling), `paths.py` (dynamic placement), `dynamic.py` (dynamic puzzle assembly), `directions.py`, `config.py` (model, `GRID_SIZE`, `WORD_COUNT`, `PRICE_PER_MILLION`, `WEB_DIR`), `__main__.py` (runs uvicorn). `web/` stays at the repo root; `config.WEB_DIR` points at it, so the app is meant to run from a source checkout.

## Architecture

Claude only chooses the words; all grid placement is plain Python.

1. `web/index.html` posts `{category, difficulty, dynamic}` to `/api/puzzle` (`api.py`). `dynamic=true` takes the dynamic path described below.
2. `api.py` maps difficulty to grid size and word count (`config.GRID_SIZE`, `config.WORD_COUNT`) and calls `generate_populated_wordsearch` in `generate.py`.
3. `generate.py` asks Claude (`config.DEFAULT_MODEL`, Haiku) for JSON `{"words": [{"word", "description"}]}` using structured outputs (`WORDS_SCHEMA`), filters the words with `validate.validate_words` (A–Z only, length fits the grid, no duplicates, has a description), places them with `grid.py`, then fills the remaining cells.
4. `grid.py` places each word at a random start/direction, allowing overlaps only where letters match. Unplaced cells are `"."` until `fill_empty_squares`; on hard, filler is biased towards letters from the hidden words (`HARD_BIAS`) to create decoys.
5. `directions.py` defines the eight `(row_step, col_step)` directions and which ones each difficulty allows (easy: right/down; medium: adds two diagonals; hard: all eight).
6. Back in `api.py`, `find_word` locates each validated word (`result["words"]`) in the finished grid, so only words that are actually findable are returned, each with `start`/`end` `[row, col]` cells. The page uses these to check the player's click-and-drag selection (either end first). Placement can silently fail, so this filter is what guarantees the puzzle is solvable. The response also carries `stats` (generation time, input/output tokens, cost in US dollars from `config.PRICE_PER_MILLION`), which the page shows; update `PRICE_PER_MILLION` if `DEFAULT_MODEL` changes.

Dynamic mode: `dynamic.generate_dynamic_wordsearch` gets words the same way (it calls `generate.generate_words` through the module so test patches apply), then `paths.place_word_on_path` places each along a path of touching cells by backtracking search, capped at `MAX_STEPS`. `paths.PATH_RULES` sets turns per difficulty: easy/medium are "bends" (`min_run` 2 moves, max 1/2 turns; words too short to bend stay straight), hard is "snake" (any turn, at least one). The recorded path is returned and re-checked with `path_spells` in `api.dynamic_placements`. In dynamic mode the page lets the player drag (cells register only near their centre) or tap cells one at a time (the selection persists between taps; Escape clears it), and a selection matches only if it equals a word's returned `path`, from either end. Matching on letters alone highlighted stray same-letter cells, so don't go back to that. Its "How words travel" note (`TRAVEL_NOTES` in `index.html`) must be kept in step with `ALLOWED_DIRECTIONS` and `PATH_RULES`.

The Anthropic client is created at import time in `generate.py`, so importing `wordsearch.api` or `wordsearch.generate` needs the API key present. Tests never call the real API: `tests/conftest.py` sets a dummy key and provides `fake_claude` (patches `generate.client.messages.create`; set the reply with `.reply(payload, stop_reason)`) and `fake_words` (patches `generate.generate_words`; `.returns([...])`) fixtures.

`api.py` mounts `web/` as static files at `/` **after** the API routes; new API routes must be declared above that mount or they will be shadowed.

`notebooks/sample_grids.py` holds hand-made 10×10 grids and `notebooks/word_generation.ipynb` is for prompt experiments; nothing in `src/` imports from `notebooks/`.
