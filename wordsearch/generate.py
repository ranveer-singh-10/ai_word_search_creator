import json
import anthropic
from grid import *

from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

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

#generate the word list and create the populated grid and return the llm response, grid and word list
def generate_populated_wordsearch(category, size, difficulty, word_count):
    grid = generate_empty_grid(size)
    easy_dirs = [DIRECTIONS[d] for d in ALLOWED_DIRECTIONS[difficulty]]

    result = generate_words(category, difficulty, word_count)

    word_list = []

    for word in result["words"]:
        word_list.append(word["word"])

    for word in word_list:
        placed = place_word_in_grid(grid, word, easy_dirs)

    fill_empty_squares(grid, word_list, difficulty)

    return {"word_list": word_list, "grid": grid, "llm_response": result}

result = generate_populated_wordsearch("Cars", 12, "hard", 10)
print("------------------------------")
print_grid(result["grid"])
print("------------------------------")
print(result["word_list"])
print("------------------------------")
print(result)


