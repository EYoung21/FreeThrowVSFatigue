# FatigueVSFreethrow

## Project Overview
FatigueVSFreethrow is a data analysis tool designed to investigate how consecutive playing minutes impact NBA players' free throw shooting percentages. This project gathers minute-by-minute player data to analyze free throw success as fatigue increases.

## Installation
```bash
# Set up a virtual environment
python3 -m venv myenv

# Activate the virtual environment
source myenv/bin/activate  # On Unix/macOS
.\myenv\Scripts\activate   # On Windows

# Install necessary packages
pip install basketball_reference_web_scraper matplotlib numpy


```

## Usage
```bash
# Run a test version to check API access and data retrieval
python main.py --test

# Run the complete data analysis
python main.py
```

## Core Components

FreeThrowAnalyzer: Primary class for collecting, processing, and analyzing free throw data.
Data Processing: Tracks player minutes and free throw attempts to examine changes over time.
Visualization: Generates graphs comparing free throw percentage as a function of playing time.
API Rate Management: Includes mechanisms for handling Basketball Reference's API limits.

## Data Collection Details
Sources data from Basketball Reference API
Focuses on game-by-game player performance, tracking:
Substitution timings
Minutes played
Free throw attempts and makes
Yearly performance averages for context

## Output and Visualization
Generates ft_percentage_analysis.png to visualize:
Free throw percentage based on playing minutes
Comparison to season averages
Performance differential over time to highlight fatigue effects

## Known Limitations
Current analysis focuses only on the initial playing stint to reduce potential bias.
API rate limits may require manual schedule adjustments.
Designed for analysis of one season (e.g., 2023-24) at a time (will be updated to include all seasons from 2000 - present, later).

### Contributing
Fork the repository
Create a feature branch
Commit your changes
Push the branch to your fork
Open a Pull Request for review

## License
This project is licensed under the GNU General Public License v3.0. See the LICENSE file for more details.
