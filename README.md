# Agro Advisory Prototype (Python)

A rule-based “expert system” prototype that generates simple crop recommendations based on soil and rainfall inputs.
Designed as a beginner-friendly AgriTech project that is easy to explain and extend.

## What it does
- Accepts crop + soil values (pH, N, P, K) + rainfall
- Produces a basic NPK estimate and practical tips
- Saves outputs to:
  - `outputs/history.json` (run history)
  - `outputs/recommendation_<crop>_<timestamp>.txt` (text report)

## Tech
- Python (standard library only)
- JSON rules file (`rules.json`)

## Run
Example:
```bash
python advisor.py --crop maize --ph 6.2 --n 30 --p 10 --k 70 --rainfall 650
