### Free Throw vs. Fatigue — Statistical Analysis of NBA Player Performance (1997–2024)

This project analyzes how consecutive minutes played affects NBA free throw accuracy. It combines play-by-play parsing, season totals, and reproducible visualizations at the season, group, and player levels.

### Highlights
- **Scope**: 24 seasons (1997–2024), 30 teams.
- **Method**: Track first continuous stint (consecutive minutes before substitution) and compare FT% by minute versus baseline season/career averages.
- **Pipelines**: Web scraping with rate-limit handling and retries, robust error logging, aggregation, regression, and plotting.

### Quick start
- Python 3.10+ recommended
- Create and activate a virtual environment:
  - Windows PowerShell: `python -m venv .venv && .\.venv\Scripts\Activate.ps1`
  - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

### How to run
- **Season-level aggregation and figures**: run `dataProcessor.py` (uses `dataForEachYear` inputs and produces season/regression CSVs and PNGs).
- **Player/group careers and figures**: run `specificDataProcessor.py` (uses `dataForEachPlayerYear`, writes to `ft_analysis_graphs`).
- **Attempt counter merger (multi-year)**: run `attemptCounterFile.py`.
- **Example single-season analysis**: `9697.py` shows one-season plotting workflow.

Note: Some scripts expect season-total CSVs in the project root (e.g., `1997_1998_player_season_totals.csv`, `1997_1998_season.csv`). These are kept at the root for compatibility.

### Repository structure
- `dataForEachYear/` — per-season minute averages, yearly averages, attempt counters (JSON-as-*.txt files used by the pipeline)
- `dataForEachPlayerYear/` — per-player per-season inputs for career/group analyses
- `ft_analysis_graphs/` — generated career and group plots and data CSVs
- `reports/years/` — season-level plots and CSV outputs (regression and FT% vs minutes)
- `logs/` — error and run logs
- `docs/` — project artifacts (PDFs, screenshots)
- `data/aggregated/` — combined multi-year summaries (convenience copies)
- `*_player_season_totals.csv`, `*_season.csv` — raw season exports kept at repo root for script paths

### Features and methodology
- **Consecutive minutes tracking**: Compute minutes since last entry and bin FT attempts by minute into the game.
- **Baselines**: Compare minute FT% to weighted season/career averages based on attempt counts.
- **Regression and trends**: Export regression stats and trend lines for FT% vs baseline and by minute.
- **Rate limiting**: Respect API limits with ~1.89s delay, Retry-After handling, and default backoff; all failures logged.

### Usage examples
- Generate season outputs (see console for progress):
  - Windows/macOS/Linux: `python dataProcessor.py`
- Generate all player career plots for predefined groups:
  - `python specificDataProcessor.py`
- Combine attempt counters across seasons:
  - `python attemptCounterFile.py`

Key outputs will appear in `reports/years/` and `ft_analysis_graphs/`.

### Dependencies
Installed via `requirements.txt`:
- `basketball-reference-web-scraper`, `nba-api`, `requests`, `pytz`, `pandas`, `numpy`, `scipy`, `matplotlib`, `bs4`

### Data sources
- Play-by-play and schedule data via `basketball_reference_web_scraper`
- Supplementary metadata via `nba_api`

### Notes and limitations
- Focuses on the first continuous stint; intentional late-game misses are not specially modeled.
- Historical data inconsistencies may exist for certain players or seasons.
- Requires network access during scraping; cached CSVs are kept at the root for reproducibility.

### License
GNU General Public License v3.0

### Final project report (STAT 011, Swarthmore)
This project was completed as my final project for STAT 011 (Statistical Methods I) at Swarthmore College.

View the full write-up below. If the embed does not render on your platform, use the link.

<div align="center">
  <object data="docs/STATS%20011_%20%E2%80%9CDrained%20or%20Just%20Tired%20%E2%80%93%20Effects%20of%20Consecutive%20Minutes%20Played%20on%20Free%20Throw%20Accuracy%E2%80%9D%20%281%29.pdf" type="application/pdf" width="100%" height="800px">
    <a href="docs/STATS%20011_%20%E2%80%9CDrained%20or%20Just%20Tired%20%E2%80%93%20Effects%20of%20Consecutive%20Minutes%20Played%20on%20Free%20Throw%20Accuracy%E2%80%9D%20%281%29.pdf">Open the STAT 011 final report (PDF)</a>
  </object>
</div>
