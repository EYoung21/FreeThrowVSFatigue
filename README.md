# FatigueVSFreethrow

### Description
A data analysis project investigating how consecutive minutes played affects NBA players' free throw shooting percentage.

### Project Goal
Analyze the relationship between fatigue (measured by consecutive minutes played) and free throw percentage in the NBA 2023-24 season. This project aims to understand whether extended playing time impacts a player's performance in this crucial aspect of the game.

### Data Collection
We collect data from Basketball Reference (basketball-reference.com) by:
1. Accessing one player's game logs per team (30 total) 
2. Using these logs to get play-by-play data for all games
3. Processing each unique game to track:
  - Player substitution patterns
  - Free throw attempts and makes
  - Time stamps for all events

### Analysis Method
- Track first continuous playing stint for each player in each game
- Calculate free throw percentage at each minute interval
- Compare against players' season averages
- Generate visualization showing:
 - Expected FT% (season average)
 - Actual FT% at each minute interval
 - Difference between expected and actual

### Project Structure
.
├── data_collection/   # Scripts for gathering and processing data
├── analysis/         # R analysis scripts 
├── output/          # Results and visualizations
└── README.md

### Dependencies
- Python 3.8+
- R 4.0+
- Required Python packages:
 - requests
 - pandas
 - beautifulsoup4
- Required R packages:
 - tidyverse
 - ggplot2

### Setup
1. Clone the repository
2. Install required packages:
  pip install -r requirements.txt
3. Run data collection scripts
4. Execute analysis scripts
5. View results in output directory

### Contributing
1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

### License
GNU General Public License v3.0
