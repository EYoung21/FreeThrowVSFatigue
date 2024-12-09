# FatigueVSFreethrow

## Project Overview
FatigueVSFreethrow analyzes the relationship between playing time and free throw shooting performance in the NBA from 2000-2024, with special focus on historically best and worst free throw shooters.

## Installation
Set up a virtual environment:
python3 -m venv myenv
source myenv/bin/activate  # Unix/macOS
.\myenv\Scripts\activate   # Windows

Install required packages:
pip install basketball_reference_web_scraper
pip install matplotlib
pip install numpy
pip install pandas
pip install scipy
pip install pytz

## Core Components
- Data Collection: Processes play-by-play data from Basketball Reference API
- Time Tracking: Monitors first continuous playing stint before substitution
- Analysis Groups:
  - 15 best free throw shooters (e.g., Nash, Lillard)
  - 15 worst free throw shooters (e.g., O'Neal, Antetokounmpo)
- Visualization: Generates both individual and group analysis graphs

## Data Processing
- Tracks minutes played before first substitution
- Records free throw attempts and makes
- Calculates:
  - Per-minute shooting percentages
  - Weighted season averages
  - Performance differentials
  - Statistical regressions

## Output Files
1. Individual Player Analysis:
   - [player_name]_career_timeline.png: FT% vs minutes played
   - [player_name]_regression.png: Actual vs expected performance
   - [player_name]_data.csv: Raw statistical data

2. Group Analysis:
   - best_group_timeline.png: Best shooters composite analysis
   - worst_group_timeline.png: Worst shooters composite analysis
   - Associated CSV files with statistical data

## Usage
Initialize analyzer:
analyzer = FreeThrowAnalyzer()

Process data:
create_player_career_graphs(best_ft_shooters + worst_ft_shooters)
create_group_graph(best_ft_shooters, "Best")
create_group_graph(worst_ft_shooters, "Worst")

## API Rate Management
- Implements 1.89s delay between requests
- Includes retry logic for rate limit responses
- Error logging system for failed requests

## Data Storage
/dataForEachPlayerYear/
- player_attempt_counter_{year-1}-{year}.txt
- player_minute_averages_{year-1}-{year}.txt
- yearly_averages_{year-1}-{year}.txt

## Known Limitations
- Analyzes only first continuous playing stint
- Subject to Basketball Reference API rate limits
- Requires stable internet connection for data collection
- Some historical player data may be incomplete

## Contributing
1. Fork repository
2. Create feature branch
3. Follow existing code structure
4. Include error handling
5. Submit pull request

## License
GNU General Public License v3.0
