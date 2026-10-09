"""Blend scores on fixed comparable ranges, with validation-selected weight."""

import numpy as np
from numpy.typing import NDArray


def blend_scores(
    collaborative: NDArray[np.float64], content: NDArray[np.float64], alpha: float
) -> NDArray[np.float64]:
    if not 0 <= alpha <= 1:
        raise ValueError("Hybrid weight must be between zero and one.")
    collaborative = (np.clip(collaborative, 1, 5) - 1) / 4
    content = (np.clip(content, -1, 1) + 1) / 2
    return alpha * collaborative + (1 - alpha) * content
