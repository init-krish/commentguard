"""
CommentGuard — Text Preprocessing & Anti-Evasion Module
───────────────────────────────────────────────────────
Normalizes adversarial text before classification:
  - Leetspeak decoding (h4t3 → hate)
  - Unicode confusable normalization
  - Zero-width character removal
  - Repeated character collapsing (haaate → hate)
  - Whitespace normalization
"""

import re
import unicodedata

# ── Leetspeak mapping ─────────────────────────────────────────────────────────
LEET_MAP = {
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "6": "g", "7": "t", "8": "b", "9": "g",
    "@": "a", "$": "s", "!": "i", "+": "t",
    "(": "c", "|": "l", "€": "e", "£": "l",
}

# ── Unicode confusables (common substitutions) ───────────────────────────────
CONFUSABLES = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y",  # Cyrillic
    "і": "i", "ⅰ": "i", "ⅼ": "l", "ⅿ": "m",                      # Roman numerals
    "ℎ": "h", "ℯ": "e", "ℴ": "o",                                  # Math symbols
    "🅰": "a", "🅱": "b",                                             # Emoji letters
    "ᴀ": "a", "ʙ": "b", "ᴄ": "c", "ᴅ": "d", "ᴇ": "e",            # Small caps
    "ꜰ": "f", "ɢ": "g", "ʜ": "h", "ɪ": "i", "ᴊ": "j",
    "ᴋ": "k", "ʟ": "l", "ᴍ": "m", "ɴ": "n", "ᴏ": "o",
    "ᴘ": "p", "ʀ": "r", "ꜱ": "s", "ᴛ": "t", "ᴜ": "u",
    "ᴠ": "v", "ᴡ": "w", "ʏ": "y", "ᴢ": "z",
}

# ── Zero-width and invisible characters ──────────────────────────────────────
INVISIBLE_RE = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\u2064"
    r"\ufeff\u00ad\u034f\u061c\u115f\u1160\u17b4\u17b5"
    r"\u180e\u2000-\u200f\u202a-\u202f\u205f-\u206f]"
)

# ── Repeated character pattern (3+ same char → 2) ───────────────────────────
REPEAT_RE = re.compile(r"(.)\1{2,}")

# ── Separator characters inserted between letters (k.i.l.l → kill) ──────────
SEPARATOR_RE = re.compile(r"(?<=\w)[.\-_*~|/\\]{1,2}(?=\w)")


def preprocess(text: str) -> str:
    """
    Clean and normalize text for toxicity classification.
    Strips adversarial evasion techniques while preserving meaning.
    """
    if not text:
        return ""

    # 1. Remove zero-width / invisible characters
    text = INVISIBLE_RE.sub("", text)

    # 2. Unicode NFKD normalization (ℍ → H, ① → 1, etc.)
    text = unicodedata.normalize("NFKD", text)

    # 3. Replace Unicode confusables (Cyrillic а → Latin a)
    text = "".join(CONFUSABLES.get(c, c) for c in text)

    # 4. Lowercase
    text = text.lower()

    # 5. Decode leetspeak (h4t3 → hate)
    text = "".join(LEET_MAP.get(c, c) for c in text)

    # 6. Remove separator evasion (k.i.l.l → kill, f-u-c-k → fuck)
    text = SEPARATOR_RE.sub("", text)

    # 7. Collapse repeated characters (haaaaaate → haate → close enough)
    text = REPEAT_RE.sub(r"\1\1", text)

    # 8. Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text
