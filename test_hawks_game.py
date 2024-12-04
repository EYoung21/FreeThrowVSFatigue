from basketball_reference_web_scraper import client
import time
import requests
import csv
import os
from basketball_reference_web_scraper.data import Team, OutputType
from datetime import datetime

def changeToFirst(word):
    # print(f"Processing name: '{word}'")  # Debug print
    if not word or not isinstance(word, str):
        print(f"Invalid name format received: {word}")
        return None
        
    word = word.strip()
    stringArr = word.split(" ")
    if len(stringArr) < 2:
        print(f"Name does not contain space: {word}")
        return None
        
    try:
        firstString = stringArr[0][0] + "." #gets first letter of first name
        secondString = stringArr[1] #gets second string
        fullString = firstString + " " + secondString
        print(f"Converted name: '{fullString}'")  # Debug print
        return fullString
    except Exception as e:
        print(f"Error processing name '{word}': {str(e)}")
        return None

def get_player_ft_pct(player_name, year):
    print(f"\nLooking up free throw percentage for: {player_name}")
    
    # Download season data if needed
    try:
        if not os.path.exists(f"./{year-1}_{year}_player_season_totals.csv"):
            client.players_season_totals(
                season_end_year=year,
                output_type=OutputType.CSV,
                output_file_path=f"./{year-1}_{year}_player_season_totals.csv"
            )
            time.sleep(1.85)
    except requests.exceptions.HTTPError as e:
        print(f"Error downloading season data: {e}")
        return None

    # Read and process the data
    try:
        with open(f"./{year-1}_{year}_player_season_totals.csv") as file:
            reader = csv.reader(file, delimiter=',')
            next(reader)  # Skip header
            rows = list(reader)[:-1]  # Skip league averages row
            
            found = False
            for i, row in enumerate(rows):
                fullString = changeToFirst(row[1])
                if fullString is None:
                    continue
                
                if fullString == player_name:
                    found = True
                    print(f"Found player: {row[1]}")
                    if int(row[13]) > 0:  # If they attempted free throws
                        made = row[12]
                        attempted = row[13]
                        print(f"FT stats - Made: {made}, Attempted: {attempted}")
                        return [int(made), int(attempted)]
                    return "No free throws"
                    
            if not found:
                print(f"Player {player_name} not found in {year-1}-{year} season")
            return None
            
    except Exception as e:
        print(f"Error processing season data: {e}")
        return None

def process_game():
    print("Fetching play-by-play data for Hawks game on 2002-10-31...")
    
    try:
        pbp_data = client.play_by_play(
            home_team=Team.ATLANTA_HAWKS,
            year=2002,
            month=10,
            day=31
        )
        
        print("\nProcessing play-by-play data...")
        player_entry_times = {}
        players_subbed_out = set()
        
        for play in pbp_data:
            print(f"\nPlay: {play.get('description')}")
            
            if 'enters' in str(play.get('description', '')):
                des_parsed = play['description'].split(' enters')
                player_in = des_parsed[0]
                des_parsed2 = des_parsed[1].split('for ')
                players_subbed_out.add(des_parsed2[1])
                player_entry_times[player_in] = 0  # Simplified for test
                
            if 'free throw' in str(play.get('description', '')):
                if 'makes' in play['description']:
                    player = play['description'].split(' makes')[0]
                if 'misses' in play['description']:
                    player = play['description'].split(' misses')[0]
                    
                print(f"\nProcessing free throw for player: {player}")
                ft_pct = get_player_ft_pct(player, 2003)  # 2002-03 season
                print(f"Free throw percentage result: {ft_pct}")
                
    except Exception as e:
        print(f"Error processing game: {e}")
        print(f"Full traceback: {datetime.now()}\n")
        raise

if __name__ == "__main__":
    process_game()