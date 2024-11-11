# FatigueVSFreethrow

### Description
A data analysis project investigating how consecutive minutes played affects NBA players' free throw shooting percentage.

### Installation
```bash
# Create virtual environment 
python3 -m venv myenv

# Activate virtual environment
source myenv/bin/activate  # On Unix/macOS
.\myenv\Scripts\activate   # On Windows

# Install required packages
pip install basketball_reference_web_scraper matplotlib numpy
```

### Usage
```python
# Run test version first to validate API access
python main.py --test

# Run full analysis
python main.py
```

### Core Components
- **FreeThrowAnalyzer**: Main class handling data collection and analysis
- **Data Processing**: Tracks player minutes and free throw attempts
- **Visualization**: Creates plots comparing performance vs fatigue
- **Rate Limiting**: Handles Basketball Reference API restrictions

### Project Structure
```
FatigueVSFreethrow/
├── main.py              # Main script
├── requirements.txt     # Package dependencies
├── README.md           # Documentation
└── output/             # Generated visualizations
```

### Data Collection
- Sources data from Basketball Reference API
- Collects play-by-play data for NBA games
- Tracks:
  - Player substitutions
  - Minutes played
  - Free throw attempts
  - Season averages

### Output
- Generates 'ft_percentage_analysis.png'
- Shows:
  - Free throw % by minute played
  - Season average comparison
  - Performance difference

### Known Limitations
- Only processes first playing stint (to reduce bias), subject to change
- May be subject to API rate limits
- Manual schedule handling may be needed pending rate limit troubleshooting
- One season data only (ex 2023-24)

### Contributing
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

### License
GNU
