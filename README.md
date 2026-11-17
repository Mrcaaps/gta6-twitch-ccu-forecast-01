# GTA VI Twitch CCU Forecast

[![make.fun](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Mrcaaps/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Mrcaaps/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)

Entry for [Forecast GTA VI's launch-day Twitch viewers hour by hour](https://make.fun/bounty/gta6-twitch-ccu-forecast-01) ($250, 20 places).

`main.py` (Python 3.13, standard library only) forecasts the Grand Theft Auto VI
Twitch category's concurrent viewers for hours 2–24 of its release day (2026-11-19
UTC) from hour 1's print, as five quantiles per hour. The model takes each
comparable past big launch's log-ratio curve `r_h = ln(v_h) − ln(v_1)` and, per
hour, reports the weighted quantiles of `r_h` across comparables — weighted by
how similar the comparable's hour-1 size is to the target's (Gaussian kernel on
`ln(v_1)`, bandwidth 1.0) with a ×3 bonus for rolling-midnight unlocks (GTA VI
unlocks at midnight local, country by country). Everything is computed at
runtime from the case file's comparables; nothing is hardcoded from the practice
cases. Deterministic, no network, no wall clock, ~0.17 s per case.

Local practice loss **0.228645** (typical miss 41.8%, 90% coverage 0.935) vs the
house persistence baseline's 0.387 — a 41% improvement. Per case: Wolverine
0.391, RDR2 0.191, God of War Ragnarök 0.133, Spider-Man 2 0.200. See
[MODEL.md](MODEL.md) for the model, the leave-one-out validation
(0.2775 vs baseline 0.3701 on rolling-midnight targets) and the rejected
variants.

## Run

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```
