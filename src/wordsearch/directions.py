# Each direction is (row_step, col_step).
DIRECTIONS = {
    "right":      (0, 1),
    "left":       (0, -1),
    "down":       (1, 0),
    "up":         (-1, 0),
    "down_right": (1, 1),
    "down_left":  (1, -1),
    "up_right":   (-1, 1),
    "up_left":    (-1, -1),
}

# Which directions each difficulty allows (from the project brief).
ALLOWED_DIRECTIONS = {
    "easy":   ["right", "down"],
    "medium": ["right", "down", "down_right", "up_right"],
    "hard":   list(DIRECTIONS),
}