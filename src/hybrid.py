"""Blend scores on fixed comparable ranges, with validation-selected weight."""

import numpy as np


def blend_scores(collaborative, content, alpha):
    if not 0 <= alpha <= 1:
        raise ValueError("Hybrid weight must be between zero and one.")
    collaborative = (np.clip(collaborative, 1, 5) - 1) / 4
    content = (np.clip(content, -1, 1) + 1) / 2
    return alpha * collaborative + (1 - alpha) * content
