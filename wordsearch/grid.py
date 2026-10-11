from sample_grids import GRID_1, GRID_2, GRID_3   # whatever names grid.py actually uses
from directions import DIRECTIONS, ALLOWED_DIRECTIONS
import random
import string

EMPTY = "."
# How often hard mode picks filler from the hidden words' letters (0 = never, 1 = always).
HARD_BIAS = 0.5

#generate empty array of the give size. Always square
def generate_empty_grid(size):
    return [[EMPTY for _ in range(size)] for _ in range(size)]

def print_grid(grid):
    for row in grid:
        print(" ".join(row))


def can_place(grid, word, start, direction):
    """True if every letter of word fits from start in direction:
    each cell must be empty or already hold the same letter."""
    position = start
    for i, letter in enumerate(word):
        row, col = position
        if grid[row][col] not in (EMPTY, letter):
            return False
        if i < len(word) - 1:
            position = next_cell(grid, position, direction)
            if position is None:
                return False
    return True


def place_word(grid, word, start, direction):
    """Write word into grid from start in direction. Assumes can_place was True."""
    position = start
    for letter in word:
        row, col = position
        grid[row][col] = letter
        position = next_cell(grid, position, direction)


# Take a word and, starting at a random position that is empty or already holds
# the word's first letter, try to place the word.
# Choose the direction at random too, and try all directions before trying a new start.
def place_word_in_grid(grid, word, directions=None):
    if directions is None:
        directions = list(DIRECTIONS.values())

    starts = [(row, col) for row in range(len(grid)) for col in range(len(grid[0]))]
    random.shuffle(starts)

    for start in starts:
        row, col = start
        if grid[row][col] not in (EMPTY, word[0]):
            continue                       # quick skip: first letter can't go here

        shuffled_directions = list(directions)
        random.shuffle(shuffled_directions)
        for direction in shuffled_directions:
            if can_place(grid, word, start, direction):
                place_word(grid, word, start, direction)
                return True
    return False


# Determine the next cell in any direction.
# Returns None if the next cell would be off the grid.
def next_cell(grid, grid_position, direction):
    row, col = grid_position
    row_step, col_step = direction
    next_row = row + row_step
    next_col = col + col_step
    if 0 <= next_row < len(grid) and 0 <= next_col < len(grid[0]):
        return (next_row, next_col)
    return None

def word_fits_from(grid, word, start, direction):
    """True if word reads from start, stepping in direction, with every letter matching."""
    position = start
    for i, letter in enumerate(word):
        row, col = position
        if grid[row][col] != letter:
            return False
        if i < len(word) - 1:          # only move if there's another letter to check
            position = next_cell(grid, position, direction)
            if position is None:       # ran off the edge before the word finished
                return False
    return True


def check_word_in_grid(grid, word, directions):
    """True if word appears anywhere in grid in any of the given directions."""
    for row in range(len(grid)):
        for col in range(len(grid[0])):
            for direction in directions:
                if word_fits_from(grid, word, (row, col), direction):
                    return True
    return False

# Fill every empty square with a letter.
# Easy/medium: any letter A-Z at random.
# Hard: biased towards letters used in the hidden words, to create decoys.
def fill_empty_squares(grid, words, difficulty):
    word_letters = "".join(words)

    for row in range(len(grid)):
        for col in range(len(grid[0])):
            if grid[row][col] != EMPTY:
                continue                                   # leave placed letters alone

            if difficulty == "hard" and word_letters and random.random() < HARD_BIAS:
                grid[row][col] = random.choice(word_letters)
            else:
                grid[row][col] = random.choice(string.ascii_uppercase)


    return



