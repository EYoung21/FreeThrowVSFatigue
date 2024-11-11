from basketball_reference_web_scraper import client
from basketball_reference_web_scraper.data import OutputType

# Get all 2017-2018 regular season player box scores for Russell Westbrook
print("Getting 2017-2018 regular season player box scores for Russell Westbrook")
print(client.regular_season_player_box_scores(player_identifier="westbru01", season_end_year=2018))

# Get all 2017-2018 regular season player box scores for Russell Westbrook in JSON format
print("Getting 2017-2018 regular season player box scores for Russell Westbrook in JSON format")
print(client.regular_season_player_box_scores(player_identifier="westbru01", season_end_year=2018, output_type=OutputType.JSON))

# Output all 2017-2018 regular season player box scores for Russell Westbrook in JSON format to 2017_2018_russell_westbrook_regular_season_box_scores.json
print("Writing 2017-2018 regular season player box scores for Russell Westbrook to JSON file")
client.regular_season_player_box_scores(player_identifier="westbru01", season_end_year=2018, output_type=OutputType.JSON, output_file_path="./2017_2018_russell_westbrook_regular_season_box_scores.json")

# Output all 2017-2018 regular season player box scores for Russell Westbrook in CSV format to 2017_2018_russell_westbrook_regular_season_box_scores.csv
print("Writing 2017-2018 regular season player box scores for Russell Westbrook to CSV file")
client.regular_season_player_box_scores(player_identifier="westbru01", season_end_year=2018, output_type=OutputType.CSV, output_file_path="./2017_2018_russell_westbrook_regular_season_box_scores.csv")