# Goethe A1–B1 word list

`goethe_a1-b1.tsv` is a merged, deduplicated, CEFR-leveled vocabulary list:
each row is a word, an example German sentence, and its English translation.

Columns (tab-separated, one header row):

| column      | meaning                                                   |
|-------------|-----------------------------------------------------------|
| `level`     | `A1`, `A2`, or `B1` — the *lowest* level the word appears at |
| `word`      | the head word / lemma (with article + plural where given)   |
| `german`    | an example sentence using the word (this is what gets spoken) |
| `english`   | English translation of the example sentence                |
| `freq_rank` | corpus frequency rank (1 = most common); `10000000` = not found in the frequency list, so it sorts last |

Counts: **A1 847, A2 1018, B1 2283** (4148 total). Each word is listed once, at
the lowest level it occurs in — so the A2 rows are words *new* at A2, and B1 rows
are words *new* at B1. Together they form a cumulative A1→B1 progression.

## Provenance & licensing

The vocabulary derives from the official **Goethe-Institut Wortlisten** — the
closest thing to a "source of truth" for CEFR-aligned German, since the CEFR
itself defines competences, not word lists, and each exam board operationalizes
it. Official source PDFs:

- A1: https://www.goethe.de/pro/relaunch/prf/de/A1_SD1_Wortliste_02.pdf
- A2: https://www.goethe.de/pro/relaunch/prf/sr/Goethe-Zertifikat_A2_Wortliste.pdf
- B1: https://www.goethe.de/pro/relaunch/prf/de/Goethe-Zertifikat_B1_Wortliste.pdf

The tabular form (word + example sentence + translation) was sourced from the
community project **ilkermeliksitki/goethe-institute-wordlist**
(https://github.com/ilkermeliksitki/goethe-institute-wordlist), then merged and
leveled by `build_wordlist.py`.

That upstream repo carries **no license**, and the underlying vocabulary is
Goethe-Institut copyrighted material. Treat this file as fine for **personal
language-learning use only** — do not redistribute it as a standalone dataset.
The upstream also warns some words may be missing; cross-check the official PDFs
above when accuracy matters.

### Frequency ranks

`freq_rank` comes from the **hermitdave/FrequencyWords** German list
(https://github.com/hermitdave/FrequencyWords, `content/2018/de/de_50k.txt`),
derived from the OpenSubtitles corpus (CC-BY-SA 4.0) — so ranks reflect
*conversational/spoken* frequency, which suits a learning app. Each Goethe word
is normalized (article/plural/sense markers stripped) and matched against that
list; ~89% match, the rest get the "not found" sentinel. Ranking is a
prioritization aid, not an exact science: OpenSubtitles skews toward dialogue,
and normalization can merge or miss inflected forms.

## Regenerating

`build_wordlist.py` rebuilds `goethe_a1-b1.tsv` from a local checkout of the
upstream repo. See the script header for the expected path.
