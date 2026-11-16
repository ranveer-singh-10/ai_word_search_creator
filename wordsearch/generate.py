import json
import logging
import anthropic
import string
from .grid import generate_empty_grid, place_word_in_grid, fill_empty_squares
from .directions import DIRECTIONS, ALLOWED_DIRECTIONS

from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
logger = logging.getLogger(__name__)

ALLOWED_LETTERS = set(string.ascii_uppercase)
DEFAULT_MODEL = "claude-haiku-5-5"


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


# Keep only words that can go in the grid: letters A-Z only, the right length, no duplicates.
# Returns (valid, rejected) so you can see what was dropped and why.
def validate_words(words, max_length, min_length=3):
    valid = []
    rejected = []
    seen = set()

    for item in words:
        word = str(item.get("word", "")).strip().upper()
        description = str(item.get("description", "")).strip()

        if not word or not set(word) <= ALLOWED_LETTERS:
            reason = "not letters A-Z"
        elif len(word) < min_length:
            reason = "too short"
        elif len(word) > max_length:
            reason = "too long for grid"
        elif word in seen:
            reason = "duplicate"
        elif not description:
            reason = "missing description"
        else:
            seen.add(word)
            valid.append({"word": word, "description": description})
            continue

        rejected.append({"word": word, "reason": reason})

    return valid, rejected

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

#result = generate_populated_wordsearch("Cars", 12, "hard", 10)
#print("------------------------------")
#print_grid(result["grid"])
#print("------------------------------")
#print(result["word_list"])
#print("------------------------------")
#print(result)


