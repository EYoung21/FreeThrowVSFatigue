# do for wnba after?
#adjust for intentional misses at end of games somehow (or just drowned out by noise?)
#fix issue where error number for play by play parsing

import csv
from basketball_reference_web_scraper import client
import time
import requests
from basketball_reference_web_scraper.data import Team, OutputType, Location
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple
import math
import matplotlib.pyplot as plt
import numpy as np
import pytz
import pandas as pd
from bs4 import BeautifulSoup
import ast
import os
from nba_api.stats.static import players
from nba_api.stats.endpoints import commonplayerinfo
import traceback
import json
from scipy import stats
from collections import defaultdict

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

error_logger = ErrorLogger("SpecificPlayerVersionErrors.txt")

class playerToMinToAttemptsClass:
    def __init__(self):
        self.playerToMinToAttempts = defaultdict(lambda: defaultdict(int)) #cause its a defaultdict mapping mins to attempts at that minute

class FreeThrowAnalyzer:
    def __init__(self):
        self.playerMinutes = defaultdict(lambda: defaultdict([]))
        self.error_logger = ErrorLogger("SpecificPlayerVersionErrors.txt")
        
        # Use defaultdict to automatically initialize counters for new players
        self.playerToTotalAttempted = defaultdict(int)
        self.playerToTotalMade = defaultdict(int)
        self.playerToSeasonAvg = dict()

            
    def process_team_games(self, team: Team, year: int, month: int, day: int, seasonYear, attemptCounter, best_ft_shooters, worst_ft_shooters, bestworst):
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
            self._process_game_data(pbp_data, team, year, month, day, seasonYear, attemptCounter, best_ft_shooters, worst_ft_shooters, bestworst) #passing year so I can print it
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
                        self._process_game_data(pbp_data, team, year, month, day, seasonYear, attemptCounter, best_ft_shooters, worst_ft_shooters, bestworst)
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
                        self._process_game_data(pbp_data, team, year, month, day, seasonYear, attemptCounter, best_ft_shooters, worst_ft_shooters, bestworst)
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
    
    def _process_game_data(self, pbp_data: List[dict], team, year, month, day, seasonYear, attemptCounter, best_ft_shooters, worst_ft_shooters, bestworst):
        player_entry_times = {}
        playersThatSubbedOut = set()

        for play in pbp_data:
            if 'enters' in str(play.get('description', '')):
                desParsed = play['description'].split(' enters')
                player_in = desParsed[0]
                desParsed2 = desParsed[1].split('for ')
                player_out = desParsed2[1]

                if player_in not in bestworst and player_out not in bestworst:
                    continue

                if player_in in bestworst:
                    converted_time = self.calculateConvertedIGT(
                        play.get('remaining_seconds_in_period'),
                        play.get('period'),
                        play.get('period_type')
                    )
                    player_entry_times[player_in] = converted_time
                
                if player_out in bestworst:
                    playersThatSubbedOut.add(player_out)

            if 'free throw' in str(play.get('description', '')):
                if 'makes' in play['description']:
                    player = play['description'].split(' makes')[0]
                    if player not in bestworst or player in playersThatSubbedOut:
                        continue
                    self.playerToTotalMade[player] += 1
                    self.playerToTotalAttempted[player] += 1
                elif 'misses' in play['description']:
                    player = play['description'].split(' misses')[0]
                    if player not in bestworst or player in playersThatSubbedOut:
                        continue
                    self.playerToTotalAttempted[player] += 1

                if player not in player_entry_times:
                    player_entry_times[player] = 0.0

                entry_time = player_entry_times.get(player)
                current_time = self.calculateConvertedIGT(
                    play.get('remaining_seconds_in_period'),
                    play.get('period'),
                    play.get('period_type')
                )

                seconds_played = current_time - entry_time
                minutes_played = seconds_played / 60

                if minutes_played < 0:
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
                        f.write(debug_string)
                    continue

                curr_minute = int(math.floor(minutes_played))

                if player not in self.playerToSeasonAvg:
                    ft_pct = self.get_player_ft_pct(player, seasonYear)
                    if ft_pct and ft_pct != "No free throws":
                        self.playerToSeasonAvg[player] = ft_pct[0]/ft_pct[1] * 100

                if player not in self.playerMinutes:
                    self.playerMinutes[player] = defaultdict(lambda: [0, 0])

                if 'makes' in play['description']:
                    self.playerMinutes[player][curr_minute][0] += 1
                    attemptCounter.playerToMinToAttempts[player][curr_minute] += 1
                else:
                    self.playerMinutes[player][curr_minute][1] += 1
                    attemptCounter.playerToMinToAttempts[player][curr_minute] += 1
    
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

        for minute in self.playerMinutes:
            
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

def plot_ft_percentages(minute_averages, yearly_averages, startYear, endYear, totalMade, totalAttempted):
    if not os.path.exists('dataForEachYear'):
        os.makedirs('dataForEachYear')

    # Convert and sort minutes, ensuring integer keys
    minutes = sorted([float(k) for k in minute_averages.keys()])
    ft_percentages = [minute_averages[str(int(m)) if m.is_integer() else str(m)] for m in minutes]
    yearly_percentages = [yearly_averages[str(int(m)) if m.is_integer() else str(m)] for m in minutes]
    differences = [ft_percentages[i] - yearly_percentages[i] for i in range(len(minutes))]

    # Rest of the function remains the same
    diff_df = pd.DataFrame({
        'Minute': minutes,
        'Difference': differences
    })
    diff_df.to_csv(os.path.join('dataForEachYear', f'difference_averages_{startYear}-{endYear}.txt'), index=False)

    slope, intercept, r_value, p_value, std_err = stats.linregress(ft_percentages, yearly_percentages)

    with open(f'{startYear}-{endYear}_regression_stats.txt', 'w') as f:
        f.write(f"Analysis for {startYear}-{endYear} NBA Seasons\n")
        f.write("="*40 + "\n\n")
        f.write("Linear Regression Between Minute FT% and Yearly FT%:\n")
        f.write(f"  Slope: {slope:.4f}\n")
        f.write(f"  Intercept: {intercept:.4f}\n")
        f.write(f"  R-squared: {r_value**2:.4f}\n")
        f.write(f"  P-value: {p_value:.4e}\n")
        f.write(f"  Standard Error: {std_err:.4f}\n")

    regression_line = slope * np.array(ft_percentages) + intercept

    regression_df = pd.DataFrame({
        'Minute_FT%': ft_percentages,
        'Yearly_FT%': yearly_percentages,
        'Regression_Predicted': regression_line
    })
    regression_df.to_csv(f'{startYear}-{endYear}_regression_analysis.csv', index=False)

    df = pd.DataFrame({
        'Minute': minutes,
        'Minute_Average_FT%': ft_percentages,
        'Season_Average_FT%': yearly_percentages,
        'Difference': differences
    })
    df.to_csv(f'{startYear}-{endYear}_ft_percentage_data.csv', index=False)

    slope_ft, intercept_ft, r_value_ft, p_value_ft, std_err_ft = stats.linregress(minutes, ft_percentages)
    line_ft = slope_ft * np.array(minutes) + intercept_ft

    slope_yearly, intercept_yearly, r_value_yearly, p_value_yearly, std_err_yearly = stats.linregress(minutes, yearly_percentages)
    line_yearly = slope_yearly * np.array(minutes) + intercept_yearly

    slope_diff, intercept_diff, r_value_diff, p_value_diff, std_err_diff = stats.linregress(minutes, differences)
    line_diff = slope_diff * np.array(minutes) + intercept_diff

    plt.figure(figsize=(6, 6))
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

    plt.figure(figsize=(12, 8))
    plt.plot(minutes, ft_percentages, 'b-', label='Actual FT% at minute', linewidth=2)
    plt.plot(minutes, yearly_percentages, 'g-', label='Players\' Season Average', linewidth=2)
    plt.plot(minutes, differences, 'r-', label='Difference', linewidth=2)
    plt.plot(minutes, line_ft, 'b:', label=f'FT% Trend (slope: {slope_ft:.4f})', linewidth=1)
    plt.plot(minutes, line_yearly, 'g:', label=f'Season Avg Trend (slope: {slope_yearly:.4f})', linewidth=1)
    plt.plot(minutes, line_diff, 'r:', label=f'Difference Trend (slope: {slope_diff:.4f})', linewidth=1)

    stats_text = f'Regression Statistics:\nSlope: {slope:.4f}\nIntercept: {intercept:.4f}\nR²: {r_value**2:.4f}'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
            verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))

    percentage = round(totalMade/totalAttempted * 100, 2) if totalAttempted > 0 else ""
    plt.title(f'Free Throw Percentage by Minutes Played for {startYear}-{endYear} Season\nFTA: {totalAttempted}, FTs Made: {totalMade}, %: {percentage}%', 
              fontsize=14, pad=20)
    plt.xlabel('Minutes Played', fontsize=12)
    plt.ylabel('Free Throw Percentage', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.axhline(y=0, color='k', linestyle='-', alpha=0.1)
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1f}%'.format(y)))
    plt.tight_layout()
    plt.savefig(f'{startYear}-{endYear}_ft_percentage_analysis.png', bbox_inches='tight', dpi=300)


# def process_season_stats(folder_path):
#     """
#     Process basketball statistics from multiple seasons (1999-2024) and calculate overall averages.
    
#     Args:
#         folder_path (str): Path to the folder containing the season data files
#         attempt_counter_file (str): Path template for files containing attempt counts
        
#     Returns:
#         Tuple[Dict[str, float], Dict[str, float]]: Two dictionaries containing:
#             1. Average minutes per player number across all seasons
#             2. Average yearly statistics per player number across all seasons
#     """
#     minute_sums = {}
#     minute_counts = {}
#     yearly_sums = {}
#     yearly_counts = {}
    
#     # Process seasons from 1999-2000 to 2023-2024
#     for year in range(1999, 2024):
#         season = f"{year}-{year+1}"
        
#         # Construct file paths
#         minute_file = os.path.join(folder_path, f"minute_averages_{season}.txt")
#         yearly_file = os.path.join(folder_path, f"yearly_averages_{season}.txt")
#         attempts_file = os.path.join(folder_path, f"attempt_counter_{season}.txt")
        
#         try:
#             # Load attempts data for this year
#             with open(attempts_file, 'r') as f:
#                 attempts_data = json.loads(f.read())
            
#             # Process minute averages
#             with open(minute_file, 'r') as f:
#                 minute_data = json.loads(f.read())
#                 for min, percentage in minute_data.items():
#                     if min not in minute_sums:
#                         minute_sums[min] = 0
#                         minute_counts[min] = 0
#                     minute_sums[min] += percentage
#                     minute_counts[min] += 1
            
#             # Process yearly averages
#             with open(yearly_file, 'r') as f:
#                 yearly_data = json.loads(f.read())
#                 for yrmin, per in yearly_data.items():
#                     if yrmin not in yearly_sums:
#                         yearly_sums[yrmin] = 0
#                         yearly_counts[yrmin] = 0
#                     yearly_sums[yrmin] += per * attempts_data[yrmin] # Use attempts from file
#                     yearly_counts[yrmin] += attempts_data[yrmin]
                    
#         except FileNotFoundError:
#             error_details = {
#                 "season": season,
#                 "error_type": "FileNotFoundError",
#                 "traceback": traceback.format_exc()
#             }
#             error_logger.log_error("FileNotFoundError", f"Could not find data files for season {season}", error_details)
#             print(f"Warning: Could not find data files for season {season}")
#             continue
#         except json.JSONDecodeError as e:
#             error_details = {
#                 "season": season,
#                 "error_type": "JSONDecodeError",
#                 "error_message": str(e),
#                 "traceback": traceback.format_exc()
#             }
#             error_logger.log_error("JSONDecodeError", f"Invalid JSON format in files for season {season}", error_details)
#             print(f"Warning: Invalid JSON format in files for season {season}")
#             continue
    
#     minute_avgs = {}
#     yr_avgs = {}

#     for minute in minute_sums:
#         minute_avgs[minute] = minute_sums[minute] / minute_counts[minute]
    
#     for min in yearly_sums:
#         yr_avgs[min] = yearly_sums[min] / yearly_counts[min]
    
#     return [minute_avgs, yr_avgs]



def create_player_career_graphs(player_list, data_dir="dataForEachPlayerYear", output_dir="ft_analysis_graphs"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    player_career_minutes = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    player_career_attempts = defaultdict(lambda: defaultdict(int))
    player_season_data = defaultdict(lambda: defaultdict(dict))
    
    for year in range(2000, 2025):
        season = f"{year-1}-{year}"
        try:
            # Load and convert data
            with open(os.path.join(data_dir, f'player_minute_averages_{season}.txt'), 'r') as f:
                minute_data = json.load(f)
                minute_data = {player: {float(k): v for k, v in minutes.items()} 
                             for player, minutes in minute_data.items()}
            
            with open(os.path.join(data_dir, f'yearly_averages_{season}.txt'), 'r') as f:
                season_avgs = json.load(f)
            
            with open(os.path.join(data_dir, f'player_attempt_counter_{season}.txt'), 'r') as f:
                attempt_data = json.load(f)
                attempt_data = {player: {float(k): v for k, v in attempts.items()}
                              for player, attempts in attempt_data.items()}
            
            # Aggregate data per player
            for player in player_list:
                if player in minute_data and player in season_avgs and player in attempt_data:
                    player_season_data[player][year] = {
                        'minute_data': minute_data[player],
                        'attempts': attempt_data[player],
                        'season_avg': season_avgs[player]
                    }
                    
                    for minute, data in minute_data[player].items():
                        attempts = attempt_data[player][minute]
                        makes = int(data[0])
                        player_career_minutes[player][minute][0] += makes
                        player_career_minutes[player][minute][1] += attempts - makes
                        player_career_attempts[player][minute] += attempts
                        
        except FileNotFoundError:
            print(f"Missing data files for season {season}")
            continue

    for player in player_list:
        if player in player_career_minutes:
            total_makes = sum(data[0] for data in player_career_minutes[player].values())
            total_attempts = sum(player_career_attempts[player].values())
            career_pct = (total_makes / total_attempts * 100) if total_attempts > 0 else 0
            
            minutes = sorted(player_career_minutes[player].keys())
            percentages = []
            baseline = []
            attempts = []
            
            for m in minutes:
                attempts_at_min = player_career_attempts[player][m]
                makes = player_career_minutes[player][m][0]
                
                if attempts_at_min > 0:
                    # Calculate actual percentage
                    percentages.append(makes / attempts_at_min * 100)
                    attempts.append(attempts_at_min)
                    
                    # Calculate weighted baseline for this minute
                    weighted_baseline = 0
                    total_weights = 0
                    for year_data in player_season_data[player].values():
                        if m in year_data['attempts']:
                            weight = year_data['attempts'][m]
                            weighted_baseline += year_data['season_avg'] * weight
                            total_weights += weight
                    
                    baseline.append(weighted_baseline / total_weights if total_weights > 0 else career_pct)
            
            differences = [p - b for p, b in zip(percentages, baseline)]
            # Calculate trend lines
            slope_ft, intercept_ft, r_value_ft, p_value_ft, std_err_ft = stats.linregress(minutes, percentages)
            slope_diff, intercept_diff, r_value_diff, p_value_diff, std_err_diff = stats.linregress(minutes, differences)
            
            trend_ft = slope_ft * np.array(minutes) + intercept_ft
            trend_diff = slope_diff * np.array(minutes) + intercept_diff
            
            # Calculate regression between actual and baseline
            slope_reg, intercept_reg, r_value_reg, p_value_reg, std_err_reg = stats.linregress(percentages, baseline)
            regression_line = slope_reg * np.array(percentages) + intercept_reg
            
            # Create timeline plot
            plt.figure(figsize=(12, 8))
            
            plt.plot(minutes, percentages, 'b-', label='FT% at minute', linewidth=2)
            plt.plot(minutes, baseline, 'r--', label=f'Career Average: {career_pct:.1f}%', linewidth=2)
            plt.plot(minutes, differences, 'g-', label='Difference', linewidth=2)
            
            plt.plot(minutes, trend_ft, 'b:', label=f'FT% Trend (slope: {slope_ft:.4f})', linewidth=1)
            plt.plot(minutes, trend_diff, 'g:', label=f'Difference Trend (slope: {slope_diff:.4f})', linewidth=1)
            
            stats_text = (f'Career Stats:\nFTA: {total_attempts:,}\n'
                         f'FTM: {total_makes:,}\nFT%: {career_pct:.1f}%\n\n'
                         f'Trends:\nFT% Slope: {slope_ft:.4f}\n'
                         f'Diff Slope: {slope_diff:.4f}')
            plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
                    verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))
            
            plt.title(f'{player} Career Free Throws\n'
                     f'FTA: {total_attempts:,}, FTM: {total_makes:,}, FT%: {career_pct:.1f}%')
            plt.xlabel('Minutes into Game')
            plt.ylabel('Free Throw Percentage')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.legend(fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1f}%'.format(y)))
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f'{player.replace(" ", "_")}_career_timeline.png'),
                       bbox_inches='tight', dpi=300)
            plt.close()
            
            # Create regression scatter plot
            plt.figure(figsize=(8, 8))
            plt.scatter(percentages, baseline, color='blue', alpha=0.5)
            plt.plot(percentages, regression_line, 'm--', 
                    label=f'Regression (R²: {r_value_reg**2:.4f})', linewidth=2)
            
            plt.title(f'{player} - Regression: Actual vs Career Average\n'
                     f'FTA: {total_attempts:,}, FTM: {total_makes:,}, FT%: {career_pct:.1f}%')
            plt.xlabel('Actual FT%', fontsize=12)
            plt.ylabel('Career Average FT%', fontsize=12)
            plt.grid(True, linestyle='--', alpha=0.7)
            
            regression_stats = (f'Regression Statistics:\n'
                              f'Slope: {slope_reg:.4f}\n'
                              f'Intercept: {intercept_reg:.4f}\n'
                              f'R²: {r_value_reg**2:.4f}')
            plt.text(0.02, 0.98, regression_stats, transform=plt.gca().transAxes,
                    verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))
            
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f'{player.replace(" ", "_")}_regression.png'),
                       bbox_inches='tight', dpi=300)
            plt.close()
            
            # Save data to CSV
            df = pd.DataFrame({
                'Minute': minutes,
                'FT_Percentage': percentages,
                'Baseline': baseline,
                'Difference': differences,
                'Attempts': attempts,
                'FT_Trend': trend_ft,
                'Difference_Trend': trend_diff,
                'Regression_Line': regression_line
            })
            df.to_csv(os.path.join(output_dir, f'{player.replace(" ", "_")}_data.csv'), index=False)

def create_group_graph(players, group_name, data_dir="dataForEachPlayerYear", output_dir="ft_analysis_graphs"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    group_season_data = defaultdict(lambda: defaultdict(dict))
    group_minutes = defaultdict(lambda: [0, 0])  # [makes, attempts]
    
    for year in range(2000, 2025):
        season = f"{year-1}-{year}"
        try:
            with open(os.path.join(data_dir, f'player_minute_averages_{season}.txt'), 'r') as f:
                minute_data = json.load(f)
                minute_data = {player: {float(k): v for k, v in minutes.items()} 
                             for player, minutes in minute_data.items()}
            
            with open(os.path.join(data_dir, f'yearly_averages_{season}.txt'), 'r') as f:
                season_avgs = json.load(f)
            
            with open(os.path.join(data_dir, f'player_attempt_counter_{season}.txt'), 'r') as f:
                attempt_data = json.load(f)
                attempt_data = {player: {float(k): v for k, v in attempts.items()}
                              for player, attempts in attempt_data.items()}
            
            for player in players:
                if player in minute_data and player in season_avgs and player in attempt_data:
                    group_season_data[year][player] = {
                        'minute_data': minute_data[player],
                        'attempts': attempt_data[player],
                        'season_avg': season_avgs[player]
                    }
                    
                    for minute, data in minute_data[player].items():
                        attempts = attempt_data[player][minute]
                        makes = int(data[0])
                        group_minutes[minute][0] += makes
                        group_minutes[minute][1] += attempts
                        
        except FileNotFoundError:
            print(f"Missing data files for season {season}")
            continue
    
    minutes = sorted(group_minutes.keys())
    percentages = []
    baseline = []
    attempts = []
    
    total_makes = sum(data[0] for data in group_minutes.values())
    total_attempts = sum(data[1] for data in group_minutes.values())
    group_pct = (total_makes / total_attempts * 100) if total_attempts > 0 else 0
    
    for m in minutes:
        total_attempts_at_min = group_minutes[m][1]
        if total_attempts_at_min > 0:
            percentages.append(group_minutes[m][0] / total_attempts_at_min * 100)
            attempts.append(total_attempts_at_min)
            
            weighted_baseline = 0
            total_weights = 0
            for season_data in group_season_data.values():
                for player, player_data in season_data.items():
                    if m in player_data['attempts']:
                        weight = player_data['attempts'][m]
                        season_ft_pct = player_data['season_avg']
                        weighted_baseline += season_ft_pct * weight
                        total_weights += weight
            
            baseline.append(weighted_baseline / total_weights if total_weights > 0 else group_pct)
    
    # Calculate differences
    differences = [p - b for p, b in zip(percentages, baseline)]
    
    # Calculate trend lines
    slope_ft, intercept_ft, r_value_ft, p_value_ft, std_err_ft = stats.linregress(minutes, percentages)
    slope_diff, intercept_diff, r_value_diff, p_value_diff, std_err_diff = stats.linregress(minutes, differences)
    
    trend_ft = slope_ft * np.array(minutes) + intercept_ft
    trend_diff = slope_diff * np.array(minutes) + intercept_diff
    
    # Calculate regression between actual and baseline
    slope_reg, intercept_reg, r_value_reg, p_value_reg, std_err_reg = stats.linregress(percentages, baseline)
    regression_line = slope_reg * np.array(percentages) + intercept_reg
    
    # Create timeline plot
    plt.figure(figsize=(15, 10))
    
    plt.plot(minutes, percentages, 'b-', label='Group FT%', linewidth=3)
    plt.plot(minutes, baseline, 'r--', label=f'Group Average: {group_pct:.1f}%', linewidth=2)
    plt.plot(minutes, differences, 'g-', label='Difference', linewidth=2)
    
    plt.plot(minutes, trend_ft, 'b:', label=f'FT% Trend (slope: {slope_ft:.4f})', linewidth=1)
    plt.plot(minutes, trend_diff, 'g:', label=f'Difference Trend (slope: {slope_diff:.4f})', linewidth=1)
    
    stats_text = (f'Group Stats:\nFTA: {total_attempts:,}\n'
                 f'FTM: {total_makes:,}\nFT%: {group_pct:.1f}%\n\n'
                 f'Trends:\nFT% Slope: {slope_ft:.4f}\n'
                 f'Diff Slope: {slope_diff:.4f}')
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
            verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))
    
    plt.title(f'{group_name} Shooters Career Free Throws\n'
              f'FTA: {total_attempts:,}, FTM: {total_makes:,}, FT%: {group_pct:.1f}%')
    plt.xlabel('Minutes into Game')
    plt.ylabel('Free Throw Percentage')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1f}%'.format(y)))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{group_name.lower()}_group_timeline.png'),
                bbox_inches='tight', dpi=300)
    plt.close()
    
    # Create regression scatter plot
    plt.figure(figsize=(8, 8))
    plt.scatter(percentages, baseline, color='blue', alpha=0.5)
    plt.plot(percentages, regression_line, 'm--', 
            label=f'Regression (R²: {r_value_reg**2:.4f})', linewidth=2)
    
    plt.title(f'{group_name} Shooters - Regression: Actual vs Group Average\n'
              f'FTA: {total_attempts:,}, FTM: {total_makes:,}, FT%: {group_pct:.1f}%')
    plt.xlabel('Actual FT%', fontsize=12)
    plt.ylabel('Group Average FT%', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    regression_stats = (f'Regression Statistics:\n'
                       f'Slope: {slope_reg:.4f}\n'
                       f'Intercept: {intercept_reg:.4f}\n'
                       f'R²: {r_value_reg**2:.4f}')
    plt.text(0.02, 0.98, regression_stats, transform=plt.gca().transAxes,
            verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))
    
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{group_name.lower()}_group_regression.png'),
                bbox_inches='tight', dpi=300)
    plt.close()
    
    # Save data




def main():
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

    best_ft_shooters = ["I. Thomas", "S. Nash", "D. Lillard", "P. Stojaković", "C. Billups", "R. Allen", "J. Redick", "K. Irving", "K. Durant", "K. Middleton", "D. Nowitzki", "K. Korver", "D. Gallinari", "E. Boykins", "D. Booker"]

    worst_ft_shooters = ["B. Wallace", "A. Drummond", "D. Jordan", "S. O'Neal", "D. Howard", "A. Walker", "R. Gobert", "T. Chandler", "B. Bol", "B. Biyombo", "M. Harrell", "S. Adams", "J. McGee", "C. Capela", "G. Antetokounmpo"]

    bestworst = best_ft_shooters + worst_ft_shooters

    for year in range(1998, 2000):
        player_attemptCounter = playerToMinToAttemptsClass()
        
        player_attempt_counter_file = os.path.join('dataForEachPlayerYear', f'player_attempt_counter_{year-1}-{year}.txt')
        #stores attempts at each minute for a year

        player_minute_averages_file = os.path.join('dataForEachPlayerYear', f'player_minute_averages_{year-1}-{year}.txt')
        #stores averages at each minute for a given year

        player_yearly_averages_file = os.path.join('dataForEachPlayerYear', f'yearly_averages_{year-1}-{year}.txt')
        #stores yearly averages for different players

        player_yearAnalyzer = FreeThrowAnalyzer()

        for team in allTeams:
            arrHomeDates = get_team_home_dates(team, year)
            print(f"Starting: {team}")
            print("homedates: " + str(arrHomeDates))

            for date in arrHomeDates:
                print("Team: " + str(team))
                print("Year: " + str(year))
                print("Date: " + date)
                curr_date = date.split("-")
                # print(str(curr_date))
                try:
                    player_yearAnalyzer.process_team_games(allTeams[team], curr_date[0], curr_date[1], curr_date[2], year, player_attemptCounter, best_ft_shooters, worst_ft_shooters, bestworst)
                except Exception as e:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    error_details = {
                        "team": str(allTeams[team]),
                        "date": f"{curr_date[0]}-{curr_date[1]}-{curr_date[2]}",
                        "year": year,
                        "timestamp": timestamp,
                        "traceback": traceback.format_exc()
                    }
                    
                    # Log to error logger
                    error_logger.log_error("ProcessTeamGamesError", str(e), error_details)
                
                    time.sleep(2.0) #for just this one we will sleep for longer to not get rate limited
                    continue
                print("processed game")
            time.sleep(2.0)

        playerAtMinuteAvgs = player_yearAnalyzer.playerMinutes

        playerSeasonAvgs = player_yearAnalyzer.playerToSeasonAvg
        
        playerAttemptsAtMinsDict = player_attemptCounter

        # When saving dictionaries to files, handle the nested structure correctly
        with open(player_minute_averages_file, 'w') as f:
            # For player minute averages, we don't need to sort the outer dictionary by player names
            # Each player's inner dictionary of minutes should be sorted
            sorted_player_data = {}
            for player, minute_data in playerAtMinuteAvgs.items():
                # Sort the inner dictionary by minute number
                sorted_minutes = dict(sorted(minute_data.items(), key=lambda x: int(x[0])))
                sorted_player_data[player] = sorted_minutes
            json.dump(sorted_player_data, f, indent=4)

        with open(player_yearly_averages_file, 'w') as f:
            # Season averages don't need sorting as they're single values per player
            json.dump(playerSeasonAvgs, f, indent=4)

        with open(player_attempt_counter_file, 'w') as f:
            sorted_attempts = {}
            for player, minute_data in playerAttemptsAtMinsDict.playerToMinToAttempts.items():
                # Sort each player's attempts by minute
                sorted_minutes = dict(sorted(minute_data.items(), key=lambda x: int(x[0])))
                sorted_attempts[player] = sorted_minutes
            json.dump(sorted_attempts, f, indent=4)

        time.sleep(1.89)
        #stop after one year to check large
        # break


    # Create individual career graphs for all players
    create_player_career_graphs(best_ft_shooters + worst_ft_shooters)
    print("Created individual player graphs")

    # Create group graphs
    create_group_graph(best_ft_shooters, "Best")
    print("Created Best Shooters group graphs")
    
    create_group_graph(worst_ft_shooters, "Worst")
    print("Created Worst Shooters group graphs")

    exit()

if __name__ == '__main__':
    main()