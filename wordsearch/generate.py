import json
import anthropic
import string
from .grid import generate_empty_grid, place_word_in_grid, fill_empty_squares
from .directions import DIRECTIONS, ALLOWED_DIRECTIONS

from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

ALLOWED_LETTERS = set(string.ascii_uppercase)
DEFAULT_MODEL = "claude-haiku-5-5"

def generate_words(category, difficulty, count=10, model = DEFAULT_MODEL):
    system_prompt = (
        "You generate words for word search puzzles. Easy difficulty means common words of 3–6 letters, and hard means less common words of 7–12 letters, medium means a mix of both"
        "Respond with JSON only and include a small description for each word, no other text, in this format: "
        '{"words": [{"word": "COMET", "description": "An icy body that develops a tail near the Sun"},    {"word": "ORBIT", "description": "The curved path of one object around another"}]}'
    )

    user_prompt = (
        f"Category: {category}\n"
        f"Difficulty: {difficulty}\n"
        f"Give me {count} words. Single words only, letters A-Z, no spaces or hyphens or special characters"
    )

    response = client.messages.create(
        model=model,
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = next(block.text for block in response.content if block.type == "text")
    #print(response.usage)
    return {"words": json.loads(text)["words"], "usage": response.usage}


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

#generate the word list and create the populated grid and return the llm response, grid and word list
def generate_populated_wordsearch(category, size, difficulty, word_count):
    grid = generate_empty_grid(size)
    easy_dirs = [DIRECTIONS[d] for d in ALLOWED_DIRECTIONS[difficulty]]

    result = generate_words(category, difficulty, word_count)

    result = generate_words(category, difficulty, word_count)
    valid, rejected = validate_words(result["words"], max_length=size)
    word_list = [item["word"] for item in valid]

    for word in result["words"]:

        word_list.append(word["word"])

    for word in word_list:
        placed = place_word_in_grid(grid, word, easy_dirs)

    fill_empty_squares(grid, word_list, difficulty)

    return {"word_list": word_list, "grid": grid, "llm_response": result}

#result = generate_populated_wordsearch("Cars", 12, "hard", 10)
#print("------------------------------")
#print_grid(result["grid"])
#print("------------------------------")
#print(result["word_list"])
#print("------------------------------")
#print(result)


