#!/usr/bin/env python3
"""Rebuild goethe_a1-b1.tsv from a checkout of the upstream Goethe word lists.

Steps to regenerate:
  1. Clone the source data:
       git clone https://github.com/ilkermeliksitki/goethe-institute-wordlist /tmp/gw
  2. Download a German frequency list (OpenSubtitles, hermitdave/FrequencyWords):
       curl -sL -o /tmp/de_50k.txt \\
         https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/de/de_50k.txt
  3. Run this script (adjust SRC / FREQ below if you put files elsewhere):
       python build_wordlist.py

It concatenates the per-letter TSVs for A1/A2/B1, strips header rows, assigns
each word to the LOWEST CEFR level it appears at (so levels don't double-count),
and attaches a corpus frequency rank so callers can prioritize common words.
See README.md for column definitions and provenance.
"""

import re
import glob
import os
from collections import Counter

# Local checkout of ilkermeliksitki/goethe-institute-wordlist (must contain a1/ a2/ b1/).
SRC = os.environ.get("GOETHE_SRC", "/tmp/gw")
# hermitdave German frequency list ("word count" per line).
FREQ = os.environ.get("GOETHE_FREQ", "/tmp/de_50k.txt")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "goethe_a1-b1.tsv")
HEADER = ("german word", "german sentence", "english translation")
# freq_rank for words not found in the frequency list — sorts them last.
NO_RANK = 10 ** 7


def base_key(word):
    """Normalize a head word so senses/articles/plurals collapse for dedup."""
    w = word.strip().lower()
    w = re.sub(r"\(\d+\)", "", w)            # drop sense markers like (1)
    w = re.sub(r"^(der|die|das)\s+", "", w)  # drop article
    w = w.split(",")[0]                      # drop plural marker after comma
    w = re.sub(r"\(.*?\)", "", w)            # drop parentheticals e.g. (E-)
    return w.strip()


def load_frequency(path):
    """Return {normalized_word: rank} where rank 1 = most frequent."""
    if not os.path.exists(path):
        print(f"⚠ Frequency list not found at {path}; freq_rank will be blank.")
        return {}
    rank = {}
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            word = line.split(" ", 1)[0].strip().lower()
            # Keep the best (lowest) rank if a normalized form recurs.
            if word and word not in rank:
                rank[word] = i
    return rank


def main():
    freq = load_frequency(FREQ)
    assigned = {}   # base lemma -> level first seen at
    rows = []
    for level in ("a1", "a2", "b1"):
        for fp in sorted(glob.glob(os.path.join(SRC, level, "[a-z].tsv"))):
            with open(fp, encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n")
                    if not line.strip():
                        continue
                    parts = line.split("\t")
                    if len(parts) < 3:
                        continue
                    word, de, en = parts[0].strip(), parts[1].strip(), parts[2].strip()
                    if (word.lower(), de.lower(), en.lower()) == HEADER:
                        continue
                    k = base_key(word)
                    if not k:
                        continue
                    prev = assigned.get(k)
                    if prev is not None and prev != level:
                        continue  # already assigned at a lower level
                    assigned[k] = level
                    rank = freq.get(k, NO_RANK)
                    rows.append((level.upper(), word, de, en, str(rank)))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("level\tword\tgerman\tenglish\tfreq_rank\n")
        for r in rows:
            f.write("\t".join(r) + "\n")

    counts = Counter(r[0] for r in rows)
    ranked = sum(1 for r in rows if int(r[4]) != NO_RANK)
    print(f"Wrote {len(rows)} entries -> {OUT}")
    print("Per level:", dict(sorted(counts.items())))
    print(f"With frequency rank: {ranked}/{len(rows)}")


if __name__ == "__main__":
    main()
