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
            time.sleep(3.1)

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
    
    def _process_game_data(self, pbp_data: List[dict]): #we'll have to get the data by quarters, because each quarter resets at 12:00
        """Process play by play data to extract free throw attempts and player minutes."""
        player_entry_times = {}  # Track when players entered the game

        playersThatSubbedOut = set()

        for play in pbp_data:
            # print(play.get('description', ''))
            # continue
            # exit()
            # Track substitutions
            if 'enters' in str(play.get('description', '')):
                desParsed = play['description'].split(' enters')
                # print(str(desParsed))
                # exit()
                player_in = desParsed[0]
                desParsed2 = desParsed[1].split('for ')

                playersThatSubbedOut.add(desParsed2[1])
                
                player_entry_times[player_in] = self.calculateConvertedIGT(play.get('remaining_seconds_in_period'), play.get('period'))
                #calculateConvertedIGT will convert from remaining seconds in period + quarter to current minute in game
                        
            # Track free throws
            if 'free throw' in str(play.get('description', '')):
                if 'makes' in play['description']:
                    player = play['description'].split(' makes')[0]
                if 'misses' in play['description']:
                    player = play['description'].split(' misses')[0]

                if player in playersThatSubbedOut:
                    continue #we only want to track the first stretch of playing time
                
                if player not in player_entry_times: #they were a starter
                    player_entry_times[player] = "0" #they came into the game at 0 minutes

                entry_time = player_entry_times.get(player)

                print("entry time:" + str(entry_time))

                print("Converted time at freethrow: " + str(self.calculateConvertedIGT(play.get('remaining_seconds_in_period'), play.get('period'))))

                # exit()

                minutes_played = (self.calculateConvertedIGT(play.get('remaining_seconds_in_period'), play.get('period')) - float(entry_time))
                
                curr_minute = math.floor(minutes_played)

                if curr_minute not in self.minutes:
                    if 'makes' in play['description']: #the player made the freethrow, they're now 1 for 1
                        self.minutes[curr_minute] = [1, 0, set()] #total made, total missed, players at this minute
                        self.minutes[curr_minute][2].add(player) #adds player to set if not already in it
                    else: #the freethrow was missed
                        self.minutes[curr_minute] = [0, 1, set()] #they're 0 for 1
                        self.minutes[curr_minute][2].add(player)
                else: #the minute already was instantiated
                    if 'misses' in play['description']: #the player made the freethrow, they're now 1 for 1
                        self.minutes[curr_minute][0] += 1 #adds a make
                        self.minutes[curr_minute][2].add(player) #adds player to set if not already in it
                    else: #the freethrow was missed
                        self.minutes[curr_minute][1] += 1 #adds a miss
                        self.minutes[curr_minute][2].add(player)

    def calculateConvertedIGT(self, remainingSecondsInQuarter, quarter): #remaining seconds, quarter (1, 2, 3, 4)
        # print("remaining seconds: " + str(remainingSecondsInQuarter))
        # print("quarter: " + str(quarter))
        # exit()
        
        remainingMinutes = remainingSecondsInQuarter / 60
        minutesPlayedInQuarter = 12 - remainingMinutes

        if str(quarter) == "1":
            return minutesPlayedInQuarter
        elif str(quarter) == "2":
            return 12 + minutesPlayedInQuarter
        elif str(quarter) == "3":
            return 24 + minutesPlayedInQuarter
        elif str(quarter) == "4":
            return 36 + minutesPlayedInQuarter



    def get_player_ft_pct(self, player_name, season_stats): 
        #number_repeated represents how many consequetive times a player's ft average comes from another team
        
        for i in range(len(season_stats)):
            player = season_stats[i]
            if player['name'] == player_name:
                # Calculate FT%
                if player['free_throws_attempted'] > 0:  # avoid division by zero
                    made = player['free_throws_made']
                    missed = player['free_throws_attempted']
                    if season_stats[i+1]['name'] != player_name:
                        return (made / (made+missed)) * 100 #calculates average
                    else: #handles case where player played on different teams in a year (got traded?)
                        indicesToCheck = []
                        j = i+1
                        while j < len(season_stats):
                            if season_stats[j]['name'] == player_name:
                                indicesToCheck.append(j)
                            j += 1

                        for k in range(len(indicesToCheck)):
                            if season_stats[k]['free_throws_attempted'] > 0:
                                made += season_stats[k]['free_throws_made']
                                missed += season_stats[k]['free_throws_attempted']

                        return (made / (made+missed)) * 100

        return None #if player requested wasn't in season stats
        
        #will return array where first bucket is dictionary of minutes to minute averages and second bucket is dictionary of minutes to yearly averages
    def calculateMinuteAndYearlyAverages(self):
        # print("minutes: " + str(self.minutes))
        #this didn't print anything ??

        atMinuteAverages = dict() #maps minutes to their minute averages (of all fts at that minute)
        atMinuteYearlyAverages = dict()

        try:
            season_stats = client.players_season_totals(season_end_year=2024)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Get the Retry-After header, if available
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    # If Retry-After is in seconds, wait that long
                    print(f"Rate limited. Retrying after {retry_after} seconds.")
                    time.sleep(int(retry_after))
                    # Retry the request
                    season_stats = client.players_season_totals(season_end_year=2024)
                else:
                    print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
                    time.sleep(60)  # Default wait time if Retry-After header is missing
                    season_stats = client.players_season_totals(season_end_year=2024)
            else:
                # Re-raise if it's a different HTTP error
                raise


        for i in range(len(self.minutes)): #minute would be i (index + 1)
            minuteAverage = self.minutes[i+1][0] / self.minutes[i+1][0] + self.minutes[i+1][1]  #total made / total made + total missed
            atMinuteAverages[i+1] = minuteAverage * 100 #to get percentage

            totalPercentage = float(0)
            players = list(self.minutes[i+1][2])
            totalNumberPlayers = len(players)
            for i in range(totalNumberPlayers): #looping through set of players that shot fts at each minute
                currPlayerName = players[i] #curr player
                totalPercentage += float(self.get_player_ft_pct(currPlayerName, season_stats))

            averageFTPercentageForAllPlayersAtMinute = totalPercentage / totalNumberPlayers

            atMinuteYearlyAverages[i+1] = averageFTPercentageForAllPlayersAtMinute
        
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
    print("Writing games for 2017-2018 season to CSV file")
    # endYear = 2024
    # client.season_schedule(season_end_year=endYear, output_type=OutputType.CSV, output_file_path=f"./{endYear-1}_{endYear}_season.csv")
    # time.sleep(3.1)



    #commented for a sec for testing
    # for key in allTeams:
    #     # below, "team" should be in this format: "Team.BOSTON_CELTICS"
    #     arrHomeDates = get_team_home_dates(key)
    #     print("currTeam: " + str(key))
    #     print("homedates: " + str(arrHomeDates))

    #     for date in arrHomeDates:
    #         # print("here!")
    #         curr_date = date.split("-")
    #         analyzer.process_team_games(allTeams[key], curr_date[0], curr_date[1], curr_date[2]) #team, year, month, day
    #         print("minutes: " + str(analyzer.minutes))

        
        
    #set default value (to wait between calls to avoid rate limits) and then google exponetial backoff


    # minuteAverages = calculateMinuteAverages()
    analyzer.minutes = {2: [11, 30, {'W. Matthews', 'T. Young', 'C. Braun', 'A. Burks', 'Z. Williams', 'M. Turner', 'D. Sharpe', 'O. Okongwu', 'N. Batum', 'M. Bagley', 'J. Johnson', 'M. Robinson', 'M. Morris', 'D. Barlow', 'D. Mitchell', 'P. Reed', 'D. Smith', 'J. Smith', 'S. Lundy', 'J. Embiid', 'B. Bogdanović', 'S. Bey'}], 3: [4, 21, {'W. Matthews', 'T. Young', 'L. Walker', 'S. Lundy', 'R. Barrett', 'C. Capela', 'J. Embiid', 'N. Claxton', 'S. Gilgeous-Alexander', 'M. Bridges', 'B. Bogdanović', 'D. House', 'S. Bey', 'D. Sharpe'}], 6: [4, 16, {'B. Wesley', 'R. Barrett', 'O. Toppin', 'T. Lyles', 'O. Okongwu', 'D. Hunter', 'B. Bogdanović', 'T. Maxey', 'S. Dinwiddie', 'N. Alexander-Walker', 'S. Bey', 'B. Mathurin'}], 8: [4, 12, {'K. Kuzma', 'C. Capela', 'J. Embiid', 'D. Murray', 'B. Bogdanović', 'C. Cunningham', 'S. Bey'}], 0: [5, 14, {'W. Matthews', 'D. Smith', 'B. Fernando', 'O. Okongwu', 'P. Baldwin', 'D. Hunter', 'S. Gilgeous-Alexander', 'D. Barlow', 'D. House', 'I. Hartenstein', 'J. Williams'}], 9: [4, 6, {'K. Lowry', 'J. Randle', 'B. Bogdanović', 'P. Banchero', 'S. Bey'}], 1: [7, 19, {'W. Matthews', 'J. Smith', 'B. Fernando', 'K. Caldwell-Pope', 'J. Embiid', 'O. Okongwu', 'C. Capela', 'R. Gobert', 'M. Bridges', 'C. Porter', 'J. Johnson'}], 4: [7, 15, {'E. Omoruyi', 'P. Beverley', 'C. Capela', 'O. Okongwu', 'J. Richardson', 'D. Murray', 'B. Bogdanović', 'M. Bridges', 'M. Turner', 'J. Williams', 'G. Mathews', 'Z. Nnaji'}], 5: [5, 17, {'O. Toppin', 'H. Highsmith', 'C. Capela', 'R. Rollins', 'O. Okongwu', 'B. Bogdanović', 'K. Oubre', 'A. Nesmith', 'K. Johnson', 'S. Bey', 'J. Johnson'}], 13: [0, 2, {'B. Bogdanović', 'A. Edwards'}], 7: [4, 18, {'J. Ivey', 'B. Coulibaly', 'J. Embiid', 'O. Okongwu', 'D. Hunter', 'S. Gilgeous-Alexander', 'M. Bridges', 'S. Merrill', 'S. Bey'}], 11: [2, 7, {'J. Randle', 'M. Monk', 'B. Bogdanović', 'M. Bridges', 'S. Bey'}], 15: [1, 1, {'S. Gilgeous-Alexander', 'J. Randle'}], 17: [1, 0, {'J. Embiid'}], 10: [3, 9, {'O. Okongwu', 'S. Gilgeous-Alexander', 'B. Bogdanović', 'M. Bridges', 'B. Mathurin'}], -29: [1, 1, {'M. Bridges'}], 16: [1, 1, {'S. Gilgeous-Alexander'}]}
    ansArr = analyzer.calculateMinuteAndYearlyAverages()
    
    minuteAveragesDict = ansArr[0]

    minuteYearlyAveragesDict = ansArr[1]

    # print("minuteAvg: " + str(minuteAveragesDict)) #empty for some reason?

    # print("minuteYearlyAvg: " + str(minuteYearlyAveragesDict)) #empty for some reason?

    plot_ft_percentages(minuteAveragesDict, minuteYearlyAveragesDict)

    exit()

if __name__ == '__main__':
    main()