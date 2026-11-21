"""Build a dynamic mode puzzle: the same Claude word list, placed along bending paths."""
import logging

from . import generate  # used as generate.generate_words so tests can patch it in one place
from .directions import DIRECTIONS, ALLOWED_DIRECTIONS
from .grid import generate_empty_grid, fill_empty_squares
from .paths import PATH_RULES, place_word_on_path
from .validate import validate_words

logger = logging.getLogger(__name__)


def generate_dynamic_wordsearch(category, size, difficulty, word_count):
    """Ask Claude for words, place the valid ones along paths and fill the grid.

    Returns the placed words (each with its "path" of [row, col] cells), the grid
    and the raw llm response. Words that couldn't be placed are left out.
    """
    grid = generate_empty_grid(size)
    directions = [DIRECTIONS[d] for d in ALLOWED_DIRECTIONS[difficulty]]

    result = generate.generate_words(category, difficulty, word_count, max_length=size)
    valid, rejected = validate_words(result["words"], max_length=size)
    if rejected:
        logger.info("Rejected words: %s", rejected)

    placed = []
    for item in valid:
        path = place_word_on_path(grid, item["word"], directions, **PATH_RULES[difficulty])
        if path:
            placed.append({**item, "path": [list(cell) for cell in path]})
        else:
            logger.info("Couldn't place %s", item["word"])

    fill_empty_squares(grid, [item["word"] for item in placed], difficulty)

    return {"words": placed, "grid": grid, "llm_response": result}
