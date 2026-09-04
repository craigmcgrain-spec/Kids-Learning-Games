from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache


# Common English graphemes are kept together so young readers see useful
# sound-sized chunks rather than arbitrary letters.
_GRAPHEMES = sorted(
    {
        "ough", "augh", "eigh", "tion", "sion", "tch", "dge", "igh", "air",
        "ear", "ure", "sh", "ch", "th", "wh", "ph", "ck", "ng", "qu", "ee",
        "ea", "oa", "oo", "ou", "ow", "oi", "oy", "ai", "ay", "er", "ir",
        "ur", "ar", "or", "aw", "au", "ew", "ue",
    },
    key=len,
    reverse=True,
)
_PATTERN = re.compile("|".join(map(re.escape, _GRAPHEMES)) + "|[a-z]", re.I)

_MULTI_PHONEMES = (
    "tS", "dZ", "aI", "eI", "OI", "aU", "oU", "I@", "e@", "U@",
)
_PHONEME_LABELS = {
    "p": "p",
    "b": "b",
    "t": "t",
    "d": "d",
    "k": "k",
    "g": "g",
    "f": "f",
    "v": "v",
    "T": "th",
    "D": "th",
    "s": "s",
    "z": "z",
    "S": "sh",
    "Z": "zh",
    "h": "h",
    "tS": "ch",
    "dZ": "j",
    "m": "m",
    "n": "n",
    "N": "ng",
    "l": "l",
    "L": "l",
    "r": "r",
    "w": "w",
    "j": "y",
    "I": "ih",
    "i:": "ee",
    "E": "eh",
    "a": "a",
    "V": "uh",
    "A:": "ah",
    "O": "aw",
    "O:": "aw",
    "0": "o",
    "U": "oo",
    "u:": "oo",
    "@": "uh",
    "3": "er",
    "3:": "er",
    "eI": "ay",
    "aI": "eye",
    "OI": "oy",
    "aU": "ow",
    "oU": "oh",
    "I@": "ear",
    "e@": "air",
    "U@": "ure",
}


@dataclass(frozen=True, slots=True)
class Phoneme:
    code: str
    label: str


def phoneme_chunks(word: str) -> list[str]:
    """Split a printed word into child-friendly sound/grapheme chunks."""
    clean = word.lower().replace("’", "'").strip(" .'")
    if not clean:
        return []
    chunks = _PATTERN.findall(clean)
    if len(chunks) > 2 and chunks[-1] == "e":
        chunks[-2:] = [chunks[-2] + "e"]
    return chunks


def parse_espeak_phonemes(raw: str) -> list[Phoneme]:
    """Convert eSpeak mnemonic output into individually playable sounds."""
    cleaned = raw.strip().replace("'", "").replace(",", "").replace("#", "").replace(";", "")
    phonemes: list[Phoneme] = []
    index = 0
    while index < len(cleaned):
        code = next(
            (item for item in _MULTI_PHONEMES if cleaned.startswith(item, index)),
            cleaned[index],
        )
        index += len(code)
        if index < len(cleaned) and cleaned[index] in ":2":
            code += cleaned[index]
            index += 1
        base_code = code.removesuffix("2")
        phonemes.append(Phoneme(code, _PHONEME_LABELS.get(base_code, base_code.lower())))
    return phonemes


@lru_cache(maxsize=512)
def phonemes_for_word(word: str) -> list[Phoneme]:
    """Ask eSpeak for the word's pronunciation, falling back to graphemes."""
    try:
        result = subprocess.run(
            ["espeak-ng", "-q", "-x", "-v", "en-us", word],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return [Phoneme("", chunk) for chunk in phoneme_chunks(word)]
    parsed = parse_espeak_phonemes(result.stdout)
    return parsed or [Phoneme("", chunk) for chunk in phoneme_chunks(word)]
