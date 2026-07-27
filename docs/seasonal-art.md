# Making a new seasonal Billie

Every seasonal Billie is the *same* platypus in a different costume: same pose,
same disdain, same thick hand-drawn outlines — just wearing the occasion. The
trick to keeping them consistent is to **edit the canonical art** rather than
generate a new platypus from scratch, then convert the result to the half-block
ANSI art the CLI actually renders.

Each season ships two files in `src/billie/static/`:

- `billie-<season>.png` — high-res art, shown in Kitty-graphics-capable
  terminals (Kitty, Ghostty, WezTerm).
- `billie-<season>.txt` — 256-color half-block ANSI art, the fallback everywhere
  else. This is the one most people see.

## Prerequisites

- [`imagemage`](https://github.com/quinnypig/imagemage) — the image CLI:
  ```bash
  brew tap quinnypig/imagemage && brew install imagemage
  export OPENAI_API_KEY="..."   # imagemage defaults to OpenAI gpt-image-2
  ```
- [`uv`](https://docs.astral.sh/uv/) — runs the two Python helpers in `tools/`.
  Pillow is pulled in on the fly with `uv run --with pillow`; it is deliberately
  **not** a project dependency (the shipped package never touches it).

## The pipeline

Working in a scratch directory, with `<season>` as the new name:

### 1. Edit the base art into a costume

```bash
imagemage edit src/billie/static/billie.png \
  "Add <the costume/props>. Keep the EXACT same grumpy, disdainful platypus: \
   same yellow-green body, blue duck bill, angry furrowed brow, orange webbed \
   feet, blue crosshatched tail, same seated arms-crossed pose, same flat \
   hand-drawn cartoon style with thick dark outlines. Fully transparent \
   background, no scenery, no floor." \
  -o /tmp/billie-<season>.png --force
```

The "keep the EXACT same platypus" clause is what holds the family together —
lean on it. Props read best when Billie is visibly unimpressed by them.

### 2. Reclaim real transparency, crop, and right-size

gpt-image renders "transparent" as an opaque light checkerboard, so the edit
comes back with no real alpha. `tools/debg.py` flood-fills that light
background inward from the border to true transparency — detached, colorful
elements (confetti) and interior light details (a candle flame) survive because
the fill only spreads across background-colored pixels. It then crops to content
and caps the longest side (1500px keeps it in family with its siblings):

```bash
uv run --with pillow python tools/debg.py \
  /tmp/billie-<season>.png src/billie/static/billie-<season>.png 1500
```

If Billie ends up with a light halo or, worse, see-through, nudge `SPREAD_MAX`
/ `LIGHT_MIN` at the top of `debg.py`. Or just re-prompt step 1 asking for a
**flat solid white** background, which keys even more cleanly than a
checkerboard.

### 3. Convert to half-block ANSI

`tools/png_to_ansi.py` renders the PNG as `▄`/`▀` half-blocks — foreground is
the bottom pixel, background the top — at 60 columns (the house width). Fully
transparent cells become spaces, so there is no dark-mode halo on the edges:

```bash
uv run --with pillow python tools/png_to_ansi.py \
  src/billie/static/billie-<season>.png src/billie/static/billie-<season>.txt 60
```

Sanity-check it in a real terminal:

```bash
cat src/billie/static/billie-<season>.txt
```

## Wire the season into the code

1. **`src/billie/seasons.py`** — add an entry to `SEASONS`. Calendar seasons use
   a `dates` tuple `((start_month, start_day), (end_month, end_day))` (inclusive;
   a single day repeats it, e.g. `((7, 28), (7, 28))`). Give it `"pic":
   "billie-<season>.txt"` and a `words` pool — the seasonal words *replace* the
   default pool, so make them all count.
2. **`src/billie/core.py`** — add `"<season>"` to `season_choices` so
   `--season <season>` works.
3. **`tests/test_seasons.py`** — bump the season-count test, add the name to the
   expected set, and add detection cases (on the day, and the days on either
   side).

Then:

```bash
uv run pytest
billie -s <season>      # eyeball it
```

## Notes

- First calendar match in `SEASONS` order wins; `billing` (day-of-month) is
  checked last. List a precise single-day holiday **above** any wider or movable
  season it can overlap — in particular above the dynamic Easter window, which
  drifts across late March and early April — so the specific day beats the broad
  one. (This is why `backup` on Mar 31 and `aprilfools` on Apr 1 sit before
  `easter`.)
- Kitty rendering derives the PNG name from the `.txt` name, so the two files
  must share a stem (`billie-<season>`).
- Half-block art is twice as tall in pixels as it is in character rows, so a
  ~60×34 `.txt` needs a terminal at least 34 rows tall; the CLI bows out with a
  polite complaint if the terminal is too small.
