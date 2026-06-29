from __future__ import annotations

KEY_MATRIX = [
    ["a", "e", "i", "o", "u", "y", ".", " "],
    ["m", "n", "l", "r", "w", "h", "'", "-"],
    ["b", "p", "f", "v", "c", "j", "q", "x"],
    ["t", "d", "s", "z", "g", "k", "?", "!"],
    ["0", "1", "2", "3", "4", "5", "6", "7"],
    ["8", "9", "+", "-", "/", "=", "(", ")"],
    [",", ";", ":", "_", "@", "#", "&", "*"],
    ["\b", "\n", "\t", "<", ">", "[", "]", "~"],
]

X_CENTERS = [-0.875, -0.625, -0.375, -0.125, 0.125, 0.375, 0.625, 0.875]
Y_CENTERS = [0.875, 0.625, 0.375, 0.125, -0.125, -0.375, -0.625, -0.875]


def nearest_center_index(value: float, centers: list[float]) -> int:
    return min(range(len(centers)), key=lambda i: abs(float(value) - float(centers[i])))
