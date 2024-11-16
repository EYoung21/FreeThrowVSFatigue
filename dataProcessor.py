# do for wnba after?
#adjust for intentional misses at end of games somehow (or just drowned out by noise?)

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


class FreeThrowAnalyzer:
    def __init__(self):
        # self.processed_games: Set[str] = set()
        self.minutes = dict()
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

            
    def process_team_games(self, team: Team, year: int, month: int, day: int, yearAnalyzer):
        #for each team, loop through every day in the season and get only HOME games, call this function on it
        """Get play by play data for a team's game on a specific date."""
        try:
            pbp_data = client.play_by_play(
                home_team=team,
                year=year,
                month=month,
                day=day
            )
            time.sleep(2.22)
            self._process_game_data(pbp_data, team, yearAnalyzer, year) #passing year so I can print it
            # print("play by play: " + str(pbp_data))
            # exit()


            # print("playByPlay dara: " + str(pbp_data))
            
            # game_id = f"{year}{month:02d}{day:02d}_{team}"
            # if game_id not in self.processed_games:
            # self.processed_games.add(game_id)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Get the Retry-After header, if available
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    # If Retry-After is in seconds, wait that long
                    print(f"Rate limited. Retrying after {retry_after} seconds.")
                    time.sleep(int(retry_after))
                    # Retry the request
                    pbp_data = client.play_by_play(
                        home_team=team,
                        year=year,
                        month=month,
                        day=day
                    )
                    time.sleep(2.22)
                    self._process_game_data(pbp_data, team, yearAnalyzer, year)
                else:
                    print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                    time.sleep(60)  # Default wait time if Retry-After header is missing
                    pbp_data = client.play_by_play(
                        home_team=team,
                        year=year,
                        month=month,
                        day=day
                    )
                    time.sleep(2.22)
                    self._process_game_data(pbp_data, team, yearAnalyzer, year)
            else:
                print(f"Error getting PBP {team} on {year}-{month}-{day}: {e}")
                raise
    
    def _process_game_data(self, pbp_data: List[dict], team, yearAnalyzer, year):
        player_entry_times = {}
        playersThatSubbedOut = set()

        # Debug: Print the full game timeline
        # print("\n=== Game Timeline ===")
        # for play in pbp_data:
        #     print(f"Period: {play.get('period')}, Remaining Seconds: {play.get('remaining_seconds_in_period')}, Description: {play.get('description')}")

        for play in pbp_data:
            # print(str(play))
            # continue
            if 'enters' in str(play.get('description', '')):
                desParsed = play['description'].split(' enters')
                player_in = desParsed[0]
                desParsed2 = desParsed[1].split('for ')
                playersThatSubbedOut.add(desParsed2[1])
                
                # Debug: Print substitution details
                converted_time = self.calculateConvertedIGT(play.get('remaining_seconds_in_period'), play.get('period'))
                # print(f"\n=== Substitution ===")
                # print(f"Player entering: {player_in}")
                # print(f"Period: {play.get('period')}")
                # print(f"Remaining seconds: {play.get('remaining_seconds_in_period')}")
                # print(f"Converted time: {converted_time}")
                
                player_entry_times[player_in] = converted_time

            if 'free throw' in str(play.get('description', '')):
                self.total_attempted += 1
                yearAnalyzer.total_attempted += 1
                if 'makes' in play['description']:
                    player = play['description'].split(' makes')[0]
                    self.total_made += 1
                    yearAnalyzer.total_made += 1
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

                entry_time = player_entry_times.get(player)
                current_time = self.calculateConvertedIGT(play.get('remaining_seconds_in_period'), play.get('period'))
                
                print(f"Entry time seconds: {entry_time}")
                print(f"Current time seconds: {current_time}")
                
                seconds_played = current_time - entry_time
                
                # print(f"Seconds played: {seconds_played}")
                
                minutes_played = seconds_played / 60

                print(f"Minutes played: {minutes_played}")
                
                if minutes_played < 0:
                    print(f"WARNING: Negative minutes detected at {minutes_played}!")
                    # print(f"Full play data: {play}")
                    self.total_negative_minutes += 1
                    yearAnalyzer.total_negative_minutes += 1
                    continue

                curr_minute = int(math.floor(minutes_played))

                print("minute played: " + str(curr_minute))

                print()
                if curr_minute not in self.minutes:
                    if 'makes' in play['description']: #the player made the freethrow, they're now 1 for 1
                        print(str(player))
                        print("make")
                        self.minutes[curr_minute] = [1, 0, set()] #total made, total missed, players at this minute
                        self.minutes[curr_minute][2].add(player) #adds player to set if not already in it
                    else: #the freethrow was missed
                        print(str(player))
                        print("miss")
                        self.minutes[curr_minute] = [0, 1, set()] #they're 0 for 1
                        self.minutes[curr_minute][2].add(player)
                else: #the minute already was instantiated
                    if 'makes' in play['description']: #the player made the freethrow, they're now 1 for 1
                        print(str(player))
                        print("make")
                        self.minutes[curr_minute][0] += 1 #adds a make
                        self.minutes[curr_minute][2].add(player) #adds player to set if not already in it
                    else: #the freethrow was missed
                        print(str(player))
                        print("miss")
                        self.minutes[curr_minute][1] += 1 #adds a miss
                        self.minutes[curr_minute][2].add(player)
                
                if curr_minute not in yearAnalyzer.minutes:
                    if 'makes' in play['description']: #the player made the freethrow, they're now 1 for 1
                        # print(str(player))
                        # print("make")
                        yearAnalyzer.minutes[curr_minute] = [1, 0, set()] #total made, total missed, players at this minute
                        yearAnalyzer.minutes[curr_minute][2].add(player) #adds player to set if not already in it
                    else: #the freethrow was missed
                        # print(str(player))
                        # print("miss")
                        yearAnalyzer.minutes[curr_minute] = [0, 1, set()] #they're 0 for 1
                        self.minutes[curr_minute][2].add(player)
                else: #the minute already was instantiated
                    if 'makes' in play['description']: #the player made the freethrow, they're now 1 for 1
                        # print(str(player))
                        # print("make")
                        yearAnalyzer.minutes[curr_minute][0] += 1 #adds a make
                        yearAnalyzer.minutes[curr_minute][2].add(player) #adds player to set if not already in it
                    else: #the freethrow was missed
                        # print(str(player))
                        # print("miss")
                        yearAnalyzer.minutes[curr_minute][1] += 1 #adds a miss
                        yearAnalyzer.minutes[curr_minute][2].add(player)
            

    def calculateConvertedIGT(self, remainingSecondsInQuarter, quarter): #remaining seconds, quarter (1, 2, 3, 4)
        # print("remaining seconds: " + str(remainingSecondsInQuarter))
        # print("quarter: " + str(quarter))
        # exit()
        
        return (quarter * 12 * 60) - remainingSecondsInQuarter #returns seconds elapses so far

        # remainingMinutes = remainingSecondsInQuarter / 60
        # minutesPlayedInQuarter = 12 - remainingMinutes

        # if str(quarter) == "1":
        #     return minutesPlayedInQuarter
        # elif str(quarter) == "2":
        #     return 12 + minutesPlayedInQuarter
        # elif str(quarter) == "3":
        #     return 24 + minutesPlayedInQuarter
        # elif str(quarter) == "4":
        #     return 36 + minutesPlayedInQuarter


    
    def year_get_player_ft_pct(self, player_name, year, originAnalyzer): 
        #number_repeated represents how many consequetive times a player's ft average comes from another team
        # print("playername: " + player_name)
        def changeToFirst(word):
            if word == "Scotty Pippen Jr.": #edge case with scotty pippen Jr.
                originAnalyzer.ftNameToActualName["S. Pippen "] = "Scotty Pippen Jr."
                return "S. Pippen "
            if word == "Sasha Vezenkov":
                originAnalyzer.ftNameToActualName["A. Vezenkov"] = "Sasha Vezenkov"
                return "A. Vezenkov"
            if word == "Dariq Whitehead":
                originAnalyzer.ftNameToActualName["D. Miller-Whitehead"] = "Dariq Whitehead"
                return "D. Miller-Whitehead"
            # print("word: " + word)
            stringArr = word.split(" ")
            firstString = stringArr[0][0] + "." #gets first letter of first name
            secondString = stringArr[1] #gets second string
            fullString = firstString + " " + secondString

            return fullString

        try:
            if not os.path.exists(f"./{year-1}_{year}_player_season_totals.csv"):
                client.players_season_totals(
                    season_end_year=year, 
                    output_type=OutputType.CSV, 
                    output_file_path=f"./{year-1}_{year}_player_season_totals.csv"
                )
                time.sleep(2.22)
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
                        time.sleep(2.22)
                else:
                    print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                    time.sleep(60)  # Default wait time if Retry-After header is missing
                    if not os.path.exists(f"./{year-1}_{year}_player_season_totals.csv"):
                        client.players_season_totals(
                            season_end_year=year, 
                            output_type=OutputType.CSV, 
                            output_file_path=f"./{year-1}_{year}_player_season_totals.csv"
                        )
                        time.sleep(2.22)
            else:
                # Re-raise if it's a different HTTP error
                raise

        with open(f"./{year-1}_{year}_player_season_totals.csv") as file:
            reader = csv.reader(file, delimiter=',')
            # Skip the header row
            next(reader)
            rows = list(reader)
            #indcies 12 and 13 are made and attempted respectively
            rows = rows[:-1] #skip last row, league averages
            for i, row in enumerate(rows):
                # player_row = row[0]
                # print("Player from row: " + row[1])
                print("name from rows: " + row[1])
                fullString = changeToFirst(row[1])
                # print("changed: " + fullString)
                # exit()
                print("Player from row changed name: " + fullString)

                if fullString == player_name:
                    originAnalyzer.ftNameToActualName[player_name] = row[1] #converts from ftname to full name, stores in dictionary
                    print("Player from row: " + row[1])
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
                            if row[1] not in originAnalyzer.actualNameToSeasonAverages:
                                originAnalyzer.actualNameToSeasonAverages[row[1]] = {year : [int(made), int(attempted)]}
                            else: #actualName was already in actualNameToSeasonAverages
                                originAnalyzer.actualNameToSeasonAverages[row[1]][year][0] += int(made)
                                originAnalyzer.actualNameToSeasonAverages[row[1]][year][1] += int(attempted)

                            return [int(made), int(attempted)] 
                            #returns array of number made in first bucket and number attempted in second bucket
                    return "No free throws"
            return None #if player requested wasn't in season stats

        #will return array where first bucket is dictionary of minutes to minute averages and second bucket is dictionary of minutes to yearly averages
    def calculateMinuteAndYearlyAverages(self, year, originAnalyzer):
        atMinuteAverages = dict() #maps minutes to their minute averages (of all fts at that minute)
        atMinuteYearlyAverages = dict()

        for key in self.minutes:
            total_made = 0
            total_attempted = 0
            minuteAverage = self.minutes[key][0] / (self.minutes[key][0] + self.minutes[key][1])  #total made / total made + total missed
            atMinuteAverages[key] = minuteAverage * 100 #to get percentage

            totalPercentage = float(0)
            players = list(self.minutes[key][2])
            totalNumberPlayers = len(players)
            for i in range(totalNumberPlayers): #looping through set of players that shot fts at each minute
                currPlayerName = players[i] #curr player
                print("Looking for: " + "|" + str(currPlayerName) + "|")
                # print(str(data))
                # print(str(self.get_player_ft_pct(data, "Joel Embid")))
                # exit()
                # print("looking for: " + str(currPlayerName))
                madeAttemptedArr = self.year_get_player_ft_pct(currPlayerName, year, originAnalyzer)
                if madeAttemptedArr != "No free throws":
                    # print("returned: " + str(returned))
                    total_made += madeAttemptedArr[0]
                    total_attempted += madeAttemptedArr[1]

            # averageFTPercentageForAllPlayersAtMinute = totalPercentage / totalNumberPlayers

            atMinuteYearlyAverages[key] = (total_made / total_attempted) * 100
        
        return [atMinuteAverages, atMinuteYearlyAverages]
    
    def __get_player_ft_pct(self, player_name, year): 
        #number_repeated represents how many consequetive times a player's ft average comes from another team
        # print("playername: " + player_name)
        def changeToFirst(word):
            # print("word: " + word)
            stringArr = word.split(" ")
            firstString = stringArr[0][0] + "." #gets first letter of first name
            secondString = stringArr[1] #gets second string
            fullString = firstString + " " + secondString

            return fullString
        
        if year in self.actualNameToSeasonAverages[player_name]:
            #if year is in already existing parsed ft% for given player for given year, we don't have to do all of the above (it was done for us in a previously)
            try:
                made = self.actualNameToSeasonAverages[player_name][year][0]
                attempted = self.actualNameToSeasonAverages[player_name][year][1]
                return [int(made), int(attempted)]
            except Exception as e:
                self.dictionary_error_counter += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                error_msg = f"""
            ERROR {self.dictionary_error_counter}:
            Time: {timestamp}
            Player: {player_name}
            Year: {year}
            Error: {str(e)}
            Traceback: {traceback.format_exc()}
            Dictionary State: {self.actualNameToSeasonAverages.get(player_name, 'Player not found')}
            ----------------------------------------
            """
                
                with open('dictionaryErrors.txt', 'a') as f:
                    f.write(error_msg)
                
                # You might want to return some default value here instead of None
                return [0, 0]  # or whatever default makes sense for your application
        else:#
            try:
                if not os.path.exists(f"./{year-1}_{year}_player_season_totals.csv"):
                    client.players_season_totals(
                        season_end_year=year, 
                        output_type=OutputType.CSV, 
                        output_file_path=f"./{year-1}_{year}_player_season_totals.csv"
                    )
                    time.sleep(2.22)
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
                            time.sleep(2.22)
                    else:
                        print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                        time.sleep(60)  # Default wait time if Retry-After header is missing
                        if not os.path.exists(f"./{year-1}_{year}_player_season_totals.csv"):
                            client.players_season_totals(
                                season_end_year=year, 
                                output_type=OutputType.CSV, 
                                output_file_path=f"./{year-1}_{year}_player_season_totals.csv"
                            )
                            time.sleep(2.22)
                else:
                    # Re-raise if it's a different HTTP error
                    raise
            
            with open(f"./{year-1}_{year}_player_season_totals.csv") as file:
                reader = csv.reader(file, delimiter=',')
                # Skip the header row
                next(reader)
                rows = list(reader)
                #indcies 12 and 13 are made and attempted respectively
                rows = rows[:-1] #skip last row, league averages
                for i, row in enumerate(rows):
                    # player_row = row[0]
                    # print("Player from row: " + row[1])
                    print("name from rows: " + row[1])
                    fullString = changeToFirst(row[1])
                    # print("changed: " + fullString)
                    # exit()
                    print("Player from row changed name: " + fullString)

                    if fullString == player_name:
                        print("Player from row: " + row[1])
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
                return None #if player requested wasn't in season stats
            

    
    def calculateLargeMinuteAndYearlyAverages(self):
        atMinuteAverages = dict() #maps minutes to their minute averages (of all fts at that minute)
        atMinuteYearlyAverages = dict()
        

        for key in self.minutes:
            minuteAverage = self.minutes[key][0] / (self.minutes[key][0] + self.minutes[key][1])  #total made / total made + total missed
            atMinuteAverages[key] = minuteAverage * 100 #to get percentage

            # totalPercentage = float(0)
            players = list(self.minutes[key][2])
            totalNumberPlayers = len(players)
            for i in range(totalNumberPlayers): #looping through set of players that shot fts at each minute
                #TODO:here, get nba entry and exit years (/dates) (/present?) of current player, then loop through only those years
                #https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/commonplayerinfo.md

                #may have to get player id with:
                #https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/static/players.md

                currPlayerName = players[i] #curr player
                actualName = self.ftNameToActualName[currPlayerName] 
                #to convert from ftname to actual name, which we kept track of during original loop through all seasons by passing originalAnalyzer to individual calculateMinuteAndYearlyAverages func
                nbaapiPlayer = get_player_career_span(actualName)
                
                print(str(get_player_career_span(actualName)))

                firstYear = nbaapiPlayer['rookie_year']
                lastYear = nbaapiPlayer['last_year']


                # exit()
                # break

                for year in range(firstYear, lastYear + 1): #to hit their last season, range is exclusive of upper bound
                    print("Looking for: " + "|" + str(currPlayerName) + "|")
                    # print(str(data))
                    # print(str(self.get_player_ft_pct(data, "Joel Embid"))) #need to write new version of this function but for multiple names
                    # exit()
                    # print("looking for: " + str(currPlayerName))
                    madeAttemptedArr = self.__get_player_ft_pct(actualName, year)
                    #could maybe pass in actualName here, to not have to convert from name in player_season_totals to ftName type, then you could map "actualName"
                    #but actual name from nbaapiPlayer may differ form the names in that csv, so best to leave it as this for now
                    if madeAttemptedArr != "No free throws":
                        total_made = madeAttemptedArr[0]
                        total_attempted = madeAttemptedArr[1]
                    
                    # if (returned is None): #the player 
                    #     continue

            # averageFTPercentageForAllPlayersAtMinute = (total_made / total_attempted) * 100

            atMinuteYearlyAverages[key] = (total_made / total_attempted) * 100
        
        return [atMinuteAverages, atMinuteYearlyAverages]

def get_player_career_span(player_name):
   # Search for the player
   player_matches = players.find_players_by_full_name(player_name)
   
   if not player_matches:
       return f"No player found with name '{player_name}'"
   
   if len(player_matches) > 1:
       # If multiple matches, show all options
       return "Multiple players found:\n" + "\n".join(
           f"- {p['full_name']} (ID: {p['id']})" for p in player_matches
       )
   
   # Get the player's ID and info
   player = player_matches[0]
   player_info = commonplayerinfo.CommonPlayerInfo(player_id=player['id'])
   common_info = player_info.get_normalized_dict()['CommonPlayerInfo'][0]
   
   # Return formatted career information
   return {
       'name': common_info['DISPLAY_FIRST_LAST'],
       'rookie_year': common_info['FROM_YEAR'],
       'last_year': common_info['TO_YEAR'],
       'seasons_played': common_info['SEASON_EXP'],
       'is_active': player['is_active']
   }

def get_team_home_dates(team, year):
    # Open the file and create the reader
    try:
        if not os.path.exists(f"./{year-1}_{year}_season.csv"):
            client.season_schedule(
                season_end_year=year,
                output_type=OutputType.CSV,
                output_file_path=f"./{year-1}_{year}_season.csv"
            )
            time.sleep(2.22)
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
                    time.sleep(2.22)
            else:
                print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                time.sleep(60)  # Default wait time if Retry-After header is missing
                if not os.path.exists(f"./{year-1}_{year}_season.csv"):
                    client.season_schedule(
                        season_end_year=year,
                        output_type=OutputType.CSV,
                        output_file_path=f"./{year-1}_{year}_season.csv"
                    )
                    time.sleep(2.22)
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
    import numpy as np
    from scipy import stats

    # Get all minutes (x-axis)
    minutes = sorted(minute_averages.keys())

    # Get corresponding values for each line
    ft_percentages = [minute_averages[m] for m in minutes]
    yearly_percentages = [yearly_averages[m] for m in minutes]
    differences = [ft_percentages[i] - yearly_percentages[i] for i in range(len(minutes))]

    # Create DataFrame and save to CSV
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

    # Plot original lines
    plt.plot(minutes, ft_percentages, 'b-', label='Actual FT% at minute', linewidth=2)
    plt.plot(minutes, yearly_percentages, 'g-', label='Players\' Season Average', linewidth=2)
    plt.plot(minutes, differences, 'r-', label='Difference', linewidth=2)

    # Plot trendlines
    plt.plot(minutes, line_ft, 'b:', label=f'FT% Trend (slope: {slope_ft:.4f})', linewidth=1)
    plt.plot(minutes, line_yearly, 'g:', label=f'Season Avg Trend (slope: {slope_yearly:.4f})', linewidth=1)
    plt.plot(minutes, line_diff, 'r:', label=f'Difference Trend (slope: {slope_diff:.4f})', linewidth=1)

    # Customize the plot
    if totalAttempted > 0:
        percentage = round(totalMade/totalAttempted, 2)
    else:
        percentage = ""
    plt.title(f'Free Throw Percentage by Minutes Played for {startYear}-{endYear} Season | FTA: {totalAttempted}, FTs Made: {totalMade}, %: {percentage}', fontsize=14)
    plt.xlabel('Minutes Played', fontsize=12)
    plt.ylabel('Free Throw Percentage', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10)

    # Add a horizontal line at y=0 for reference in difference
    plt.axhline(y=0, color='k', linestyle='-', alpha=0.1)

    # Format y-axis as percentage
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1f}%'.format(y)))

    # Save the plot
    plt.savefig(f'{startYear}-{endYear}_ft_percentage_analysis.png')
    plt.show()

 #this function would parse a printed txt file of 
def parse_data_file(file_path):
    # Open and read the file content
    with open(file_path, 'r') as file:
        content = file.read()

    # Parse the data from string to Python dictionary
    # Assuming the data format in the file is a valid Python dictionary structure
    try:
        data = ast.literal_eval(content)
    except (SyntaxError, ValueError) as e:
        print("Error parsing file:", e)
        return None

    return data

def main():
    analyzer = FreeThrowAnalyzer()

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



    #VITAL, only commented for a sec for testing
    for year in range(2000, 2025):
        # Check if both files already exist
        minute_averages_file = f'minute_averages_{year}.txt'
        yearly_averages_file = f'yearly_averages_{year}.txt'
        
        #comment this out to produce new documents for minute and minute yearly avgs at minutes (or delete exisitng ones)
        if os.path.exists(minute_averages_file) and os.path.exists(yearly_averages_file):
            print(f"Files for year {year} already exist, skipping...")
            continue
            
        yearAnalyzer = FreeThrowAnalyzer()

        for key in allTeams:
            arrHomeDates = get_team_home_dates(key, year)
            print(f"Starting: {key}")
            print("homedates: " + str(arrHomeDates))

            for date in arrHomeDates:
                print("Team: " + str(key))
                print("Year: " + str(year))
                print("Date: " + date)
                curr_date = date.split("-")
                analyzer.play_by_play_error_counter = 0

                try:
                    analyzer.process_team_games(allTeams[key], curr_date[0], curr_date[1], curr_date[2], yearAnalyzer)
                except Exception as e:
                    analyzer.play_by_play_error_counter += 1
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    error_msg = f"""
                    ERROR {analyzer.play_by_play_error_counter}:
                    Time: {timestamp}
                    Team: {allTeams[key]}
                    Date: {curr_date[0]}-{curr_date[1]}-{curr_date[2]}
                    Error: {str(e)}
                    Traceback: {traceback.format_exc()}
                    ----------------------------------------
                    """
                    
                    with open('playByPlayErrors.txt', 'a') as f:
                        f.write(error_msg)
                    
                        continue
                print("processed game")
        print(f"Total neg at {year}:" + str(yearAnalyzer.total_negative_minutes))
        print(f"Totl made at {year}" + str(yearAnalyzer.total_made))
        print(f"Total attempted at {year}" + str(yearAnalyzer.total_attempted))
        yearlyAnsArr = yearAnalyzer.calculateMinuteAndYearlyAverages(year, analyzer)
        yearlyMinuteAveragesDict = yearlyAnsArr[0]
        yearlyMinuteYearlyAveragesDict = yearlyAnsArr[1]

        # Save dictionaries to text files
        with open(minute_averages_file, 'w') as f:
            json.dump(yearlyMinuteAveragesDict, f, indent=4)
        
        with open(yearly_averages_file, 'w') as f:
            json.dump(yearlyMinuteYearlyAveragesDict, f, indent=4)

        plot_ft_percentages(yearlyMinuteAveragesDict, yearlyMinuteYearlyAveragesDict, year-1, year, yearAnalyzer.total_made, yearAnalyzer.total_attempted)
        
        #stop after one year to check large
        # break







    
    #for 2023-24 season
    # analyzer.minutes = parse_data_file("/Users/eliyoung/Stat011Project/FatigueVSFreethrow/dictionary.txt")

    #this will print the dictionary
    # print("minutesDict: " + str(analyzer.minutes))

    # analyzer.minutes = {2: [1564, 435, {'T. Watford', 'B. Bol', 'J. Robinson-Earl', 'S. Aldama', 'P. Connaughton', 'J. Landale', 'A. Coffey', 'E. Mobley', 'D. Terry', 'A. Fudge', 'J. Isaac', 'D. Jordan', 'B. Williams', 'K. Durant', 'N. Jović', 'D. DeRozan', 'C. Braun', 'G. Bitadze', 'T. Jackson-Davis', 'P. George', 'D. Mitchell', 'G. Brown', 'Z. LaVine', 'M. Turner', 'I. Stewart', 'D. Bane', 'P. Banchero', 'D. Lillard', 'P. Watson', 'J. Cain', 'T. Haliburton', 'C. Thomas', 'K. Irving', 'P. Achiuwa', 'N. Little', 'J. Morant', 'M. Bagley', 'D. Schröder', 'T. Thompson', 'O. Toppin', 'D. Sabonis', 'J. Freeman-Liberty', 'F. Ntilikina', 'T. Lyles', 'I. Okoro', 'C. Wallace', 'D. Theis', 'K. Murray', 'Z. Nnaji', 'J. Allen', 'L. Waters', 'S. Milton', 'B. Miller', 'C. Martin', 'J. Poole', 'J. Grant', 'P. Beverley', 'A. Pokusevski', 'J. Sims', 'C. Metu', 'T. Camara', 'D. Green', 'O. Prosper', 'D. Barlow', 'O. Robinson', 'B. Wesley', 'H. Barnes', 'R. Hachimura', 'T. Eason', 'J. Sochan', 'S. Barnes', 'C. LeVert', 'J. Murray', 'R. Jackson', 'T. Vukcevic', 'S. Sharpe', 'J. Crowder', 'T. Craig', 'Z. Williams', 'J. Nwora', 'D. Rose', 'J. Tatum', 'J. Collins', 'D. Roddy', 'I. Jackson', 'L. Walker', 'M. Moody', 'K. Thompson', 'A. Nembhard', 'J. Konchar', 'J. McGee', 'D. Exum', 'C. Joseph', 'C. Cunningham', 'K. Towns', 'J. Robinson', 'V. Williams', 'E. Fournier', 'J. Alvarado', 'A. Black', 'T. Maxey', 'J. Jaquez', 'B. Mathurin', 'A. Thompson', 'M. Beauchamp', 'D. Brooks', 'B. Boston', 'L. Shamet', 'D. Šarić', 'D. Booker', 'S. Lee', 'J. Nowell', 'T. Harris', 'Z. Collins', 'J. Ramsey', 'J. Jackson', 'K. Leonard', 'D. Powell', 'D. Avdija', 'V. Wembanyama', 'R. Holmes', 'M. Williams', 'N. Vučević', 'I. Joe', 'L. James', 'R. Council', 'G. Niang', 'S. Henderson', 'K. George', 'T. Hardaway', 'D. DiVincenzo', 'O. Yurtseven', 'A. Wiggins', 'B. Ingram', 'U. Garuba', 'O. Anunoby', 'I. Quickley', 'K. Hayes', 'D. Hunter', 'P. Washington', 'C. Gillespie', 'D. Jarreau', 'J. Embiid', 'B. Portis', 'C. Anthony', 'G. Hayward', 'T. Jones', 'J. Rhoden', 'Z. Williamson', 'G. Dick', 'D. Banton', 'J. Bernard', 'J. Poeltl', 'I. Zubac', 'P. Reed', 'M. Branham', 'A. Drummond', 'T. Brown', 'L. Markkanen', 'M. Wagner', 'O. Agbaji', 'M. Sasser', 'D. Vassell', 'Y. Watanabe', 'F. Korkmaz', 'D. Garland', 'S. Bey', 'D. Gallinari', 'D. White', 'C. Paul', 'G. Jackson', 'M. Morris', 'C. Sexton', 'K. Martin', 'M. Flynn', 'T. Rozier', 'M. Robinson', 'M. Kleber', 'N. Powell', 'I. Hartenstein', 'B. Bogdanović', 'C. McCollum', 'B. Sensabaugh', 'J. Randle', 'R. Williams', 'S. Pippen ', 'J. Davis', 'N. Batum', 'J. Clarkson', 'G. Mathews', 'C. Capela', 'C. Livingston', 'O. Sarr', 'C. Porter', 'K. Johnson', 'E. Omoruyi', 'O. Okongwu', 'L. Stevens', 'S. Mays', 'T. Herro', 'J. Green', 'S. Gilgeous-Alexander', 'C. Reddish', 'N. Richards', 'J. Giddey', 'B. Brown', 'J. Vanderbilt', 'J. Valančiūnas', 'N. Alexander-Walker', 'D. Gafford', 'K. Lofton', 'B. Hyland', 'J. Johnson', 'U. Azubuike', 'D. Lively', 'G. Harris', 'K. Oubre', 'M. Fultz', 'B. Lopez', 'S. Mamukelashvili', 'M. McBride', 'T. McConnell', 'O. Brissett', 'S. Cissoko', 'B. Coulibaly', 'J. Walker', 'A. Sengun', 'R. Barrett', 'M. Diabaté', 'K. Caldwell-Pope', 'N. Clowney', 'L. Garza', 'I. Badji', 'T. Young', 'E. Gordon', 'J. Okogie', 'D. Reath', 'P. Pritchard', 'D. Sharpe', 'J. Ingles', 'M. Monk', 'N. Reid', 'B. Biyombo', 'M. Bridges', 'N. Marshall', 'K. Olynyk', 'D. Daniels', 'J. Nurkić', 'G. Williams', 'J. Ivey', 'J. Wiseman', 'A. Dosunmu', 'C. White', 'L. Nance', 'J. Butler', 'G. Allen', 'G. Antetokounmpo', 'K. Middleton', 'L. Ball', 'M. Brogdon', 'J. Tate', 'A. Burks', 'D. Russell', 'P. Siakam', 'C. Zeller', 'C. Holmgren', 'C. Swider', 'D. Melton', 'M. Diakite', 'B. Marjanović', 'J. Wilson', 'A. Gill', 'R. Gobert', 'M. Plumlee', 'K. Huerter', 'F. Wagner', 'J. Hawkins', 'J. Harden', 'A. Green', 'C. Osman', 'W. Carter', 'J. Hayes', 'B. Adebayo', 'J. Suggs', 'T. Hendricks', 'J. Juzang', 'J. LaRavia', 'A. Reaves', 'M. Christie', 'L. Kornet', 'T. Smith', 'J. Strawther', 'K. Porziņģis', 'K. Knox', 'A. Lawson', 'B. Key', 'K. Anderson', 'J. Minott', 'M. Strus', 'C. Kispert', 'S. Merrill', 'S. Dinwiddie', 'C. Johnson', 'D. Nix', 'C. Duarte', 'D. Wright', 'D. Fox', 'D. Dennis', 'T. Murphy', 'M. Bamba', 'A. Len', 'C. Whitmore', 'J. Brown', 'S. Curry', 'J. McDaniels', 'F. VanVleet', 'R. Lopez', 'D. Eubanks', 'T. Horton-Tucker', 'J. Kuminga', 'J. Thor', 'D. Smith', 'J. Smith', 'T. Mann', 'J. Brunson', 'R. Rupert', 'V. Micić', 'M. Porter', 'B. Podziemski', 'M. Conley', 'L. Miller', 'C. Boucher', 'K. Love', 'C. Okeke', 'D. Robinson', 'A. Davis', 'N. Jokić', 'G. Trent', 'A. Edwards', 'J. Duren', 'W. Matthews', 'A. Gordon', 'K. Bates-Diop', 'N. Claxton', 'R. Westbrook', 'C. Wood', 'J. Williams', 'D. Jones', 'D. Jeffries', 'B. McGowens', 'B. Fernando', 'D. Bertāns', 'L. Black', 'L. Dončić', 'J. Hardy', 'S. Lundy', 'K. Kuzma'}], 3: [1589, 423, {'T. Watford', 'B. Bol', 'J. Robinson-Earl', 'P. Connaughton', 'J. Landale', 'A. Sanogo', 'A. Coffey', 'D. Terry', 'E. Mobley', 'J. Isaac', 'D. Jordan', 'B. Williams', 'I. Livers', 'K. Durant', 'N. Jović', 'D. DeRozan', 'C. Braun', 'G. Bitadze', 'T. Jackson-Davis', 'P. George', 'D. Mitchell', 'Z. LaVine', 'M. Turner', 'I. Stewart', 'S. Umude', 'D. Bane', 'P. Banchero', 'H. Giles', 'D. Lillard', 'P. Watson', 'T. Haliburton', 'C. Thomas', 'K. Irving', 'P. Achiuwa', 'M. Bagley', 'D. Schröder', 'R. Rollins', 'J. Holiday', 'F. Petrušev', 'O. Toppin', 'D. Sabonis', 'T. Lyles', 'I. Okoro', 'L. Dort', 'J. Goodwin', 'C. Wallace', 'D. Theis', 'K. Murray', 'Z. Nnaji', 'J. Allen', 'B. Miller', 'C. Martin', 'J. Poole', 'J. Grant', 'P. Beverley', 'O. Tshiebwe', 'A. Pokusevski', 'J. Sims', 'C. Metu', 'O. Prosper', 'D. Barlow', 'O. Robinson', 'B. Wesley', 'R. Hachimura', 'T. Eason', 'J. Sochan', 'C. LeVert', 'J. Murray', 'R. Jackson', 'S. Sharpe', 'J. Richardson', 'T. Craig', 'B. Beal', 'J. Nwora', 'T. Warren', 'J. Tatum', 'J. Collins', 'D. Roddy', 'D. Murray', 'L. Walker', 'M. Moody', 'I. Jackson', 'K. Thompson', 'A. Nembhard', 'J. McGee', 'D. Exum', 'P. Baldwin', 'K. Towns', 'J. Robinson', 'V. Williams', 'E. Fournier', 'J. Alvarado', 'T. Maxey', 'J. Jaquez', 'K. Ellis', 'B. Mathurin', 'A. Thompson', 'M. Beauchamp', 'D. Brooks', 'B. Boston', 'D. Šarić', 'D. Booker', 'L. Shamet', 'J. Hart', 'T. Harris', 'Z. Collins', 'J. Ramsey', 'J. Jackson', 'K. Leonard', 'D. Powell', 'D. Avdija', 'V. Wembanyama', 'R. Holmes', 'M. Williams', 'N. Vučević', 'I. Joe', 'L. James', 'R. Council', 'S. Henderson', 'K. George', 'M. Nowell', 'T. Hardaway', 'D. DiVincenzo', 'O. Yurtseven', 'A. Wiggins', 'B. Ingram', 'I. Quickley', 'D. Hunter', 'P. Washington', 'P. Mills', 'D. Jarreau', 'J. Embiid', 'B. Portis', 'C. Anthony', 'G. Hayward', 'T. Jones', 'Z. Williamson', 'G. Dick', 'A. Simons', 'D. Banton', 'J. Poeltl', 'I. Zubac', 'P. Reed', 'M. Branham', 'A. Drummond', 'T. Brown', 'L. Markkanen', 'M. Wagner', 'O. Agbaji', 'M. Sasser', 'F. Korkmaz', 'N. Queta', 'S. Bey', 'D. Gallinari', 'D. White', 'C. Paul', 'G. Jackson', 'M. Morris', 'J. Springer', 'C. Sexton', 'W. Kessler', 'K. Martin', 'M. Flynn', 'M. Kleber', 'N. Powell', 'I. Hartenstein', 'B. Bogdanović', 'C. McCollum', 'B. Sensabaugh', 'A. Nesmith', 'J. Randle', 'H. Highsmith', 'R. Williams', 'S. Pippen ', 'J. Davis', 'J. Clarkson', 'G. Mathews', 'T. Prince', 'C. Capela', 'C. Livingston', 'O. Sarr', 'C. Porter', 'K. Johnson', 'E. Omoruyi', 'S. Hauser', 'O. Okongwu', 'S. Mays', 'L. Stevens', 'K. Dunn', 'T. Herro', 'J. Green', 'S. Gilgeous-Alexander', 'J. McLaughlin', 'J. Hood-Schifino', 'N. Richards', 'B. Brown', 'C. Payne', 'D. McDermott', 'J. Valančiūnas', 'N. Alexander-Walker', 'D. Gafford', 'K. Lofton', 'J. Johnson', 'U. Azubuike', 'D. Lively', 'K. Oubre', 'M. Fultz', 'S. Mamukelashvili', 'M. McBride', 'T. McConnell', 'O. Brissett', 'S. Fontecchio', 'O. Dieng', 'S. Cissoko', 'B. Coulibaly', 'J. Walker', 'A. Sengun', 'R. Barrett', 'D. House', 'K. Caldwell-Pope', 'L. Garza', 'I. Badji', 'T. Forrest', 'T. Young', 'E. Gordon', 'J. Okogie', 'D. Reath', 'N. Hinton', 'P. Pritchard', 'D. Sharpe', 'J. Ingles', 'M. Monk', 'N. Reid', 'M. Bridges', 'C. Castleton', 'N. Marshall', 'K. Olynyk', 'J. Nurkić', 'G. Williams', 'J. Ivey', 'J. Wiseman', 'A. Dosunmu', 'C. White', 'L. Nance', 'J. Butler', 'G. Allen', 'G. Antetokounmpo', 'K. Middleton', 'L. Ball', 'M. Brogdon', 'J. Tate', 'L. Kennard', 'A. Burks', 'D. Russell', 'P. Siakam', 'C. Holmgren', 'B. Marjanović', 'G. Temple', 'J. Phillips', 'B. Sheppard', "R. O'Neale", 'A. Gill', 'M. Plumlee', 'R. Gobert', 'T. Bryant', 'J. Porter', 'F. Wagner', 'J. Hawkins', 'J. Harden', 'A. Green', 'C. Osman', 'W. Carter', 'J. Hayes', 'B. Adebayo', 'J. Suggs', 'T. Hendricks', 'J. Juzang', 'J. LaRavia', 'A. Reaves', 'M. Christie', 'L. Kornet', 'M. Muscala', 'J. Strawther', 'K. Lewis', 'K. Porziņģis', 'L. Šamanić', 'K. Anderson', 'A. Horford', 'A. Holiday', 'A. Hagans', 'C. Kispert', 'S. Merrill', 'S. Dinwiddie', 'C. Johnson', 'C. Duarte', 'D. Wright', 'D. Fox', 'D. Dennis', 'T. Murphy', 'M. Bamba', 'C. Whitmore', 'J. Brown', 'S. Curry', 'J. McDaniels', 'J. Champagnie', 'D. Eubanks', 'T. Horton-Tucker', 'J. Kuminga', 'J. Thor', 'D. Smith', 'J. Smith', 'B. Boeheim', 'I. Wainright', 'T. Mann', 'J. Brunson', 'V. Micić', 'M. Porter', 'B. Podziemski', 'M. Pereira', 'C. Boucher', 'K. Love', 'D. Robinson', 'A. Davis', 'A. Caruso', 'N. Jokić', 'G. Trent', 'A. Edwards', 'J. Duren', 'W. Matthews', 'A. Gordon', 'M. Smart', 'K. Bates-Diop', 'N. Claxton', 'R. Westbrook', 'C. Wood', 'J. Williams', 'D. Jones', 'B. McGowens', 'B. Fernando', 'L. Black', 'G. Santos', 'L. Dončić', 'C. Houstan', 'J. Hardy', 'S. Lundy', 'K. Looney', 'K. Kuzma'}]}




    # ansArr = analyzer.calculateLargeMinuteAndYearlyAverages() 
    ansArr = analyzer.calculateLargeMinuteAndYearlyAverages() 






    #will have to be career ft shots for each player, or could be the yearly averages for every year they played
    
    minuteAveragesDict = ansArr[0]

    minuteYearlyAveragesDict = ansArr[1]

    # print("minuteAvg: " + str(minuteAveragesDict)) #empty for some reason?

    # print("minuteYearlyAvg: " + str(minuteYearlyAveragesDict)) #empty for some reason?

    print("Total neg from 2000-2024: " + str(analyzer.total_negative_minutes))
    print("Total made from 2000-2024:" + str(analyzer.total_made))
    print("Total made from 2000-2024" + str(analyzer.total_attempted))

    print()

    plot_ft_percentages(minuteAveragesDict, minuteYearlyAveragesDict, 2000, 2024, analyzer.total_made, analyzer.total_attempted)

    exit()

if __name__ == '__main__':
    main()