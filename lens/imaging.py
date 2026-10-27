import math


def apply_kernel(pixels, kernel, divisor=1.0):
    """Applique un kernel 3x3 sur une image 8x8 (niveaux de gris 0-255)."""
    size = len(pixels)
    result = [[0] * size for _ in range(size)]
    for y in range(size):
        for x in range(size):
            acc = 0.0
            for ky in range(3):
                for kx in range(3):
                    py = max(0, min(size - 1, y + ky - 1))   # bords : pixel le plus proche
                    px = max(0, min(size - 1, x + kx - 1))
                    acc += pixels[py][px] * kernel[ky][kx]
            # floor(x + 0.5) = même arrondi que Math.floor(x + 0.5) en JavaScript
            result[y][x] = max(0, min(255, math.floor(acc / divisor + 0.5)))
    return result