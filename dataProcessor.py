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




class FreeThrowAnalyzer:
    def __init__(self):
        # self.processed_games: Set[str] = set()
        self.minutes = dict()
        
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

            
    def process_team_games(self, team: Team, year: int, month: int, day: int):
        #for each team, loop through every day in the season and get only HOME games, call this function on it
        """Get play by play data for a team's game on a specific date."""
        try:
            pbp_data = client.play_by_play(
                home_team=team,
                year=year,
                month=month,
                day=day
            )
            time.sleep(1.85)
            self._process_game_data(pbp_data, team, year, month, day) #passing year so I can print it
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
                    time.sleep(1.85)
                    self._process_game_data(pbp_data, team, year, month, day)
                else:
                    print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                    time.sleep(60)  # Default wait time if Retry-After header is missing
                    pbp_data = client.play_by_play(
                        home_team=team,
                        year=year,
                        month=month,
                        day=day
                    )
                    time.sleep(1.85)
                    self._process_game_data(pbp_data, team, year, month, day)
            else:
                print(f"Error getting PBP {team} on {year}-{month}-{day}: {e}")
                raise
    
    def _process_game_data(self, pbp_data: List[dict], team, year, month, day):
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

                entry_time = player_entry_times.get(player)
                current_time = self.calculateConvertedIGT(play.get('remaining_seconds_in_period'), play.get('period'), play.get('period_type'))
                
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

                print()
                if curr_minute not in self.minutes:
                    if 'makes' in play['description']: #the player made the freethrow, they're now 1 for 1
                        print(str(player))
                        print("make")
                        self.minutes[curr_minute] = [1, 0, dict()] #!!!!!!!YOYOYO total made, total missed, players at this minute mapped to arr of their yearly ft% average and the number of attempts at that minute
                        # if player not in self.minutes[curr_minute][2]:
                        self.minutes[curr_minute][2][player] = [1, self.get_player_ft_pct(player, year)] # attempts at min, ft% at yr
                        # self.minutes[curr_minute][2].add(player) #adds player to set if not already in it
                    else: #the freethrow was missed
                        print(str(player))
                        print("miss")
                        self.minutes[curr_minute] = [0, 1, dict()] #they're 0 for 1
                        self.minutes[curr_minute][2][player] = [1, self.get_player_ft_pct(player, year)]
                else: #the minute already was instantiated
                    if 'makes' in play['description']: #the player made the freethrow, they're now 1 for 1
                        print(str(player))
                        print("make")
                        self.minutes[curr_minute][0] += 1 #adds a make
                        if player not in self.minutes[curr_minute][2]:
                            self.minutes[curr_minute][2][player] = [1, self.get_player_ft_pct(player, year)] #creates player dict
                        else:
                            self.minutes[curr_minute][2][player][0] += 1 #increments attempt in player dict

                        # self.minutes[curr_minute][2].add(player) #adds player to set if not already in it  #adds player to dictionary mapped to [<number fts attempted>, season ft avg]
                    else: #the freethrow was missed
                        print(str(player))
                        print("miss")
                        self.minutes[curr_minute][1] += 1 #adds a miss
                        if player not in self.minutes[curr_minute][2]:
                            self.minutes[curr_minute][2][player] = [1, self.get_player_ft_pct(player, year)] #creates player dict
                        else:
                            self.minutes[curr_minute][2][player][0] += 1 #increments attempt in player dict
            

    def calculateConvertedIGT(self, remainingSecondsInPeriod, quarter, type): #remaining seconds, quarter (1, 2, 3, 4)
        # print("remaining seconds: " + str(remainingSecondsInQuarter))
        # print("quarter: " + str(quarter))
        # exit()
        if type != "OVERTIME":
            return (quarter * 12 * 60) - remainingSecondsInPeriod #returns seconds elapses so far
        else:
            return (4*12*60) + (quarter*5*60) - remainingSecondsInPeriod

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


    
    # def year_get_player_ft_pct(self, player_name, year, originAnalyzer): 
    #     def changeToFirst(word):
    #         if word == "Scotty Pippen Jr.":
    #             originAnalyzer.ftNameToActualName["S. Pippen "] = "Scotty Pippen Jr."
    #             return "S. Pippen "
    #         if word == "Sasha Vezenkov":
    #             originAnalyzer.ftNameToActualName["A. Vezenkov"] = "Sasha Vezenkov"
    #             return "A. Vezenkov"
    #         if word == "Dariq Whitehead":
    #             originAnalyzer.ftNameToActualName["D. Miller-Whitehead"] = "Dariq Whitehead"
    #             return "D. Miller-Whitehead"
    #         stringArr = word.split(" ")
    #         firstString = stringArr[0][0] + "." #gets first letter of first name
    #         secondString = stringArr[1] #gets second string
    #         fullString = firstString + " " + secondString
    #         return fullString

    #     try:
    #         if not os.path.exists(f"./{year-1}_{year}_player_season_totals.csv"):
    #             client.players_season_totals(
    #                 season_end_year=year, 
    #                 output_type=OutputType.CSV, 
    #                 output_file_path=f"./{year-1}_{year}_player_season_totals.csv"
    #             )
    #             time.sleep(1.85)
    #     except requests.exceptions.HTTPError as e:
    #         if e.response.status_code == 429:
    #             retry_after = e.response.headers.get("Retry-After")
    #             if retry_after:
    #                 print(f"Rate limited. Retrying after {retry_after} seconds.")
    #                 time.sleep(int(retry_after))
    #                 if not os.path.exists(f"./{year-1}_{year}_player_season_totals.csv"):
    #                     client.players_season_totals(
    #                         season_end_year=year, 
    #                         output_type=OutputType.CSV, 
    #                         output_file_path=f"./{year-1}_{year}_player_season_totals.csv"
    #                     )
    #                     time.sleep(1.85)
    #             else:
    #                 print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
    #                 time.sleep(60)
    #                 if not os.path.exists(f"./{year-1}_{year}_player_season_totals.csv"):
    #                     client.players_season_totals(
    #                         season_end_year=year, 
    #                         output_type=OutputType.CSV, 
    #                         output_file_path=f"./{year-1}_{year}_player_season_totals.csv"
    #                     )
    #                     time.sleep(1.85)
    #         else:
    #             raise

    #     # Open file with UTF-8 encoding and error handling
    #     with open(f"./{year-1}_{year}_player_season_totals.csv", 'r', encoding='utf-8', errors='replace') as file:
    #         reader = csv.reader(file, delimiter=',')
    #         next(reader)  # Skip header row
    #         rows = list(reader)
    #         rows = rows[:-1]  # Skip last row (league averages)
            
    #         for i, row in enumerate(rows):
    #             print("name from rows: " + row[1])
    #             fullString = changeToFirst(row[1])
    #             print("Player from row changed name: " + fullString)

    #             if fullString == player_name:
    #                 originAnalyzer.ftNameToActualName[player_name] = row[1]
    #                 print("Player from row: " + row[1])
    #                 if int(row[13]) > 0:
    #                     made = row[12]
    #                     attempted = row[13]
    #                     if i + 1 >= len(rows) or changeToFirst(rows[i+1][1]) != player_name:
    #                         return [int(made), int(attempted)]
    #                     else:
    #                         indicesToCheck = []
    #                         j = i+1
    #                         while j < len(rows):
    #                             if changeToFirst(rows[j][1]) == player_name:
    #                                 indicesToCheck.append(j)
    #                             j += 1

    #                         for k in range(len(indicesToCheck)):
    #                             if int(rows[k][13]) > 0:
    #                                 made += rows[k][12]
    #                                 attempted += rows[k][13]
                            
    #                         if row[1] not in originAnalyzer.actualNameToSeasonAverages:
    #                             originAnalyzer.actualNameToSeasonAverages[row[1]] = {year: [int(made), int(attempted)]}
    #                         else:
    #                             originAnalyzer.actualNameToSeasonAverages[row[1]][year] = [int(made), int(attempted)]

    #                         return [int(made), int(attempted)]
    #                 return "No free throws"
    #         return None

        #will return array where first bucket is dictionary of minutes to minute averages and second bucket is dictionary of minutes to yearly averages
    def calculateMinuteAndYearlyAverages(self, year):
        atMinuteAverages = dict() #maps minutes to their minute averages (of all fts at that minute)
        atMinuteYearlyAverages = dict()

        for key in self.minutes:
            
            minuteAverage = self.minutes[key][0] / (self.minutes[key][0] + self.minutes[key][1])  #total made / total made + total missed
            atMinuteAverages[key] = minuteAverage * 100 #to get percentage

            playerLength = len(list(self.minutes[key][2]))

            numerator = 0

            denominator = 0

            for key2 in self.minutes[key][2]:
                numerator += self.minutes[key][2][key2][0] * self.minutes[key][2][key2][1]
                denominator += self.minutes[key][2][key2][0]
            
            atMinuteYearlyAverages[key] = float(numerator / denominator)

            #numerator  = attempted * percentage of player

            #denominator = sum of total attempts

            # players = list(self.minutes[key][2])
            # totalNumberPlayers = len(players)
            # for i in range(totalNumberPlayers): #looping through set of players that shot fts at each minute
            #     currPlayerName = players[i] #curr player
            #     print("Looking for: " + "|" + str(currPlayerName) + "|")
            #     # print(str(data))
            #     # print(str(self.get_player_ft_pct(data, "Joel Embid")))
            #     # exit()
            #     # print("looking for: " + str(currPlayerName))
            #     madeAttemptedArr = self.year_get_player_ft_pct(currPlayerName, year, originAnalyzer)
            #     if madeAttemptedArr != "No free throws" and madeAttemptedArr is not None:
            #         # print("returned: " + str(returned))
            #         total_made += madeAttemptedArr[0]
            #         total_attempted += madeAttemptedArr[1]

            # averageFTPercentageForAllPlayersAtMinute = totalPercentage / totalNumberPlayers

            # atMinuteYearlyAverages[key] = (total_made / total_attempted) * 100
        
        return [atMinuteAverages, atMinuteYearlyAverages]
    
    def get_player_ft_pct(self, player_name, year): 
        #number_repeated represents how many consequetive times a player's ft average comes from another team
        # print("playername: " + player_name)
        def changeToFirst(word):
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
                time.sleep(1.85)
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
                        time.sleep(1.85)
                else:
                    print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                    time.sleep(60)  # Default wait time if Retry-After header is missing
                    if not os.path.exists(f"./{year-1}_{year}_player_season_totals.csv"):
                        client.players_season_totals(
                            season_end_year=year, 
                            output_type=OutputType.CSV, 
                            output_file_path=f"./{year-1}_{year}_player_season_totals.csv"
                        )
                        time.sleep(1.85)
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
            time.sleep(1.85)
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
                    time.sleep(1.85)
            else:
                print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                time.sleep(60)  # Default wait time if Retry-After header is missing
                if not os.path.exists(f"./{year-1}_{year}_season.csv"):
                    client.season_schedule(
                        season_end_year=year,
                        output_type=OutputType.CSV,
                        output_file_path=f"./{year-1}_{year}_season.csv"
                    )
                    time.sleep(1.85)
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


def process_season_stats(folder_path: str) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Process basketball statistics from multiple seasons (1999-2024) and calculate overall averages.
    
    Args:
        folder_path (str): Path to the folder containing the season data files
        
    Returns:
        Tuple[Dict[str, float], Dict[str, float]]: Two dictionaries containing:
            1. Average minutes per player number across all seasons
            2. Average yearly statistics per player number across all seasons
    """
    # Initialize dictionaries to store sums and counts for averaging
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
        
        try:
            # Process minute averages
            with open(minute_file, 'r') as f:
                minute_data = json.loads(f.read())
                for min, percetnage in minute_data.items():
                    if min not in minute_sums:
                        minute_sums[min] = 0
                        minute_counts[min] = 0
                    minute_sums[min] += percetnage
                    minute_counts[min] += 1
            
            # Process yearly averages
            with open(yearly_file, 'r') as f:
                yearly_data = json.loads(f.read())
                for yrmin, per in yearly_data.items():
                    if yrmin not in yearly_sums:
                        yearly_sums[yrmin] = 0
                        yearly_counts[yrmin] = 0
                    yearly_sums[yrmin] += per
                    yearly_counts[yrmin] += 1
                    
        except FileNotFoundError:
            print(f"Warning: Could not find data files for season {season}")
            continue
        except json.JSONDecodeError:
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

    def set_default(obj):
        if isinstance(obj, set):
            return list(obj)
        raise TypeError

    total_neg = 0
    total_made = 0
    total_attempted = 0

    #VITAL, only commented for a sec for testing
    for year in range(2000, 2025):
        # Check if both files already exist
        minute_averages_file = os.path.join('dataForEachYear', f'minute_averages_{year-1}-{year}.txt')
        yearly_averages_file = os.path.join('dataForEachYear', f'yearly_averages_{year-1}-{year}.txt')

        # minute_total_dict_file = f"all_minute_total_dict_file_{year-1}-{year}"
        
        #comment this out to produce new documents for minute and minute yearly avgs at minutes (or delete exisitng ones)
        # if os.path.exists(minute_averages_file) and os.path.exists(yearly_averages_file):
        #     print(f"Files for {year-1}-{year} already exist, skipping...")
        #     continue
            
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
                    yearAnalyzer.process_team_games(allTeams[key], curr_date[0], curr_date[1], curr_date[2])
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
                        time.sleep(2.0) #for just this one we will sleep for longer to not get rate limited
                        continue
                print("processed game")
        print(f"Total neg at {year}:" + str(yearAnalyzer.total_negative_minutes))
        total_neg += yearAnalyzer.total_negative_minutes
        print(f"Totl made at {year}" + str(yearAnalyzer.total_made))
        total_made += yearAnalyzer.total_made
        print(f"Total attempted at {year}" + str(yearAnalyzer.total_attempted))
        total_attempted += yearAnalyzer.total_attempted
        yearlyAnsArr = yearAnalyzer.calculateMinuteAndYearlyAverages(year)
        yearlyMinuteAveragesDict = yearlyAnsArr[0]
        yearlyMinuteYearlyAveragesDict = yearlyAnsArr[1]

        # Save dictionaries to text files
        with open(minute_averages_file, 'w') as f:
            json.dump(yearlyMinuteAveragesDict, f, indent=4)
        
        with open(yearly_averages_file, 'w') as f:
            json.dump(yearlyMinuteYearlyAveragesDict, f, indent=4)

        # with open(minute_total_dict_file, 'w') as f:
        #     json.dump(yearAnalyzer.minutes, f, indent=4, default=set_default)

        plot_ft_percentages(yearlyMinuteAveragesDict, yearlyMinuteYearlyAveragesDict, year-1, year, yearAnalyzer.total_made, yearAnalyzer.total_attempted)
        
        #stop after one year to check large
        # break







    
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
            json.dump(minute_averages, f, indent=4)
        
    with open(all_yearly_averages_file, 'w') as f:
        json.dump(yearly_averages, f, indent=4)

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

    print("Total neg from 2000-2024: " + str(analyzer.total_negative_minutes))
    print("Total made from 2000-2024:" + str(analyzer.total_made))
    print("Total made from 2000-2024" + str(analyzer.total_attempted))

    print()

    plot_ft_percentages(minute_averages, yearly_averages, 2000, 2024, total_made, total_attempted)

    exit()

if __name__ == '__main__':
    main()