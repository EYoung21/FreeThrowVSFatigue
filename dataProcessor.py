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

class FreeThrowAnalyzer:
    def __init__(self):
        # self.processed_games: Set[str] = set()
        self.minutes = dict()
        #each minute should have a total made and total missed
        #AND a an average of each player's yearly ft % that is included in the above
        #      - we can accomplish this by keeping a set of players that show freethrows during this consequetive minute
        #      - and also then calculating the whole average after we're done parsing data (Made / made + missed)
            
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
            time.sleep(1)

            # print("play by play: " + str(pbp_data))
            # exit()


            # print("playByPlay dara: " + str(pbp_data))
            
            # game_id = f"{year}{month:02d}{day:02d}_{team}"
            # if game_id not in self.processed_games:
            self._process_game_data(pbp_data)
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
                    return self.process_team_games(team, year, month, day)
                else:
                    print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                    time.sleep(60)  # Default wait time if Retry-After header is missing
                    return self.process_team_games(team, year, month, day)
            else:
                print(f"Error processing game {team} on {year}-{month}-{day}: {e}")
                raise
    
    def _process_game_data(self, pbp_data: List[dict]):
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
                if 'makes' in play['description']:
                    player = play['description'].split(' makes')[0]
                if 'misses' in play['description']:
                    player = play['description'].split(' misses')[0]

                if player in playersThatSubbedOut:
                    continue

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
            # exit()
            

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


    
    def get_player_ft_pct(self, player_name): 
        #number_repeated represents how many consequetive times a player's ft average comes from another team
        
        def changeToFirst(word):
            stringArr = word.split(" ")
            firstString = stringArr[0][0] + "." #gets first letter of first name
            secondString = stringArr[1] #gets second string
            fullString = firstString + " " + secondString
            return fullString



        with open("./2023_2024_player_season_totals.csv") as file:
            reader = csv.reader(file, delimiter=',')
            # Skip the header row
            next(reader)
            rows = list(reader)
            #indcies 12 and 13 are made and attempted respectively
            for i, row in enumerate(rows):
                # player_row = row[0]
                fullString = changeToFirst(row[1])
                # print(fullString)
                # exit()

                if fullString == player_name:
                    if int(row[13]) > 0: # avoid division by zero
                        made = row[12]
                        attempted = row[13]
                        if i + 1 >= len(rows) or changeToFirst(rows[i+1][1]) != player_name:
                            # print("player only appeared once")
                            return float((int(made) / int(attempted))) * 100 #calculates average
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
                            return float((int(made) / int(attempted))) * 100
            return None #if player requested wasn't in season stats

        # for i in range(len(season_stats)):
        #     player = season_stats[i]
        #     if player['name'] == player_name:
        #         # Calculate FT%
        #         if player['free_throws_attempted'] > 0:  # avoid division by zero
        #             made = player['free_throws_made']
        #             missed = player['free_throws_attempted']
        #             if season_stats[i+1]['name'] != player_name:
        #                 return (made / (made+missed)) * 100 #calculates average
        #             else: #handles case where player played on different teams in a year (got traded?)
        #                 indicesToCheck = []
        #                 j = i+1
        #                 while j < len(season_stats):
        #                     if season_stats[j]['name'] == player_name:
        #                         indicesToCheck.append(j)
        #                     j += 1

        #                 for k in range(len(indicesToCheck)):
        #                     if season_stats[k]['free_throws_attempted'] > 0:
        #                         made += season_stats[k]['free_throws_made']
        #                         missed += season_stats[k]['free_throws_attempted']

        #                 return (made / (made+missed)) * 100

        # return None #if player requested wasn't in season stats

        #will return array where first bucket is dictionary of minutes to minute averages and second bucket is dictionary of minutes to yearly averages
    def calculateMinuteAndYearlyAverages(self):
        # print("minutes: " + str(self.minutes))
        #this didn't print anything ??
        # year = 2024

        # exit()

        atMinuteAverages = dict() #maps minutes to their minute averages (of all fts at that minute)
        atMinuteYearlyAverages = dict()

        try:
            client.players_season_totals(
                season_end_year=2024, 
                output_type=OutputType.CSV, 
                output_file_path="./2023_2024_player_season_totals.csv"
            )
            time.sleep(1)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Get the Retry-After header, if available
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    # If Retry-After is in seconds, wait that long
                    print(f"Rate limited. Retrying after {retry_after} seconds.")
                    time.sleep(int(retry_after))
                    # Retry the request
                    client.players_season_totals(
                        season_end_year=2024, 
                        output_type=OutputType.CSV, 
                        output_file_path="./2023_2024_player_season_totals.csv"
                    )
                else:
                    print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                    time.sleep(60)  # Default wait time if Retry-After header is missing
                    client.players_season_totals(
                        season_end_year=2024, 
                        output_type=OutputType.CSV, 
                        output_file_path="./2023_2024_player_season_totals.csv"
                    )
            else:
                # Re-raise if it's a different HTTP error
                raise

        # exit()

        # print("seasonstats: " + str(season_stats))

        #https://www.basketball-reference.com/leagues/NBA_2024_totals.html
        #could maybe parse the above url to get seaosn stats (more specifically yearly ft % for specific players in 2023-24)


        for key in self.minutes: #minute would be i (index + 1)
            #self.minutes[i+1] may not be the first minute, ex if 1 was not in it, TODO: need to change this
            minuteAverage = self.minutes[key][0] / (self.minutes[key][0] + self.minutes[key][1])  #total made / total made + total missed
            atMinuteAverages[key] = minuteAverage * 100 #to get percentage

            totalPercentage = float(0)
            players = list(self.minutes[key][2])
            totalNumberPlayers = len(players)
            for i in range(totalNumberPlayers): #looping through set of players that shot fts at each minute
                currPlayerName = players[i] #curr player
                # print("|" + str(currPlayerName) + "|")
                # print(str(data))
                # print(str(self.get_player_ft_pct(data, "Joel Embid")))
                # exit()
                # print("looking for: " + str(currPlayerName))
                totalPercentage += float(self.get_player_ft_pct(currPlayerName))

            averageFTPercentageForAllPlayersAtMinute = totalPercentage / totalNumberPlayers

            atMinuteYearlyAverages[key] = averageFTPercentageForAllPlayersAtMinute
        
        return [atMinuteAverages, atMinuteYearlyAverages]
    


def get_team_home_dates(team):
    # Open the file and create the reader
    with open("./2023_2024_season.csv") as file:
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

def plot_ft_percentages(minute_averages, yearly_averages):
    # Get all minutes (x-axis)
    minutes = sorted(minute_averages.keys())

    print(minutes)
    
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
    df.to_csv('ft_percentage_data.csv', index=False)
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    # Plot each line
    plt.plot(minutes, ft_percentages, 'b-', label='Actual FT% at minute', linewidth=2)
    plt.plot(minutes, yearly_percentages, 'g-', label='Players\' Season Average', linewidth=2)
    plt.plot(minutes, differences, 'r--', label='Difference', linewidth=2)
    
    # Customize the plot
    plt.title('Free Throw Percentage by Minutes Played', fontsize=14)
    plt.xlabel('Minutes Played', fontsize=12)
    plt.ylabel('Free Throw Percentage', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10)
    
    # Add a horizontal line at y=0 for reference in difference
    plt.axhline(y=0, color='k', linestyle='-', alpha=0.1)
    
    # Format y-axis as percentage
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1f}%'.format(y)))
    
    # Save the plot
    plt.savefig('ft_percentage_analysis.png')
    plt.show()

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

    #it's possible that we will have to manually create the date of home games for each team for the entire season
    # print("Writing games for 2017-2018 season to CSV file")
    # endYear = 2024
    # client.season_schedule(season_end_year=endYear, output_type=OutputType.CSV, output_file_path=f"./{endYear-1}_{endYear}_season.csv")
    # time.sleep(3.1)



    # commented for a sec for testing
    for key in allTeams:
        # below, "team" should be in this format: "Team.BOSTON_CELTICS"
        arrHomeDates = get_team_home_dates(key)
        print("currTeam: " + str(key))
        # print("homedates: " + str(arrHomeDates))

        for date in arrHomeDates:
            # print("here!")
            curr_date = date.split("-")
            analyzer.process_team_games(allTeams[key], curr_date[0], curr_date[1], curr_date[2]) #team, year, month, day
            # print("minutes: " + str(analyzer.minutes))
            print("processed game")
        # break
    print("minutesDict: " + str(analyzer.minutes))
        
        
    #set default value (to wait between calls to avoid rate limits) and then google exponetial backoff


    # minuteAverages = calculateMinuteAverages()
    # analyzer.minutes = {2: [57, 15, {'D. Hunter', 'J. Embiid', 'S. Bey', 'D. Mitchell', 'T. Young', 'D. Sharpe', 'O. Okongwu', 'S. Barnes', 'J. Johnson', 'M. Robinson', 'C. Braun', 'M. Flynn', 'Z. Williams', 'C. Capela', 'P. Reed', 'W. Matthews', 'A. Pokusevski', 'N. Batum', 'S. Lundy', 'J. Tatum', 'D. Smith', 'G. Mathews', 'M. Bagley', 'M. Turner', 'A. Reaves', 'D. Bertāns', 'A. Burks', 'P. Pritchard', 'M. Morris', 'D. Barlow', 'T. Horton-Tucker', 'J. Smith', 'B. Bogdanović'}], 3: [50, 7, {'J. Embiid', 'B. Podziemski', 'S. Bey', 'T. Young', 'D. House', 'D. Sharpe', 'O. Okongwu', 'L. Walker', 'C. Metu', 'N. Claxton', 'M. Flynn', 'R. Barrett', 'S. Gilgeous-Alexander', 'L. James', 'C. Capela', 'M. Plumlee', 'W. Matthews', 'D. Booker', 'S. Lundy', 'G. Mathews', 'M. Bridges', 'T. Forrest', 'J. Brown', 'B. Bogdanović', 'D. Murray'}], 6: [31, 8, {'D. Hunter', 'B. Mathurin', 'N. Alexander-Walker', 'S. Bey', 'O. Toppin', 'B. Wesley', 'O. Okongwu', 'J. Butler', 'R. Rupert', 'M. Flynn', 'R. Barrett', 'J. Ivey', 'T. Maxey', 'K. Leonard', 'T. Lyles', 'S. Dinwiddie', 'T. Horton-Tucker', 'B. Bogdanović', 'G. Santos', 'D. White', 'C. Anthony'}], 8: [26, 9, {'J. Embiid', 'J. Porter', 'M. Brown', 'S. Bey', 'C. Cunningham', 'J. Allen', 'B. Fernando', 'C. Boucher', 'N. Richards', 'B. Bogdanović', 'K. Kuzma', 'B. Miller', 'D. Murray', 'C. Capela'}], 0: [24, 10, {'D. Hunter', 'W. Matthews', 'J. Landale', 'O. Okongwu', 'D. Barlow', 'J. Isaac', 'D. Smith', 'J. Johnson', 'B. Fernando', 'T. Mann', 'D. House', 'B. Bogdanović', 'J. Williams', 'K. Leonard', 'B. Lopez', 'I. Hartenstein', 'S. Gilgeous-Alexander', 'P. Baldwin'}], 9: [13, 5, {'D. Booker', 'P. Banchero', 'S. Bey', 'K. Lowry', 'B. Fernando', 'B. Bogdanović', 'J. Randle', 'M. Flynn', 'R. Hachimura'}], 1: [35, 15, {'D. Hunter', 'J. Embiid', 'O. Okongwu', 'J. Johnson', 'Z. Williamson', 'L. James', 'C. Capela', 'A. Pokusevski', 'W. Matthews', 'M. Bridges', 'L. Kornet', 'C. Porter', 'B. Fernando', 'J. Nurkić', 'J. Smith', 'K. Caldwell-Pope', 'J. Hood-Schifino', 'D. Murray', 'R. Gobert'}], 4: [29, 11, {'D. Hunter', 'J. Porter', 'M. Brown', 'S. Bey', 'P. Beverley', 'T. Young', 'D. Wade', 'O. Okongwu', 'S. Curry', 'C. Capela', 'N. Powell', 'G. Mathews', 'M. Turner', 'J. Richardson', 'Z. Nnaji', 'E. Omoruyi', 'M. Bridges', 'B. Bogdanović', 'J. Williams', 'D. Murray'}], 5: [29, 9, {'D. Hunter', 'S. Bey', 'O. Toppin', 'A. Nesmith', 'K. Oubre', 'O. Okongwu', 'J. Johnson', 'R. Rollins', 'C. Capela', 'J. Tatum', 'A. Reaves', 'K. Leonard', 'K. Bufkin', 'B. Fernando', 'T. Horton-Tucker', 'K. Johnson', 'H. Highsmith', 'B. Bogdanović', 'D. Murray'}], 13: [1, 1, {'A. Edwards', 'B. Bogdanović'}], 7: [31, 7, {'D. Hunter', 'J. Embiid', 'O. Okongwu', 'C. Capela', 'G. Dick', 'S. Bey', 'S. Merrill', 'D. Murray', 'J. Ivey', 'K. Porziņģis', 'B. Fernando', 'J. Duren', 'B. Coulibaly', 'S. Gilgeous-Alexander', 'M. Bridges', 'F. Wagner'}], 11: [15, 1, {'D. Hunter', 'S. Bey', 'D. Murray', 'B. Fernando', 'B. Bogdanović', 'J. Randle', 'M. Monk', 'M. Bridges'}], 15: [2, 0, {'S. Gilgeous-Alexander', 'J. Randle'}], 17: [1, 0, {'J. Embiid'}], 10: [16, 4, {'B. Mathurin', 'O. Okongwu', 'G. Dick', 'S. Bey', 'J. Butler', 'B. Bogdanović', 'S. Gilgeous-Alexander', 'M. Bridges'}], -29: [2, 0, {'M. Bridges'}], 16: [6, 1, {'D. Booker', 'D. Murray', 'S. Gilgeous-Alexander', 'K. Leonard'}], 14: [1, 0, {'D. Booker'}], 18: [0, 1, {'M. Bridges'}], 37: [2, 0, {'W. Matthews'}]}
    ansArr = analyzer.calculateMinuteAndYearlyAverages()
    
    minuteAveragesDict = ansArr[0]

    minuteYearlyAveragesDict = ansArr[1]

    print("minuteAvg: " + str(minuteAveragesDict)) #empty for some reason?

    print("minuteYearlyAvg: " + str(minuteYearlyAveragesDict)) #empty for some reason?

    print()

    plot_ft_percentages(minuteAveragesDict, minuteYearlyAveragesDict)

    exit()

if __name__ == '__main__':
    main()