from typing import Dict, Type

from rapidfuzz import fuzz
from tqdm import tqdm


class _Singleton(type):
    """A metaclass that creates a Singleton base class when called."""
    _instances: Dict[Type, object] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def clean_overlap(prev_text, next_text, min_overlap=50, similarity=85)-> str:
    prev_text = prev_text.strip()
    next_text = next_text.strip()

    max_len = min(len(prev_text), len(next_text))

    best_size = 0

    for size in tqdm(range(min_overlap, max_len), desc="Procesando texto", unit="int"):
        tail = prev_text[-size:]
        head = next_text[:size]

        score = fuzz.ratio(tail, head)

        if score >= similarity:
            best_size = size

    if best_size > 0:
        print(f"🧹 Overlap RapidFuzz detectado: {best_size} chars")
        return next_text[best_size:].lstrip()

    return next_text
