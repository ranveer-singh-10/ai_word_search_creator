"""Clean up the words Claude returns so only ones that fit in the grid are used."""
import string

from .config import MIN_WORD_LENGTH

ALLOWED_LETTERS = set(string.ascii_uppercase)


# Keep only words that can go in the grid: letters A-Z only, the right length, no duplicates.
# Returns (valid, rejected) so you can see what was dropped and why.
def validate_words(words, max_length, min_length=MIN_WORD_LENGTH):
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
