# do for wnba after?
#adjust for intentional misses at end of games somehow (or just drowned out by noise?)
#fix issue where error number for play by play parsing (/ other exceptions) doesn't increment

import csv
from basketball_reference_web_scraper import client
import time
import requests
from basketball_reference_web_scraper.data import Team, OutputType
from datetime import datetime
from typing import Dict, List, Set
import math
from basketball_reference_web_scraper.data import Team, Location
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import csv
import pytz
import pandas as pd
from bs4 import BeautifulSoup
import ast
import os
#import this
from nba_api.stats.static import players
from nba_api.stats.endpoints import commonplayerinfo
import traceback
from datetime import datetime
import json
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import pandas as pd
import os
import json
from typing import Dict, List, Tuple
from collections import defaultdict
from scipy import stats
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# Look for? / do we maybe need to handle?:

# Technical fouls where players aren't actually subbed   ----  handled by substitutions, ex:
# Technical foul by B. Portis	 	16-17	 	 
# 5:01.0	Technical foul by B. Portis	 	16-17	 	 
# 5:01.0	 	 	16-17	 	Technical foul by A. Nembhard
# 5:01.0	B. Portis ejected from game	 	16-17	 	 
# 5:01.0	 	 	16-18	+1	T. Haliburton makes technical free throw
# 5:01.0	P. Connaughton enters the game for P. Beverley	 	16-18	 	 
# 5:01.0	A. Jackson enters the game for B. Portis

# Start of quarters where players "enter" but aren't substituting --- handled already!

# Injuries where players leave without a substitution 
# When there's injuries, it displays as a substitution: ex:Nov 17, 2024
	# J. Wells enters the game for V. Williams

# Overtime periods? -- handled, i think this is what was causing the negative minutes glitch, it's fixed now
# Play off games? -- I tested, they're included

# Time resets due to replay reviews or corrections? -- shouldn't be a problem, I would assume is accurately updated in nba

class ErrorLogger:
    def __init__(self, filename):
        self.filename = filename
        # Clear the file at start
        with open(self.filename, 'w') as f:
            f.write(f"Error Log Started: {datetime.now()}\n{'='*50}\n\n")
    
    def log_error(self, error_type, error_message, details=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.filename, 'a') as f:
            f.write(f"Time: {timestamp}\n")
            f.write(f"Error Type: {error_type}\n")
            f.write(f"Error Message: {error_message}\n")
            if details:
                f.write(f"Details: {details}\n")
            f.write(f"{'='*50}\n\n")

error_logger = ErrorLogger("AllErrors.txt")

class minToAttemptsClass:
    def __init__(self):
        self.minToAttempts = defaultdict(int) #cause its a defaultdict mapping mins to attempts at that minute

class FreeThrowAnalyzer:
    def __init__(self):
        # self.processed_games: Set[str] = set()
        self.minutes = dict()
        
        self.error_logger = ErrorLogger("AllErrors.txt")

        #dict that goes from year to minute to attempts at that minute

        #here, what if instead of dict[minute] = ft made, fr missed, [#set of all players that made up that stat], we do:

        # minute -> ftms ftas (all players made up that figure)

        #NEW IDEA!
        # dict[minute] = [fts made, fts missed, all players that made up that stat's yearly averages added up, the number of players that amde up that stat]
        # then we can calculate the average of the yearly averages at each minute later.
        #NEW IDEA!


        # // total %
        # // number of players that make up percentage
        # // weight by number of ft attempts for each player
        # // weight would be number of attempts    (may want to store number made, too)


        #WHAT TO DO
        # add up all the total %s, where total % == (sum of all yearly percentage * number of ft attempted) / sum of all # ft attempted
        # divide that total by the number of players that made up the percentage through accumulator

        # weight handled above



        #each minute should have a total made and total missed
        #AND a an average of each player's yearly ft % that is included in the above
        #      - we can accomplish this by keeping a set of players that show freethrows during this consequetive minute
        #      - and also then calculating the whole average after we're done parsing data (Made / made + missed)
        self.total_attempted = 0
        self.total_made = 0
        self.total_negative_minutes = 0
        self.ftNameToActualName = dict()
        
        #dictionary of dictionaries
        self.actualNameToSeasonAverages = dict()
        #maps from "actual_name" to a dictionary of years mapped to arrays of [total_made, total_attempted] //should eliminate having to reparse seaosn averages

        self.dictionary_error_counter = 0

        self.play_by_play_error_counter = 0

            
    def process_team_games(self, team: Team, year: int, month: int, day: int, seasonYear, attemptCounter):
        #for each team, loop through every day in the season and get only HOME games, call this function on it
        """Get play by play data for a team's game on a specific date."""
        try:
            # print("we're here2")
            pbp_data = client.play_by_play(
                home_team=team,
                year=year,
                month=month,
                day=day
            )
            time.sleep(1.89)
            self._process_game_data(pbp_data, team, year, month, day, seasonYear, attemptCounter) #passing year so I can print it
            # print("play by play: " + str(pbp_data))
            # exit()

            # print("playByPlay dara: " + str(pbp_data))
            
            # game_id = f"{year}{month:02d}{day:02d}_{team}"
            # if game_id not in self.processed_games:
            # self.processed_games.add(game_id)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Log the initial rate limit error
                error_details = {
                    "team": str(team),
                    "date": f"{year}-{month}-{day}",
                    "status_code": 429,
                    "error_type": "Rate Limit"
                }
                self.error_logger.log_error("RateLimitError", str(e), error_details)
                
                # Get the Retry-After header, if available
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    # Log retry attempt
                    self.error_logger.log_error(
                        "RetryAttempt", 
                        f"Rate limited. Retrying after {retry_after} seconds.",
                        {"retry_after": retry_after}
                    )
                    print(f"Rate limited. Retrying after {retry_after} seconds.")
                    time.sleep(int(retry_after))
                    try:
                        # Retry the request
                        pbp_data = client.play_by_play(
                            home_team=team,
                            year=year,
                            month=month,
                            day=day
                        )
                        time.sleep(1.89)
                        self._process_game_data(pbp_data, team, year, month, day, seasonYear, attemptCounter)
                    except Exception as retry_error:
                        # Log any errors during retry
                        error_details = {
                            "team": str(team),
                            "date": f"{year}-{month}-{day}",
                            "retry_attempt": "after_rate_limit",
                            "traceback": traceback.format_exc()
                        }
                        self.error_logger.log_error("RetryError", str(retry_error), error_details)
                        raise
                else:
                    # Log default retry attempt
                    self.error_logger.log_error(
                        "RetryAttempt", 
                        "Rate limited. No Retry-After header found. Using default 60 second wait.",
                        {"default_wait": 60}
                    )
                    print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                    time.sleep(60)  # Default wait time if Retry-After header is missing
                    try:
                        pbp_data = client.play_by_play(
                            home_team=team,
                            year=year,
                            month=month,
                            day=day
                        )
                        time.sleep(1.89)
                        self._process_game_data(pbp_data, team, year, month, day, seasonYear, attemptCounter)
                    except Exception as retry_error:
                        # Log any errors during retry
                        error_details = {
                            "team": str(team),
                            "date": f"{year}-{month}-{day}",
                            "retry_attempt": "default_wait",
                            "traceback": traceback.format_exc()
                        }
                        self.error_logger.log_error("RetryError", str(retry_error), error_details)
                        raise
            else:
                # Log non-rate-limit HTTP errors
                error_details = {
                    "team": str(team),
                    "date": f"{year}-{month}-{day}",
                    "status_code": e.response.status_code if hasattr(e, 'response') else 'N/A',
                    "traceback": traceback.format_exc()
                }
                self.error_logger.log_error("HTTPError", str(e), error_details)
                print(f"Error getting PBP {team} on {year}-{month}-{day}: {e}")
                raise
    
    def _process_game_data(self, pbp_data: List[dict], team, year, month, day, seasonYear, attemptCounter):
        # print("we're here3")
        player_entry_times = {}
        playersThatSubbedOut = set()

        # self.technical_foul_counter = {}  # Tracks technicals per player

        # Debug: Print the full game timeline
        # print("\n=== Game Timeline ===")
        # for play in pbp_data:
        #     print(f"Period: {play.get('period')}, Remaining Seconds: {play.get('remaining_seconds_in_period')}, Description: {play.get('description')}")
        
        # // total %
        #     // number of players
        #     // weight by number of ft attempts for each player
        #     // weight would be number of attempts    (may want to store number made, too)
        # print("yudjkse")
        for play in pbp_data:
            # print(str(play))
            # continue

            if 'enters' in str(play.get('description', '')):
                desParsed = play['description'].split(' enters')
                player_in = desParsed[0]
                desParsed2 = desParsed[1].split('for ')
                playersThatSubbedOut.add(desParsed2[1])
                
                # Debug: Print substitution details
                converted_time = self.calculateConvertedIGT(play.get('remaining_seconds_in_period'), play.get('period'), play.get('period_type'))
                # print(f"\n=== Substitution ===")
                # print(f"Player entering: {player_in}")
                # print(f"Period: {play.get('period')}")
                # print(f"Remaining seconds: {play.get('remaining_seconds_in_period')}")
                # print(f"Converted time: {converted_time}")
                
                player_entry_times[player_in] = converted_time

            if 'free throw' in str(play.get('description', '')):
                # print(str(play))
                self.total_attempted += 1
                if 'makes' in play['description']:
                    player = play['description'].split(' makes')[0]
                    self.total_made += 1
                if 'misses' in play['description']:
                    player = play['description'].split(' misses')[0]

                if player in playersThatSubbedOut:
                    continue
                print("Curr team: " + str(team))
                print("Curr year: " + str(year))
                # Debug: Print free throw details
                # print(f"\n=== Free Throw ===")
                # print(f"Player: {player}")
                # print(f"Period: {play.get('period')}")
                # print(f"Remaining seconds: {play.get('remaining_seconds_in_period')}")
                
                if player not in player_entry_times:
                    print(f"Starter detected: {player}")
                    player_entry_times[player] = float(0.0)
                
                # print("HEREEEE")

                entry_time = player_entry_times.get(player)
                # print("HEREEEE2")
                # print(str(play.get('remaining_seconds_in_period')) + " " + str(play.get('period')) + " " + str(play.get('period_type')))
                current_time = self.calculateConvertedIGT(play.get('remaining_seconds_in_period'), play.get('period'), play.get('period_type'))
                # print("HEREEEE3")

                print(f"Entry time seconds: {entry_time}")
                print(f"Current time seconds: {current_time}")
                
                seconds_played = current_time - entry_time
                
                # print(f"Seconds played: {seconds_played}")
                
                minutes_played = seconds_played / 60

                print(f"Minutes played: {minutes_played}")
                
                if minutes_played < 0:
                    print(f"WARNING: Negative minutes detected at {minutes_played}!")
                    # print(f"Full play data: {play}")

                    debug_string = f"""
                    Negative minutes detected:
                    Player: {str(player)}
                    Entry time (seconds): {str(entry_time)}
                    Current time (seconds): {str(current_time)}
                    Minutes played: {str(minutes_played)}
                    Team: {str(team)}
                    Year: {str(year)}
                    Month: {str(month)}
                    Day: {str(day)}
                    """

                    print(debug_string)

                    with open('negativeMinsDebugging.txt', 'a') as f:
                        f.write(debug_string)  # Write to file

                    self.total_negative_minutes += 1
                    continue

                curr_minute = int(math.floor(minutes_played))

                print("minute played: " + str(curr_minute))

                
                # print("curr_minute: " + str(curr_minute))
                # print(str(self.minutes))
                # ft_pct = self.get_player_ft_pct(player, seasonYear)
                # print("returned: " + str(ft_pct))
                # exit()
                if curr_minute not in self.minutes:
                    ft_pct = self.get_player_ft_pct(player, seasonYear)
                    # print(str(ft_pct))
                    if ft_pct is None or ft_pct == "No free throws":
                        print(f"No FT data found for {player} in year {year}")
                        continue
                    
                    if 'makes' in play['description']:
                        print(str(player))
                        print("make")
                        self.minutes[curr_minute] = [1, 0, dict()]
                        self.minutes[curr_minute][2][player] = [1, ft_pct[0]/ft_pct[1] * 100] # Convert to percentage
                        
                        attemptCounter.minToAttempts[curr_minute] += 1
                        # print("percentage just retrieved: " + str(self.minutes[curr_minute][2][player][1]))
                    else:
                        print(str(player))
                        print("miss")
                        self.minutes[curr_minute] = [0, 1, dict()]
                        self.minutes[curr_minute][2][player] = [1, ft_pct[0]/ft_pct[1] * 100] # Convert to percentage
                        # print("percentage just retrieved: " + str(self.minutes[curr_minute][2][player][1]))
                        attemptCounter.minToAttempts[curr_minute] += 1
                else:
                    ft_pct = self.get_player_ft_pct(player, seasonYear)
                    if ft_pct is None or ft_pct == "No free throws":
                        print(f"No FT data found for {player} in year {year}")
                        continue
                        
                    if 'makes' in play['description']:
                        print(str(player))
                        print("make")
                        self.minutes[curr_minute][0] += 1
                        if player not in self.minutes[curr_minute][2]:
                            self.minutes[curr_minute][2][player] = [1, ft_pct[0]/ft_pct[1] * 100]
                        else:
                            self.minutes[curr_minute][2][player][0] += 1

                        attemptCounter.minToAttempts[curr_minute] += 1
                        # print("percentage just retrieved: " + str(self.minutes[curr_minute][2][player][1]))
                    else:
                        print(str(player))
                        print("miss")
                        self.minutes[curr_minute][1] += 1
                        if player not in self.minutes[curr_minute][2]:
                            self.minutes[curr_minute][2][player] = [1, ft_pct[0]/ft_pct[1] * 100]
                        else:
                            self.minutes[curr_minute][2][player][0] += 1

                        attemptCounter.minToAttempts[curr_minute] += 1
                        # print("percentage just retrieved: " + str(self.minutes[curr_minute][2][player][1]))
                # print("Minutes: ")
                # print(str(self.minutes))
                print()
    
    def calculateConvertedIGT(self, remainingSecondsInPeriod, quarter, typeIs): #remaining seconds, quarter (1, 2, 3, 4)
        # print("remaining seconds: " + str(remainingSecondsInQuarter))
        # print("quarter: " + str(quarter))
        # exit()
        # print("the type is: " + str(typeIs))
        if str(typeIs) != "PeriodType.OVERTIME":
            return (quarter * 12 * 60) - remainingSecondsInPeriod #returns seconds elapses so far
        else:
            # print("it's OVERTIME!!dwkfuhwflhwfe")
            return (4*12*60) + (quarter*5*60) - remainingSecondsInPeriod

        #will return array where first bucket is dictionary of minutes to minute averages and second bucket is dictionary of minutes to yearly averages
    
    def calculateMinuteAndYearlyAverages(self):
        atMinuteAverages = dict() #maps minutes to their minute averages (of all fts at that minute)
        atMinuteYearlyAverages = dict()

        for minute in self.minutes:
            
            minuteAverage = self.minutes[minute][0] / (self.minutes[minute][0] + self.minutes[minute][1])  #total made / total made + total missed
            atMinuteAverages[minute] = minuteAverage * 100 #to get percentage

            # playerLength = len(list(self.minutes[key][2]))
            #don't think i need
            
            numeratorSum = 0
            
            denominatorSum = 0

            for player in self.minutes[minute][2]:
                numerator = self.minutes[minute][2][player][0] * self.minutes[minute][2][player][1]
                denominator = self.minutes[minute][2][player][0]

                numeratorSum += numerator

                denominatorSum += denominator

            
            atMinuteYearlyAverages[minute] = float(numeratorSum / denominatorSum)
            #this is our weighted average ft% at a given min

            #sum of all %s * attampts / sum of all attempts
        
        return [atMinuteAverages, atMinuteYearlyAverages]
    
    def get_player_ft_pct(self, player_name, year): 
        #number_repeated represents how many consequetive times a player's ft average comes from another team
        # print("playername: " + player_name)
        def changeToFirst(word):
            if word == "Nenê":
                return "N. Hilário"
            if not word or not isinstance(word, str):
                print(f"Warning: Invalid name format: {word}")
                return None
            
            word = word.strip()
            # Debug print
            # print(f"Processing name: '{word}'")

            stringArr = word.split(" ")
            if len(stringArr) < 2:
                print(f"Warning: Name does not contain space: {word}")
                return None
                
            try:
                firstString = stringArr[0][0] + "." #gets first letter of first name
                secondString = stringArr[1] #gets second string
                fullString = firstString + " " + secondString
                return fullString
            except Exception as e:
                error_details = {
                    "input_word": word,
                    "string_array": stringArr,
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc()
                }
                error_logger.log_error("NameProcessingError", f"Error processing name '{word}': {str(e)}", error_details)
                print(f"Error processing name '{word}': {str(e)}")
                return None
                
        try:
            if not os.path.exists(f"./{year-1}_{year}_player_season_totals.csv"):
                client.players_season_totals(
                    season_end_year=year, 
                    output_type=OutputType.CSV, 
                    output_file_path=f"./{year-1}_{year}_player_season_totals.csv"
                )
                time.sleep(1.89)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Get the Retry-After header, if available
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    # If Retry-After is in seconds, wait that long
                    print(f"Rate limited. Retrying after {retry_after} seconds.")
                    time.sleep(int(retry_after))
                    # Retry the request
                    if not os.path.exists(f"./{year-1}_{year}_player_season_totals.csv"):
                        client.players_season_totals(
                            season_end_year=year, 
                            output_type=OutputType.CSV, 
                            output_file_path=f"./{year-1}_{year}_player_season_totals.csv"
                        )
                        time.sleep(1.89)
                else:
                    print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                    time.sleep(60)  # Default wait time if Retry-After header is missing
                    if not os.path.exists(f"./{year-1}_{year}_player_season_totals.csv"):
                        client.players_season_totals(
                            season_end_year=year, 
                            output_type=OutputType.CSV, 
                            output_file_path=f"./{year-1}_{year}_player_season_totals.csv"
                        )
                        time.sleep(1.89)
            else:
                # Re-raise if it's a different HTTP error
                raise
        
        with open(f"./{year-1}_{year}_player_season_totals.csv") as file:
            reader = csv.reader(file, delimiter=',')
            next(reader)  # Skip header
            rows = list(reader)
            if not rows:
                print(f"Warning: No data found for year {year}")
                return None
            #indcies 12 and 13 are made and attempted respectively
            rows = rows[:-1] #skip last row, league averages
            print(f"Looking for {player_name} in {year-1}-{year} season")
            found = False
            for i, row in enumerate(rows):
                # player_row = row[0]
                # print("Player from row: " + row[1])
                # print("name from rows: " + row[1])
                fullString = changeToFirst(row[1])
                if fullString is None:
                    # Skip this row or handle the error appropriately
                    continue

                # print("changed: " + fullString)
                # exit()
                # print("Player from row changed name: " + fullString)

                if fullString == player_name:
                    found = True
                    # print(f"Found {player_name}: FT made={row[12]}, FT attempted={row[13]}")
                    # print("Player from row: " + row[1])
                    if int(row[13]) > 0: # avoid division by zero
                        made = row[12]
                        attempted = row[13]
                        if i + 1 >= len(rows) or changeToFirst(rows[i+1][1]) != player_name:
                            # print("player only appeared once")
                            return [int(made), int(attempted)] 
                            #returns array of number made in first bucket and number attempted in second bucket
                        else:
                            indicesToCheck = []
                            j = i+1
                            while j < len(rows):
                                if changeToFirst(rows[j][1]) == player_name:
                                    indicesToCheck.append(j)
                                j += 1

                            for k in range(len(indicesToCheck)):
                                if int(rows[k][13]) > 0:
                                    made += rows[k][12]
                                    attempted += rows[k][13]
                            # print("player was traded mid season")
                            return [int(made), int(attempted)] 
                            #returns array of number made in first bucket and number attempted in second bucket
                    return "No free throws"
            if not found:
                print(f"Player {player_name} not found in {year-1}-{year} season")
            return None #if player requested wasn't in season stats

def get_team_home_dates(team, year):
    # Open the file and create the reader
    try:
        if not os.path.exists(f"./{year-1}_{year}_season.csv"):
            client.season_schedule(
                season_end_year=year,
                output_type=OutputType.CSV,
                output_file_path=f"./{year-1}_{year}_season.csv"
            )
            time.sleep(1.89)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            # Get the Retry-After header, if available
            retry_after = e.response.headers.get("Retry-After")
            if retry_after:
                # If Retry-After is in seconds, wait that long
                print(f"Rate limited. Retrying after {retry_after} seconds.")
                time.sleep(int(retry_after))
                # Retry the request
                if not os.path.exists(f"./{year-1}_{year}_season.csv"):
                    client.season_schedule(
                        season_end_year=year,
                        output_type=OutputType.CSV,
                        output_file_path=f"./{year-1}_{year}_season.csv"
                    )
                    time.sleep(1.89)
            else:
                print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                time.sleep(60)  # Default wait time if Retry-After header is missing
                if not os.path.exists(f"./{year-1}_{year}_season.csv"):
                    client.season_schedule(
                        season_end_year=year,
                        output_type=OutputType.CSV,
                        output_file_path=f"./{year-1}_{year}_season.csv"
                    )
                    time.sleep(1.89)
        else:
            print(f"Error getting players season totals for {year}")
            raise


    with open(f"./{year-1}_{year}_season.csv") as file:
        reader = csv.reader(file, delimiter=',')
        # Skip the header row
        next(reader)
        
        # Initialize the dates set
        dates = set()
        
        # Create timezone objects
        utc = pytz.UTC
        et = pytz.timezone('US/Eastern')  # NBA typically uses Eastern Time
        
        for row in reader:
            if row[3] == team:  # If this is a home game
                # Parse the UTC timestamp
                utc_time = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S%z')
                
                # Convert to Eastern Time
                et_time = utc_time.astimezone(et)
                
                # Get just the date part in ET
                game_date = et_time.date()
                
                dates.add(game_date.strftime('%Y-%m-%d'))
                
                # print("CSV DATE: " + row[0])
                # print("Converted date: " + game_date.strftime('%Y-%m-%d'))
                # print()

        
    return sorted(list(dates))

from scipy import stats
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def plot_ft_percentages(minute_averages, yearly_averages, startYear, endYear, totalMade, totalAttempted):
    # Create dataForEachYear directory if it doesn't exist
    if not os.path.exists('dataForEachYear'):
        os.makedirs('dataForEachYear')

    # Get all minutes (x-axis)
    minutes = sorted(minute_averages.keys())

    # Get corresponding values for each line
    ft_percentages = [minute_averages[m] for m in minutes]
    yearly_percentages = [yearly_averages[m] for m in minutes]
    differences = [ft_percentages[i] - yearly_percentages[i] for i in range(len(minutes))]

    # Save differences to a separate CSV in the dataForEachYear folder
    diff_df = pd.DataFrame({
        'Minute': minutes,
        'Difference': differences
    })
    diff_df.to_csv(os.path.join('dataForEachYear', f'difference_averages_{startYear}-{endYear}.txt'), index=False)

    # Linear regression between minute averages and season averages
    slope, intercept, r_value, p_value, std_err = stats.linregress(ft_percentages, yearly_percentages)

    # Save regression details to text file
    with open(f'{startYear}-{endYear}_regression_stats.txt', 'w') as f:
        f.write(f"Analysis for {startYear}-{endYear} NBA Seasons\n")
        f.write("="*40 + "\n\n")
        f.write("Linear Regression Between Minute FT% and Yearly FT%:\n")
        f.write(f"  Slope: {slope:.4f}\n")
        f.write(f"  Intercept: {intercept:.4f}\n")
        f.write(f"  R-squared: {r_value**2:.4f}\n")
        f.write(f"  P-value: {p_value:.4e}\n")
        f.write(f"  Standard Error: {std_err:.4f}\n")

    # Create a line for the regression
    regression_line = slope * np.array(ft_percentages) + intercept

    # Save regression data to DataFrame
    regression_df = pd.DataFrame({
        'Minute_FT%': ft_percentages,
        'Yearly_FT%': yearly_percentages,
        'Regression_Predicted': regression_line
    })
    regression_df.to_csv(f'{startYear}-{endYear}_regression_analysis.csv', index=False)

    # Create DataFrame and save to CSV for original data
    df = pd.DataFrame({
        'Minute': minutes,
        'Minute_Average_FT%': ft_percentages,
        'Season_Average_FT%': yearly_percentages,
        'Difference': differences
    })
    df.to_csv(f'{startYear}-{endYear}_ft_percentage_data.csv', index=False)

    # Create the plot
    plt.figure(figsize=(12, 8))

    # Calculate trendlines
    slope_ft, intercept_ft, r_value_ft, p_value_ft, std_err_ft = stats.linregress(minutes, ft_percentages)
    line_ft = slope_ft * np.array(minutes) + intercept_ft

    slope_yearly, intercept_yearly, r_value_yearly, p_value_yearly, std_err_yearly = stats.linregress(minutes, yearly_percentages)
    line_yearly = slope_yearly * np.array(minutes) + intercept_yearly

    slope_diff, intercept_diff, r_value_diff, p_value_diff, std_err_diff = stats.linregress(minutes, differences)
    line_diff = slope_diff * np.array(minutes) + intercept_diff

    # Create a separate figure for regression plot
    fig_regression = plt.figure(figsize=(6, 6))
    plt.scatter(ft_percentages, yearly_percentages, color='blue', alpha=0.5)
    plt.plot(ft_percentages, regression_line, 'm--', 
            label=f'Regression (R²: {r_value**2:.4f})', linewidth=2)
    plt.xlabel('Minute FT%', fontsize=12)
    plt.ylabel('Season Average FT%', fontsize=12)
    plt.title('Regression: Minute FT% vs Season Average FT%')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{startYear}-{endYear}_regression_plot.png', bbox_inches='tight', dpi=300)
    plt.close()

    # Plot original lines and trendlines
    plt.figure(figsize=(12, 8))
    plt.plot(minutes, ft_percentages, 'b-', label='Actual FT% at minute', linewidth=2)
    plt.plot(minutes, yearly_percentages, 'g-', label='Players\' Season Average', linewidth=2)
    plt.plot(minutes, differences, 'r-', label='Difference', linewidth=2)
    plt.plot(minutes, line_ft, 'b:', label=f'FT% Trend (slope: {slope_ft:.4f})', linewidth=1)
    plt.plot(minutes, line_yearly, 'g:', label=f'Season Avg Trend (slope: {slope_yearly:.4f})', linewidth=1)
    plt.plot(minutes, line_diff, 'r:', label=f'Difference Trend (slope: {slope_diff:.4f})', linewidth=1)

    # Add regression statistics to plot
    stats_text = f'Regression Statistics:\nSlope: {slope:.4f}\nIntercept: {intercept:.4f}\nR²: {r_value**2:.4f}'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
            verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))

    # Customize the plot
    if totalAttempted > 0:
        percentage = round(totalMade/totalAttempted * 100, 2)
    else:
        percentage = ""
    plt.title(f'Free Throw Percentage by Minutes Played for {startYear}-{endYear} Season\nFTA: {totalAttempted}, FTs Made: {totalMade}, %: {percentage}%', 
              fontsize=14, pad=20)
    plt.xlabel('Minutes Played', fontsize=12)
    plt.ylabel('Free Throw Percentage', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')

    # Add a horizontal line at y=0 for reference in difference
    plt.axhline(y=0, color='k', linestyle='-', alpha=0.1)

    # Format y-axis as percentage
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1f}%'.format(y)))

    # Adjust layout to prevent legend cutoff
    plt.tight_layout()

    # Save the plot
    plt.savefig(f'{startYear}-{endYear}_ft_percentage_analysis.png', 
                bbox_inches='tight', dpi=300)
    # plt.show()

 #this function would parse a printed txt file of 
def parse_data_file(file_path, error_logger):  # Add error_logger parameter
    try:
        # Open and read the file content
        with open(file_path, 'r') as file:
            content = file.read()
            
        # Parse the data from string to Python dictionary
        try:
            data = ast.literal_eval(content)
            return data
        except (SyntaxError, ValueError) as e:
            error_details = {
                "file_path": file_path,
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "file_content_preview": content[:200] + "..." if len(content) > 200 else content
            }
            error_logger.log_error("ParseError", str(e), error_details)
            print("Error parsing file:", e)
            return None
            
    except FileNotFoundError as e:
        error_details = {
            "file_path": file_path,
            "error_type": "FileNotFoundError",
            "traceback": traceback.format_exc()
        }
        error_logger.log_error("FileError", str(e), error_details)
        print(f"File not found: {file_path}")
        return None
    except IOError as e:
        error_details = {
            "file_path": file_path,
            "error_type": "IOError",
            "traceback": traceback.format_exc()
        }
        error_logger.log_error("FileError", str(e), error_details)
        print(f"IO Error reading file: {file_path}")
        return None


def process_season_stats(folder_path):
    """
    Process basketball statistics from multiple seasons (1999-2024) and calculate overall averages.
    
    Args:
        folder_path (str): Path to the folder containing the season data files
        attempt_counter_file (str): Path template for files containing attempt counts
        
    Returns:
        Tuple[Dict[str, float], Dict[str, float]]: Two dictionaries containing:
            1. Average minutes per player number across all seasons
            2. Average yearly statistics per player number across all seasons
    """
    minute_sums = {}
    minute_counts = {}
    yearly_sums = {}
    yearly_counts = {}
    
    # Process seasons from 1999-2000 to 2023-2024
    for year in range(1999, 2024):
        season = f"{year}-{year+1}"
        
        # Construct file paths
        minute_file = os.path.join(folder_path, f"minute_averages_{season}.txt")
        yearly_file = os.path.join(folder_path, f"yearly_averages_{season}.txt")
        attempts_file = os.path.join(folder_path, f"attempt_counter_{season}.txt")
        
        try:
            # Load attempts data for this year
            with open(attempts_file, 'r') as f:
                attempts_data = json.loads(f.read())
            
            # Process minute averages
            with open(minute_file, 'r') as f:
                minute_data = json.loads(f.read())
                for min, percentage in minute_data.items():
                    if min not in minute_sums:
                        minute_sums[min] = 0
                        minute_counts[min] = 0
                    minute_sums[min] += percentage
                    minute_counts[min] += 1
            
            # Process yearly averages
            with open(yearly_file, 'r') as f:
                yearly_data = json.loads(f.read())
                for yrmin, per in yearly_data.items():
                    if yrmin not in yearly_sums:
                        yearly_sums[yrmin] = 0
                        yearly_counts[yrmin] = 0
                    yearly_sums[yrmin] += per * attempts_data[yrmin] # Use attempts from file
                    yearly_counts[yrmin] += attempts_data[yrmin]
                    
        except FileNotFoundError:
            error_details = {
                "season": season,
                "error_type": "FileNotFoundError",
                "traceback": traceback.format_exc()
            }
            error_logger.log_error("FileNotFoundError", f"Could not find data files for season {season}", error_details)
            print(f"Warning: Could not find data files for season {season}")
            continue
        except json.JSONDecodeError as e:
            error_details = {
                "season": season,
                "error_type": "JSONDecodeError",
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            error_logger.log_error("JSONDecodeError", f"Invalid JSON format in files for season {season}", error_details)
            print(f"Warning: Invalid JSON format in files for season {season}")
            continue
    
    minute_avgs = {}
    yr_avgs = {}

    for minute in minute_sums:
        minute_avgs[minute] = minute_sums[minute] / minute_counts[minute]
    
    for min in yearly_sums:
        yr_avgs[min] = yearly_sums[min] / yearly_counts[min]
    
    return [minute_avgs, yr_avgs]

def main():
    # analyzer = FreeThrowAnalyzer()

    #now, for every team loop from 

    allTeams = {
        "ATLANTA HAWKS": Team.ATLANTA_HAWKS,
        "BOSTON CELTICS": Team.BOSTON_CELTICS,
        "BROOKLYN NETS": Team.BROOKLYN_NETS,
        "CHARLOTTE HORNETS": Team.CHARLOTTE_HORNETS,
        "CHICAGO BULLS": Team.CHICAGO_BULLS,
        "CLEVELAND CAVALIERS": Team.CLEVELAND_CAVALIERS,
        "DALLAS MAVERICKS": Team.DALLAS_MAVERICKS,
        "DENVER NUGGETS": Team.DENVER_NUGGETS,
        "DETROIT PISTONS": Team.DETROIT_PISTONS,
        "GOLDEN STATE WARRIORS": Team.GOLDEN_STATE_WARRIORS,
        "HOUSTON ROCKETS": Team.HOUSTON_ROCKETS,
        "INDIANA PACERS": Team.INDIANA_PACERS,
        "LOS ANGELES CLIPPERS": Team.LOS_ANGELES_CLIPPERS,
        "LOS ANGELES LAKERS": Team.LOS_ANGELES_LAKERS,
        "MEMPHIS GRIZZLIES": Team.MEMPHIS_GRIZZLIES,
        "MIAMI HEAT": Team.MIAMI_HEAT,
        "MILWAUKEE BUCKS": Team.MILWAUKEE_BUCKS,
        "MINNESOTA TIMBERWOLVES": Team.MINNESOTA_TIMBERWOLVES,
        "NEW ORLEANS PELICANS": Team.NEW_ORLEANS_PELICANS,
        "NEW YORK KNICKS": Team.NEW_YORK_KNICKS,
        "OKLAHOMA CITY THUNDER": Team.OKLAHOMA_CITY_THUNDER,
        "ORLANDO MAGIC": Team.ORLANDO_MAGIC,
        "PHILADELPHIA 76ERS": Team.PHILADELPHIA_76ERS,
        "PHOENIX SUNS": Team.PHOENIX_SUNS,
        "PORTLAND TRAIL BLAZERS": Team.PORTLAND_TRAIL_BLAZERS,
        "SACRAMENTO KINGS": Team.SACRAMENTO_KINGS,
        "SAN ANTONIO SPURS": Team.SAN_ANTONIO_SPURS,
        "TORONTO RAPTORS": Team.TORONTO_RAPTORS,
        "UTAH JAZZ": Team.UTAH_JAZZ,
        "WASHINGTON WIZARDS": Team.WASHINGTON_WIZARDS
    }

    # total_neg = 0
    # total_made = 0
    # total_attempted = 0

    # yrToNumberAttempted = dict()
    # ca be calculated adding up 

    #VITAL, only commented for a sec for testing
    # for year in range(2000, 2025):
    # for year in range(2023, 2025):

    #     attemptCounter = minToAttemptsClass()
    #     attempt_counter_file = os.path.join('dataForEachYear', f'attempt_counter_{year-1}-{year}.txt')
    #     # Check if both files already exist
    #     minute_averages_file = os.path.join('dataForEachYear', f'minute_averages_{year-1}-{year}.txt')
    #     yearly_averages_file = os.path.join('dataForEachYear', f'yearly_averages_{year-1}-{year}.txt')

    #     # minute_total_dict_file = f"all_minute_total_dict_file_{year-1}-{year}"
        
    #     #comment this out to produce new documents for minute and minute yearly avgs at minutes (or delete exisitng ones)
    #     # if os.path.exists(minute_averages_file) and os.path.exists(yearly_averages_file):
    #     #     print(f"Files for {year-1}-{year} already exist, skipping...")
    #     #     continue
            
    #     yearAnalyzer = FreeThrowAnalyzer()

    #     for team in allTeams:
    #         arrHomeDates = get_team_home_dates(team, year)
    #         print(f"Starting: {team}")
    #         print("homedates: " + str(arrHomeDates))

    #         for date in arrHomeDates:
    #             print("Team: " + str(team))
    #             print("Year: " + str(year))
    #             print("Date: " + date)
    #             curr_date = date.split("-")
    #             # print(str(curr_date))
    #             try:
    #                 yearAnalyzer.process_team_games(allTeams[team], curr_date[0], curr_date[1], curr_date[2], year, attemptCounter)
    #             except Exception as e:
    #                 timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
    #                 error_details = {
    #                     "team": str(allTeams[team]),
    #                     "date": f"{curr_date[0]}-{curr_date[1]}-{curr_date[2]}",
    #                     "year": year,
    #                     "timestamp": timestamp,
    #                     "traceback": traceback.format_exc()
    #                 }
                    
    #                 # Log to error logger
    #                 error_logger.log_error("ProcessTeamGamesError", str(e), error_details)
                    
    #                 # Maintain existing error logging to separate file
    #                 error_msg = f"""
    #                 Time: {timestamp}
    #                 Team: {allTeams[team]}
    #                 Date: {curr_date[0]}-{curr_date[1]}-{curr_date[2]}
    #                 Error: {str(e)}
    #                 Traceback: {traceback.format_exc()}
    #                 ----------------------------------------
    #                 """
                    
    #                 with open('playByPlayErrors2,PostStrError.txt', 'a') as f:
    #                     f.write(error_msg)
    #                     time.sleep(2.0) #for just this one we will sleep for longer to not get rate limited
    #                     continue
    #             print("processed game")
    #     print(f"Total neg at {year}: " + str(yearAnalyzer.total_negative_minutes))
    #     total_neg += yearAnalyzer.total_negative_minutes
    #     print(f"Totl made at {year}: " + str(yearAnalyzer.total_made))
    #     total_made += yearAnalyzer.total_made
    #     print(f"Total attempted at {year}: " + str(yearAnalyzer.total_attempted))
    #     # yrToNumberAttempted[year] = yearAnalyzer.total_attempted
    #     total_attempted += yearAnalyzer.total_attempted
    #     yearlyAnsArr = yearAnalyzer.calculateMinuteAndYearlyAverages()
    #     yearlyMinuteAveragesDict = yearlyAnsArr[0]
    #     yearlyMinuteYearlyAveragesDict = yearlyAnsArr[1]

    #     # Save dictionaries to sorted text files
    #     with open(minute_averages_file, 'w') as f:
    #         sorted_dict = dict(sorted(yearlyMinuteAveragesDict.items(), key=lambda x: float(x[0])))
    #         json.dump(sorted_dict, f, indent=4)

    #     with open(yearly_averages_file, 'w') as f:
    #         sorted_dict = dict(sorted(yearlyMinuteYearlyAveragesDict.items(), key=lambda x: float(x[0])))
    #         json.dump(sorted_dict, f, indent=4)

    #     with open(attempt_counter_file, 'w') as f:
    #         # Sort the dictionary by minutes (converting keys to float for numerical sorting)
    #         sorted_dict = dict(sorted(attemptCounter.minToAttempts.items(), key=lambda x: float(x[0])))
    #         json.dump(sorted_dict, f, indent=4)

    #     # with open(minute_total_dict_file, 'w') as f:
    #     #     json.dump(yearAnalyzer.minutes, f, indent=4, default=set_default)

    #     plot_ft_percentages(yearlyMinuteAveragesDict, yearlyMinuteYearlyAveragesDict, year-1, year, yearAnalyzer.total_made, yearAnalyzer.total_attempted)
    #     time.sleep(1.89)
    #     #stop after one year to check large
    #     # break







    
    #for 2023-24 season
    # analyzer.minutes = parse_data_file("/Users/eliyoung/Stat011Project/FatigueVSFreethrow/dictionary.txt")

    #this will print the dictionary
    # print("minutesDict: " + str(analyzer.minutes))

    # analyzer.minutes = {2: [1564, 435, {'T. Watford', 'B. Bol', 'J. Robinson-Earl', 'S. Aldama', 'P. Connaughton', 'J. Landale', 'A. Coffey', 'E. Mobley', 'D. Terry', 'A. Fudge', 'J. Isaac', 'D. Jordan', 'B. Williams', 'K. Durant', 'N. Jović', 'D. DeRozan', 'C. Braun', 'G. Bitadze', 'T. Jackson-Davis', 'P. George', 'D. Mitchell', 'G. Brown', 'Z. LaVine', 'M. Turner', 'I. Stewart', 'D. Bane', 'P. Banchero', 'D. Lillard', 'P. Watson', 'J. Cain', 'T. Haliburton', 'C. Thomas', 'K. Irving', 'P. Achiuwa', 'N. Little', 'J. Morant', 'M. Bagley', 'D. Schröder', 'T. Thompson', 'O. Toppin', 'D. Sabonis', 'J. Freeman-Liberty', 'F. Ntilikina', 'T. Lyles', 'I. Okoro', 'C. Wallace', 'D. Theis', 'K. Murray', 'Z. Nnaji', 'J. Allen', 'L. Waters', 'S. Milton', 'B. Miller', 'C. Martin', 'J. Poole', 'J. Grant', 'P. Beverley', 'A. Pokusevski', 'J. Sims', 'C. Metu', 'T. Camara', 'D. Green', 'O. Prosper', 'D. Barlow', 'O. Robinson', 'B. Wesley', 'H. Barnes', 'R. Hachimura', 'T. Eason', 'J. Sochan', 'S. Barnes', 'C. LeVert', 'J. Murray', 'R. Jackson', 'T. Vukcevic', 'S. Sharpe', 'J. Crowder', 'T. Craig', 'Z. Williams', 'J. Nwora', 'D. Rose', 'J. Tatum', 'J. Collins', 'D. Roddy', 'I. Jackson', 'L. Walker', 'M. Moody', 'K. Thompson', 'A. Nembhard', 'J. Konchar', 'J. McGee', 'D. Exum', 'C. Joseph', 'C. Cunningham', 'K. Towns', 'J. Robinson', 'V. Williams', 'E. Fournier', 'J. Alvarado', 'A. Black', 'T. Maxey', 'J. Jaquez', 'B. Mathurin', 'A. Thompson', 'M. Beauchamp', 'D. Brooks', 'B. Boston', 'L. Shamet', 'D. Šarić', 'D. Booker', 'S. Lee', 'J. Nowell', 'T. Harris', 'Z. Collins', 'J. Ramsey', 'J. Jackson', 'K. Leonard', 'D. Powell', 'D. Avdija', 'V. Wembanyama', 'R. Holmes', 'M. Williams', 'N. Vučević', 'I. Joe', 'L. James', 'R. Council', 'G. Niang', 'S. Henderson', 'K. George', 'T. Hardaway', 'D. DiVincenzo', 'O. Yurtseven', 'A. Wiggins', 'B. Ingram', 'U. Garuba', 'O. Anunoby', 'I. Quickley', 'K. Hayes', 'D. Hunter', 'P. Washington', 'C. Gillespie', 'D. Jarreau', 'J. Embiid', 'B. Portis', 'C. Anthony', 'G. Hayward', 'T. Jones', 'J. Rhoden', 'Z. Williamson', 'G. Dick', 'D. Banton', 'J. Bernard', 'J. Poeltl', 'I. Zubac', 'P. Reed', 'M. Branham', 'A. Drummond', 'T. Brown', 'L. Markkanen', 'M. Wagner', 'O. Agbaji', 'M. Sasser', 'D. Vassell', 'Y. Watanabe', 'F. Korkmaz', 'D. Garland', 'S. Bey', 'D. Gallinari', 'D. White', 'C. Paul', 'G. Jackson', 'M. Morris', 'C. Sexton', 'K. Martin', 'M. Flynn', 'T. Rozier', 'M. Robinson', 'M. Kleber', 'N. Powell', 'I. Hartenstein', 'B. Bogdanović', 'C. McCollum', 'B. Sensabaugh', 'J. Randle', 'R. Williams', 'S. Pippen ', 'J. Davis', 'N. Batum', 'J. Clarkson', 'G. Mathews', 'C. Capela', 'C. Livingston', 'O. Sarr', 'C. Porter', 'K. Johnson', 'E. Omoruyi', 'O. Okongwu', 'L. Stevens', 'S. Mays', 'T. Herro', 'J. Green', 'S. Gilgeous-Alexander', 'C. Reddish', 'N. Richards', 'J. Giddey', 'B. Brown', 'J. Vanderbilt', 'J. Valančiūnas', 'N. Alexander-Walker', 'D. Gafford', 'K. Lofton', 'B. Hyland', 'J. Johnson', 'U. Azubuike', 'D. Lively', 'G. Harris', 'K. Oubre', 'M. Fultz', 'B. Lopez', 'S. Mamukelashvili', 'M. McBride', 'T. McConnell', 'O. Brissett', 'S. Cissoko', 'B. Coulibaly', 'J. Walker', 'A. Sengun', 'R. Barrett', 'M. Diabaté', 'K. Caldwell-Pope', 'N. Clowney', 'L. Garza', 'I. Badji', 'T. Young', 'E. Gordon', 'J. Okogie', 'D. Reath', 'P. Pritchard', 'D. Sharpe', 'J. Ingles', 'M. Monk', 'N. Reid', 'B. Biyombo', 'M. Bridges', 'N. Marshall', 'K. Olynyk', 'D. Daniels', 'J. Nurkić', 'G. Williams', 'J. Ivey', 'J. Wiseman', 'A. Dosunmu', 'C. White', 'L. Nance', 'J. Butler', 'G. Allen', 'G. Antetokounmpo', 'K. Middleton', 'L. Ball', 'M. Brogdon', 'J. Tate', 'A. Burks', 'D. Russell', 'P. Siakam', 'C. Zeller', 'C. Holmgren', 'C. Swider', 'D. Melton', 'M. Diakite', 'B. Marjanović', 'J. Wilson', 'A. Gill', 'R. Gobert', 'M. Plumlee', 'K. Huerter', 'F. Wagner', 'J. Hawkins', 'J. Harden', 'A. Green', 'C. Osman', 'W. Carter', 'J. Hayes', 'B. Adebayo', 'J. Suggs', 'T. Hendricks', 'J. Juzang', 'J. LaRavia', 'A. Reaves', 'M. Christie', 'L. Kornet', 'T. Smith', 'J. Strawther', 'K. Porziņģis', 'K. Knox', 'A. Lawson', 'B. Key', 'K. Anderson', 'J. Minott', 'M. Strus', 'C. Kispert', 'S. Merrill', 'S. Dinwiddie', 'C. Johnson', 'D. Nix', 'C. Duarte', 'D. Wright', 'D. Fox', 'D. Dennis', 'T. Murphy', 'M. Bamba', 'A. Len', 'C. Whitmore', 'J. Brown', 'S. Curry', 'J. McDaniels', 'F. VanVleet', 'R. Lopez', 'D. Eubanks', 'T. Horton-Tucker', 'J. Kuminga', 'J. Thor', 'D. Smith', 'J. Smith', 'T. Mann', 'J. Brunson', 'R. Rupert', 'V. Micić', 'M. Porter', 'B. Podziemski', 'M. Conley', 'L. Miller', 'C. Boucher', 'K. Love', 'C. Okeke', 'D. Robinson', 'A. Davis', 'N. Jokić', 'G. Trent', 'A. Edwards', 'J. Duren', 'W. Matthews', 'A. Gordon', 'K. Bates-Diop', 'N. Claxton', 'R. Westbrook', 'C. Wood', 'J. Williams', 'D. Jones', 'D. Jeffries', 'B. McGowens', 'B. Fernando', 'D. Bertāns', 'L. Black', 'L. Dončić', 'J. Hardy', 'S. Lundy', 'K. Kuzma'}], 3: [1589, 423, {'T. Watford', 'B. Bol', 'J. Robinson-Earl', 'P. Connaughton', 'J. Landale', 'A. Sanogo', 'A. Coffey', 'D. Terry', 'E. Mobley', 'J. Isaac', 'D. Jordan', 'B. Williams', 'I. Livers', 'K. Durant', 'N. Jović', 'D. DeRozan', 'C. Braun', 'G. Bitadze', 'T. Jackson-Davis', 'P. George', 'D. Mitchell', 'Z. LaVine', 'M. Turner', 'I. Stewart', 'S. Umude', 'D. Bane', 'P. Banchero', 'H. Giles', 'D. Lillard', 'P. Watson', 'T. Haliburton', 'C. Thomas', 'K. Irving', 'P. Achiuwa', 'M. Bagley', 'D. Schröder', 'R. Rollins', 'J. Holiday', 'F. Petrušev', 'O. Toppin', 'D. Sabonis', 'T. Lyles', 'I. Okoro', 'L. Dort', 'J. Goodwin', 'C. Wallace', 'D. Theis', 'K. Murray', 'Z. Nnaji', 'J. Allen', 'B. Miller', 'C. Martin', 'J. Poole', 'J. Grant', 'P. Beverley', 'O. Tshiebwe', 'A. Pokusevski', 'J. Sims', 'C. Metu', 'O. Prosper', 'D. Barlow', 'O. Robinson', 'B. Wesley', 'R. Hachimura', 'T. Eason', 'J. Sochan', 'C. LeVert', 'J. Murray', 'R. Jackson', 'S. Sharpe', 'J. Richardson', 'T. Craig', 'B. Beal', 'J. Nwora', 'T. Warren', 'J. Tatum', 'J. Collins', 'D. Roddy', 'D. Murray', 'L. Walker', 'M. Moody', 'I. Jackson', 'K. Thompson', 'A. Nembhard', 'J. McGee', 'D. Exum', 'P. Baldwin', 'K. Towns', 'J. Robinson', 'V. Williams', 'E. Fournier', 'J. Alvarado', 'T. Maxey', 'J. Jaquez', 'K. Ellis', 'B. Mathurin', 'A. Thompson', 'M. Beauchamp', 'D. Brooks', 'B. Boston', 'D. Šarić', 'D. Booker', 'L. Shamet', 'J. Hart', 'T. Harris', 'Z. Collins', 'J. Ramsey', 'J. Jackson', 'K. Leonard', 'D. Powell', 'D. Avdija', 'V. Wembanyama', 'R. Holmes', 'M. Williams', 'N. Vučević', 'I. Joe', 'L. James', 'R. Council', 'S. Henderson', 'K. George', 'M. Nowell', 'T. Hardaway', 'D. DiVincenzo', 'O. Yurtseven', 'A. Wiggins', 'B. Ingram', 'I. Quickley', 'D. Hunter', 'P. Washington', 'P. Mills', 'D. Jarreau', 'J. Embiid', 'B. Portis', 'C. Anthony', 'G. Hayward', 'T. Jones', 'Z. Williamson', 'G. Dick', 'A. Simons', 'D. Banton', 'J. Poeltl', 'I. Zubac', 'P. Reed', 'M. Branham', 'A. Drummond', 'T. Brown', 'L. Markkanen', 'M. Wagner', 'O. Agbaji', 'M. Sasser', 'F. Korkmaz', 'N. Queta', 'S. Bey', 'D. Gallinari', 'D. White', 'C. Paul', 'G. Jackson', 'M. Morris', 'J. Springer', 'C. Sexton', 'W. Kessler', 'K. Martin', 'M. Flynn', 'M. Kleber', 'N. Powell', 'I. Hartenstein', 'B. Bogdanović', 'C. McCollum', 'B. Sensabaugh', 'A. Nesmith', 'J. Randle', 'H. Highsmith', 'R. Williams', 'S. Pippen ', 'J. Davis', 'J. Clarkson', 'G. Mathews', 'T. Prince', 'C. Capela', 'C. Livingston', 'O. Sarr', 'C. Porter', 'K. Johnson', 'E. Omoruyi', 'S. Hauser', 'O. Okongwu', 'S. Mays', 'L. Stevens', 'K. Dunn', 'T. Herro', 'J. Green', 'S. Gilgeous-Alexander', 'J. McLaughlin', 'J. Hood-Schifino', 'N. Richards', 'B. Brown', 'C. Payne', 'D. McDermott', 'J. Valančiūnas', 'N. Alexander-Walker', 'D. Gafford', 'K. Lofton', 'J. Johnson', 'U. Azubuike', 'D. Lively', 'K. Oubre', 'M. Fultz', 'S. Mamukelashvili', 'M. McBride', 'T. McConnell', 'O. Brissett', 'S. Fontecchio', 'O. Dieng', 'S. Cissoko', 'B. Coulibaly', 'J. Walker', 'A. Sengun', 'R. Barrett', 'D. House', 'K. Caldwell-Pope', 'L. Garza', 'I. Badji', 'T. Forrest', 'T. Young', 'E. Gordon', 'J. Okogie', 'D. Reath', 'N. Hinton', 'P. Pritchard', 'D. Sharpe', 'J. Ingles', 'M. Monk', 'N. Reid', 'M. Bridges', 'C. Castleton', 'N. Marshall', 'K. Olynyk', 'J. Nurkić', 'G. Williams', 'J. Ivey', 'J. Wiseman', 'A. Dosunmu', 'C. White', 'L. Nance', 'J. Butler', 'G. Allen', 'G. Antetokounmpo', 'K. Middleton', 'L. Ball', 'M. Brogdon', 'J. Tate', 'L. Kennard', 'A. Burks', 'D. Russell', 'P. Siakam', 'C. Holmgren', 'B. Marjanović', 'G. Temple', 'J. Phillips', 'B. Sheppard', "R. O'Neale", 'A. Gill', 'M. Plumlee', 'R. Gobert', 'T. Bryant', 'J. Porter', 'F. Wagner', 'J. Hawkins', 'J. Harden', 'A. Green', 'C. Osman', 'W. Carter', 'J. Hayes', 'B. Adebayo', 'J. Suggs', 'T. Hendricks', 'J. Juzang', 'J. LaRavia', 'A. Reaves', 'M. Christie', 'L. Kornet', 'M. Muscala', 'J. Strawther', 'K. Lewis', 'K. Porziņģis', 'L. Šamanić', 'K. Anderson', 'A. Horford', 'A. Holiday', 'A. Hagans', 'C. Kispert', 'S. Merrill', 'S. Dinwiddie', 'C. Johnson', 'C. Duarte', 'D. Wright', 'D. Fox', 'D. Dennis', 'T. Murphy', 'M. Bamba', 'C. Whitmore', 'J. Brown', 'S. Curry', 'J. McDaniels', 'J. Champagnie', 'D. Eubanks', 'T. Horton-Tucker', 'J. Kuminga', 'J. Thor', 'D. Smith', 'J. Smith', 'B. Boeheim', 'I. Wainright', 'T. Mann', 'J. Brunson', 'V. Micić', 'M. Porter', 'B. Podziemski', 'M. Pereira', 'C. Boucher', 'K. Love', 'D. Robinson', 'A. Davis', 'A. Caruso', 'N. Jokić', 'G. Trent', 'A. Edwards', 'J. Duren', 'W. Matthews', 'A. Gordon', 'M. Smart', 'K. Bates-Diop', 'N. Claxton', 'R. Westbrook', 'C. Wood', 'J. Williams', 'D. Jones', 'B. McGowens', 'B. Fernando', 'L. Black', 'G. Santos', 'L. Dončić', 'C. Houstan', 'J. Hardy', 'S. Lundy', 'K. Looney', 'K. Kuzma'}]}
    results = process_season_stats("./dataForEachYear")
    
    minute_averages = results[0]
    yearly_averages = results[1]
    
    all_minute_averages_file = f'all_minute_averages_2000-2024.txt'
    all_yearly_averages_file = f'all_yearly_averages_2000-2024.txt'

    with open(all_minute_averages_file, 'w') as f:
        sorted_dict = dict(sorted(minute_averages.items(), key=lambda x: float(x[0])))
        json.dump(sorted_dict, f, indent=4)
            
    with open(all_yearly_averages_file, 'w') as f:
        sorted_dict = dict(sorted(yearly_averages.items(), key=lambda x: float(x[0])))
        json.dump(sorted_dict, f, indent=4)

    # # This will convert each set() in the lists to a list while preserving the structure
    # with open(all_minute_total_dict_file, 'w') as f:
    #     json.dump(analyzer.minutes, f, indent=4, default=set_default)


    #if need to convert back to set:
    # with open(all_minute_total_dict_file, 'r') as f:
    # loaded_minutes = json.load(f)
    # # Convert the third element back to a set
    # minutes = {k: [v[0], v[1], set(v[2])] for k, v in loaded_minutes.items()}

    # print("minuteAvg: " + str(minuteAveragesDict)) #empty for some reason?

    # print("minuteYearlyAvg: " + str(minuteYearlyAveragesDict)) #empty for some reason?

    # print("Total neg from 2000-2024: " + str(analyzer.total_negative_minutes))
    # print("Total made from 2000-2024:" + str(analyzer.total_made))
    # print("Total made from 2000-2024" + str(analyzer.total_attempted))

    print()

    plot_ft_percentages(minute_averages, yearly_averages, 2000, 2024, totalMade=1087740, totalAttempted=1429733)

    exit()

if __name__ == '__main__':
    main()