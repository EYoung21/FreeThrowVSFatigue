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

class FreeThrowAnalyzer:
    def __init__(self):
        # self.processed_games: Set[str] = set()
        self.minutes:Set[int] = set()
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
        #TODO: need to get info on starters for each game and their entry times to the above dictionary somehow

        playersThatSubbedOut = set()

        for play in pbp_data:
            
            # Track substitutions
            if 'ENTERS' in str(play.get('description', '')):
                desParsed = play['description'].split(' ENTERS')
                player_in = desParsed[0]
                desParsed2 = desParsed.split('for ')

                playersThatSubbedOut.add(desParsed2[1])
                
                player_entry_times[player_in] = self.calculateConvertedIGT(play.get('remaining_seconds_in_period'), play.get('period'))
                #calculateConvertedIGT will convert from remaining seconds in period + quarter to current minute in game
                        
            # Track free throws
            if 'FREE THROW' in str(play.get('description', '')):
                player = play['description'].split(' ')[0]

                if player in playersThatSubbedOut:
                    continue #we only want to track the first stretch of playing time
                
                if player not in player_entry_times: #they were a starter
                    player_entry_times[player] = "0" #they came into the game at 0 minutes

                entry_time = player_entry_times.get(player)

                minutes_played = (entry_time - self.calculateConvertedIGT(play.get('remaining_seconds_in_period'), play.get('period')))
                
                curr_minute = math.floor(minutes_played)

                if curr_minute not in self.minutes:
                    if 'MAKES' in play['description']: #the player made the freethrow, they're now 1 for 1
                        self.minutes[curr_minute] = [1, 0, set()] #total made, total missed, players at this minute
                        self.minutes[curr_minute][2].add(player) #adds player to set if not already in it
                    else: #the freethrow was missed
                        self.minutes[curr_minute] = [0, 1, set()] #they're 0 for 1
                        self.minutes[curr_minute][2].add(player)
                else: #the minute already was instantiated
                    if 'MAKES' in play['description']: #the player made the freethrow, they're now 1 for 1
                        self.minutes[curr_minute][0] += 1 #adds a make
                        self.minutes[curr_minute][2].add(player) #adds player to set if not already in it
                    else: #the freethrow was missed
                        self.minutes[curr_minute][1] += 1 #adds a miss
                        self.minutes[curr_minute][2].add(player)

    def calculateConvertedIGT(self, remainingSecondsInQuarter, quarter): #remaining seconds, quarter (1, 2, 3, 4)
        remainingMinutes = remainingSecondsInQuarter / 60
        minutesPlayedInQuarter = 12 - remainingMinutes

        if quarter == "1":
            return minutesPlayedInQuarter
        elif quarter == "2":
            return 12 + minutesPlayedInQuarter
        elif quarter == "3":
            return 24 + minutesPlayedInQuarter
        elif quarter == "4":
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

            totalPercentage = 0
            totalPlayers = len(self.minutes[i+1][2])
            for i in range(totalPlayers): #looping through set of players that shot fts at each minute
                currPlayerName = self.minutes[i+1][2][i] #curr player
                totalPercentage += self.get_player_ft_pct(self, currPlayerName, season_stats, False)

            averageFTPercentageForAllPlayersAtMinute = totalPercentage / totalPlayers

            atMinuteYearlyAverages[i+1] = averageFTPercentageForAllPlayersAtMinute
        
        return [atMinuteAverages, atMinuteYearlyAverages]
    


def get_team_home_dates(team):
    # Open the file and create the reader
    with open("./2023_2024_season.csv") as file:
        reader = csv.reader(file, delimiter=',')
        # Skip the header row
        next(reader)
        
        # Initialize the dates list
        dates = []
        
        # Loop through each row in the CSV
        for row in reader:
            print("we're here!")
            # Check if the team is the home team
            print("in column home team: " + str(row[3]))
            print("inputed team: " + str(team))
            if row[3] == team:  # Assuming home team is in the 4th column (index 3)
                print("checked!")
                # Append the date part of the start_time column to dates
                dates.append(row[0].split(" ")[0])
        
    return dates

def plot_ft_percentages(minute_averages, yearly_averages):
    # Get all minutes (x-axis)
    minutes = sorted(minute_averages.keys())
    
    # Get corresponding values for each line
    ft_percentages = [minute_averages[m] for m in minutes]
    yearly_percentages = [yearly_averages[m] for m in minutes]
    differences = [ft_percentages[i] - yearly_percentages[i] for i in range(len(minutes))]
    
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
    # client.season_schedule(season_end_year=2024, output_type=OutputType.CSV, output_file_path="./2023_2024_season.csv")
    # exit()

    print("here!")

    for key in allTeams:
        # below, "team" should be in this format: "Team.BOSTON_CELTICS"
        arrHomeDates = get_team_home_dates(key)
        print("currTeam: " + str(key))
        print("homedates: " + str(arrHomeDates))

        for date in arrHomeDates:
            curr_date = date.split("-")
            analyzer.process_team_games(allTeams[key], curr_date[0], curr_date[1], curr_date[2]) #team, year, month, day

            #set default value (to wait between calls to avoid rate limits) and then google exponetial backoff


    # minuteAverages = calculateMinuteAverages()
    
    ansArr = analyzer.calculateMinuteAndYearlyAverages()
    
    minuteAveragesDict = ansArr[0]

    minuteYearlyAveragesDict = ansArr[1]

    # print("minuteAvg: " + str(minuteAveragesDict)) #empty for some reason?

    # print("minuteYearlyAvg: " + str(minuteYearlyAveragesDict)) #empty for some reason?

    plot_ft_percentages(minuteAveragesDict, minuteYearlyAveragesDict)

    exit()

if __name__ == '__main__':
    main()