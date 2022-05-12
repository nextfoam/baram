from pathlib import Path


def file(path: str) -> Path:
    return Path(__file__).parent / path
