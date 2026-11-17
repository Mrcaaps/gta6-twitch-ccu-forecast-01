# Model note — gta6-twitch-ccu-forecast-01

## Entry
`main.py` (Python 3.13, stdlib only). Reads every `*.in` in the input dir,
writes `*.out` with hours 2..24, five quantiles each. Deterministic, ~0.2 s
per run, no network, no wall clock.

## Model
For each comparable with a full release day (24/24 hours, all viewers > 0),
compute its log-ratio curve `r_h = ln(v_h) - ln(v_1)`, h = 2..24. For each
hour, the forecast's five quantiles are the **weighted quantiles** of `r_h`
across comparables, and `q_tau(h) = p1 * exp(quantile_tau(r_h))` where `p1`
is the target's hour-1 print.

Weights (validated by leave-one-out CV, see `loo.py` / `loo-results.txt`):
- Gaussian kernel on log hour-1 size: `exp(-0.5 * ((ln v1_comp - ln p1)/1.0)^2)`.
  Games whose hour 1 was a similar size have similar curve shapes: giants
  (ELDEN RING, Cyberpunk) peaked at hour 1 and decline, small launches ramp.
- x3 bonus for rolling-midnight unlocks (unlock text mentions midnight-local
  rolling unlock). The target (GTA VI, and all practice launches) unlocks at
  rolling local midnight.

Everything is computed at runtime from the case file's comparables (38 in a
practice case, 42 in the final). Nothing is hardcoded from the practice
cases. The GTA VI category's own pre-release history (no release day yet) is
skipped automatically. If no comparable is usable, falls back to the
persistence baseline (starter formula) so the case still validates.

## What the shape looks like (rolling-midnight median r_h)
Dips to about -0.34 at hour 3, recovers as the US unlocks (hours 6 and 9),
rises to about +0.88 at hour 19, then falls. Simultaneous-global-unlock
games rise far more steeply (median +2.68 at hour 22) because their hour 1
is still pre-unlock baseline — hence the rolling bonus and the h1 kernel.

## Validation
- **LOO over the 38 comparables** (each held out, predicted from the other
  37): rolling-midnight targets, mean pinball loss **0.2775** vs persistence
  baseline **0.3701**. All-comparables LOO: 0.4100 vs 0.9297. The h1 kernel
  was the single biggest win (all-equal quantiles: 0.3647 on rolling
  targets); the rolling bonus and bw=1.0 were tuned on this LOO. A
  pre-release "jump" signal (h1 vs 7-day pre-release median) was tested and
  rejected — it hurt (0.2934 vs 0.2775). Spread multipliers > 1.0 hurt.
- **Practice loss, scored locally** (`score_practice.py`, answers re-fetched
  from SullyGnome's public chart API exactly as `input/NOTICE.txt`
  documents; hour-1 values match all four cases): **0.228645**
  (typical miss 41.8%, 90% coverage 0.935). Per case: p00 0.391, p01 0.191,
  p02 0.133, p03 0.200.
- **Starter baseline, same local scorer: 0.387097** (typical miss 82.7%,
  coverage 0.783) — matches the kit's stated ~0.387 / 82.8% / 0.783, so the
  local scorer is calibrated. My entry beats the baseline on every practice
  case, by 41% overall.
- bw=1.5 was tested on the practice and lost (0.2368 vs 0.2286); kept bw=1.0.
- Determinism: two runs byte-identical. Runtime ~0.17 s/case (cap 8 s).
- Synthetic final-scale test (h1 = 800,000): median dips to 0.48x at hour
  10 and recovers to 1.25x at hour 19 — the already-peaked giant shape.

## Known limitation
Wolverine (p00) is the weakest case (0.391): its actual viewers rose to ~9x
hour 1 by hour 21, beyond any comparable's curve. No comparable predicts a
rise that extreme from hour 1 alone; the model underpredicts late hours for
small-hour-1 launches that explode in the US evening. The spread still
covered the actuals (overall coverage 0.935).

## Files
- `main.py` — the entry.
- `loo.py` — leave-one-out validation harness (comparables only).
- `loo-results.txt` — full LOO output.
- `score_practice.py` — local practice scorer (fetches the 4 practice
  launches' release days from SullyGnome per NOTICE.txt).
- `practice-answers.json` — the 4 practice release days (hourly viewers).
