"""Ask Claude for the word list, then build the finished puzzle grid."""
import json
import logging

import anthropic

from .config import DEFAULT_MODEL  # importing config also loads .env
from .directions import DIRECTIONS, ALLOWED_DIRECTIONS
from .grid import generate_empty_grid, place_word_in_grid, fill_empty_squares
from .validate import validate_words

client = anthropic.Anthropic()
logger = logging.getLogger(__name__)


class UnsuitableCategoryError(Exception):
    """The category asks for content that isn't suitable for children."""


# The API guarantees the reply matches this schema, so there is no need to strip code fences.
WORDS_SCHEMA = {
    "type": "object",
    "properties": {
        "category_suitable": {"type": "boolean"},
        "words": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["word", "description"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["category_suitable", "words"],
    "additionalProperties": False,
}

def generate_words(category, difficulty, count=10, max_length=12, model=DEFAULT_MODEL):
    system_prompt = (
        "You generate words for word search puzzles. "
        "Easy difficulty means common words of 3–6 letters, hard means less common words of 7 letters or more, "
        "and medium means a mix of both. "
        "Include a short description for each word.\n\n"
        "The puzzles are played by children, so every word and description must be suitable for a young audience. "
        "Never include racist, sexist, homophobic or otherwise derogatory words or slurs, swear words, "
        "sexual content, or anything cruel, hateful, violent or harmful towards children. "
        "If the category asks for that kind of content, or can only be answered with it, "
        "set category_suitable to false and return an empty word list. Otherwise set category_suitable to true."
    )

    user_prompt = (
        f"Category: {category}\n"
        f"Difficulty: {difficulty}\n"
        f"Give me {count} words of at most {max_length} letters. "
        "Single words only, letters A-Z, no spaces or hyphens or special characters."
    )

    response = client.messages.create(
        model=model,
        max_tokens=4000,                       # Haiku 5.5 thinks by default, so leave room beyond the JSON
        output_config={
            "effort": "low",                   # a word list doesn't need deep reasoning
            "format": {"type": "json_schema", "schema": WORDS_SCHEMA},
        },
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    try:
        if response.stop_reason == "refusal":
            raise UnsuitableCategoryError(category)
        if response.stop_reason != "end_turn":
            raise RuntimeError(f"Word generation stopped early: {response.stop_reason}")

        text = next(block.text for block in response.content if block.type == "text")
        data = json.loads(text)
        if not data["category_suitable"]:
            raise UnsuitableCategoryError(category)
    except Exception as err:
        # The call is billed even when its reply is rejected, so let callers report the cost.
        err.usage = response.usage
        raise
    return {"words": data["words"], "usage": response.usage, "stop_reason": response.stop_reason}


# Generate the word list, place the valid words and fill the grid.
# Returns the validated words (with descriptions), the grid and the raw llm response.
def generate_populated_wordsearch(category, size, difficulty, word_count):
    grid = generate_empty_grid(size)
    directions = [DIRECTIONS[d] for d in ALLOWED_DIRECTIONS[difficulty]]

    result = generate_words(category, difficulty, word_count, max_length=size)
    valid, rejected = validate_words(result["words"], max_length=size)
    if rejected:
        logger.info("Rejected words: %s", rejected)

    word_list = [item["word"] for item in valid]
    for word in word_list:
        place_word_in_grid(grid, word, directions)

    fill_empty_squares(grid, word_list, difficulty)

    return {"words": valid, "word_list": word_list, "grid": grid, "llm_response": result}
