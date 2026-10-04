"""
CER/WER computation for OCR quality measurement.

No `jiwer` or similar third-party library is assumed to be installed in the
sandbox venv, so this is a small, dependency-free Levenshtein-distance based
implementation. It is intentionally simple and auditable rather than
feature-complete.

Definitions used here (standard OCR evaluation metrics):

    CER = edit_distance(reference_chars, hypothesis_chars) / len(reference_chars)
    WER = edit_distance(reference_words, hypothesis_words) / len(reference_words)

Both are computed on whitespace-normalized text (leading/trailing whitespace
stripped, internal whitespace runs collapsed to a single space) so that layout
differences (e.g. extra blank lines) do not dominate the score. Word order
still matters for WER because it is based on sequence edit distance.

A score of 0.0 is a perfect match. Scores can exceed 1.0 for pathological
cases (garbage output much longer than the reference).
"""
from __future__ import annotations

import dataclasses
import re


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _levenshtein(a: list, b: list) -> int:
    """Classic O(len(a) * len(b)) edit distance over arbitrary sequences
    (characters or words)."""
    if a == b:
        return 0
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)

    prev_row = list(range(len(b) + 1))
    for i, item_a in enumerate(a, start=1):
        curr_row = [i] + [0] * len(b)
        for j, item_b in enumerate(b, start=1):
            cost = 0 if item_a == item_b else 1
            curr_row[j] = min(
                prev_row[j] + 1,       # deletion
                curr_row[j - 1] + 1,   # insertion
                prev_row[j - 1] + cost,  # substitution
            )
        prev_row = curr_row
    return prev_row[-1]


@dataclasses.dataclass
class OcrQualityScore:
    reference: str
    hypothesis: str
    cer: float
    wer: float
    char_edit_distance: int
    word_edit_distance: int
    reference_char_count: int
    reference_word_count: int


def compute_cer_wer(reference: str, hypothesis: str) -> OcrQualityScore:
    ref_norm = _collapse_whitespace(reference)
    hyp_norm = _collapse_whitespace(hypothesis)

    ref_chars = list(ref_norm)
    hyp_chars = list(hyp_norm)
    char_dist = _levenshtein(ref_chars, hyp_chars)
    cer = char_dist / len(ref_chars) if ref_chars else float("nan")

    ref_words = ref_norm.split(" ") if ref_norm else []
    hyp_words = hyp_norm.split(" ") if hyp_norm else []
    word_dist = _levenshtein(ref_words, hyp_words)
    wer = word_dist / len(ref_words) if ref_words else float("nan")

    return OcrQualityScore(
        reference=reference,
        hypothesis=hypothesis,
        cer=cer,
        wer=wer,
        char_edit_distance=char_dist,
        word_edit_distance=word_dist,
        reference_char_count=len(ref_chars),
        reference_word_count=len(ref_words),
    )
