"""Dynamic mode placement: words follow a path of touching cells that changes direction.

Easy and medium use "bends": straight sections joined by one or two turns.
Hard uses "snake": the word may turn at every letter.
"""
import random

from .grid import EMPTY

# How words travel in dynamic mode, per difficulty. Directions come from ALLOWED_DIRECTIONS.
# A run is a straight section, counted in moves: a run of 2 moves covers 3 letters,
# with the corner letter shared by the runs either side of a turn.
PATH_RULES = {
    "easy":   {"max_turns": 1, "min_run": 2},      # bends
    "medium": {"max_turns": 2, "min_run": 2},      # bends
    "hard":   {"max_turns": None, "min_run": 1},   # snake: no limit on turns
}

# Search steps allowed per word, so a crowded grid can't stall the request.
MAX_STEPS = 5000


def min_turns_for(word, min_run):
    """Words long enough to bend must bend at least once; shorter ones stay straight."""
    return 1 if len(word) - 1 >= 2 * min_run else 0


def place_word_on_path(grid, word, directions, max_turns=None, min_run=1, max_steps=MAX_STEPS):
    """Write word along a path of touching, unrepeated cells, moving only in the given directions.

    Cells must be empty or already hold the same letter (so words can share letters).
    Returns the path as a list of (row, col), or None if the word couldn't be placed,
    in which case the grid is left unchanged.
    """
    rows, cols = len(grid), len(grid[0])
    min_turns = min_turns_for(word, min_run)
    steps_left = max_steps

    def fits(cell, letter):
        row, col = cell
        return 0 <= row < rows and 0 <= col < cols and grid[row][col] in (EMPTY, letter)

    # Depth-first search with backtracking, trying directions in random order.
    def extend(path, direction, run, turns):
        nonlocal steps_left
        if len(path) == len(word):
            complete = turns >= min_turns and (turns == 0 or run >= min_run)
            return path if complete else None

        steps_left -= 1
        if steps_left < 0:
            return None

        row, col = path[-1]
        options = list(directions)
        random.shuffle(options)
        for step in options:
            turning = direction is not None and step != direction
            if turning and (run < min_run or (max_turns is not None and turns >= max_turns)):
                continue
            cell = (row + step[0], col + step[1])
            if cell in path or not fits(cell, word[len(path)]):
                continue
            found = extend(path + [cell], step, 1 if turning else run + 1, turns + turning)
            if found:
                return found
        return None

    starts = [(row, col) for row in range(rows) for col in range(cols)]
    random.shuffle(starts)
    for start in starts:
        if steps_left < 0:
            break
        if fits(start, word[0]):
            path = extend([start], None, 0, 0)
            if path:
                for (row, col), letter in zip(path, word):
                    grid[row][col] = letter
                return path
    return None


def path_spells(grid, word, path):
    """True if path is a chain of touching, unrepeated cells inside the grid that spells word."""
    cells = [tuple(cell) for cell in path]
    if len(cells) != len(word) or len(set(cells)) != len(cells):
        return False
    for i, (row, col) in enumerate(cells):
        if not (0 <= row < len(grid) and 0 <= col < len(grid[0])) or grid[row][col] != word[i]:
            return False
        if i and max(abs(row - cells[i - 1][0]), abs(col - cells[i - 1][1])) != 1:
            return False
    return True
