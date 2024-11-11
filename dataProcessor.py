from basketball_reference_web_scraper import client
from basketball_reference_web_scraper.data import Team, OutputType
from datetime import datetime
from typing import Dict, List, Set
import math
from basketball_reference_web_scraper import client
from basketball_reference_web_scraper import client
from basketball_reference_web_scraper.data import Team, Location
import matplotlib.pyplot as plt
import numpy as np

class FreeThrowAnalyzer:
    def __init__(self):
        self.processed_games: Set[str] = set()
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
            
            game_id = f"{year}{month:02d}{day:02d}_{team}"
            if game_id not in self.processed_games:
                self._process_game_data(pbp_data, game_id)
                self.processed_games.add(game_id)
        except Exception as e:
            print(f"Error processing game {team} on {year}-{month}-{day}: {e}")
    
    def _process_game_data(self, pbp_data: List[dict]):
        """Process play by play data to extract free throw attempts and player minutes."""
        player_entry_times = {}  # Track when players entered the game
        
        playersThatSubbedOut = set()

        for play in pbp_data:
            
            # Track substitutions
            if 'ENTERS' in str(play.get('description', '')):
                desParsed = play['description'].split(' ENTERS')
                player_in = desParsed[0]
                desParsed2 = desParsed.split('for ')

                playersThatSubbedOut.add(desParsed2[1])

                player_entry_times[player_in] = play.get('time_seconds')
                        
            # Track free throws
            if 'FREE THROW' in str(play.get('description', '')):
                player = play['description'].split(' ')[0]

                if player in playersThatSubbedOut:
                    continue #we only want to track the first stretch of playing time

                entry_time = player_entry_times.get(player)

                minutes_played = (entry_time - play.get('time_seconds', 0)) / 60
                
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

    def get_player_ft_pct(self, player_name, season_stats):
        for player in season_stats:
            if player['name'] == player_name:
                # Calculate FT%
                if player['free_throws_attempted'] > 0:  # avoid division by zero
                    ft_pct = (player['free_throws_made'] / player['free_throws_attempted']) * 100
                    return ft_pct
        return None
        
        #will return array where first bucket is dictionary of minutes to minute averages and second bucket is dictionary of minutes to yearly averages
    def calculateMinuteAndYearlyAverages(self):
        atMinuteAverages = dict() #maps minutes to their minute averages (of all fts at that minute)
        atMinuteYearlyAverages = dict()

        season_stats = client.players_season_totals(season_end_year=2024)

        for i in range(len(self.minutes)): #minute would be i (index + 1)
            minuteAverage = self.minutes[i+1][0] / self.minutes[i+1][0] + self.minutes[i+1][1]  #total made / total made + total missed
            atMinuteAverages[i+1] = minuteAverage

            totalPercentage = 0
            totalPlayers = len(self.minutes[i+1][2])
            for i in range(totalPlayers): #looping through set of players that shot fts at each minute
                currPlayerName = self.minutes[i+1][2][i] #curr player
                totalPercentage += self.get_player_ft_pct(self, currPlayerName, season_stats)

            averageFTPercentageForAllPlayersAtMinute = totalPercentage / totalPlayers

            atMinuteYearlyAverages[i+1] = averageFTPercentageForAllPlayersAtMinute
        
        return [atMinuteAverages, atMinuteYearlyAverages]
    


def get_team_home_dates(team, schedule):
    return [game['start_time'].date() for game in schedule if game['home_team'] == team]

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

    allTeams = ["Celtics", "Nets", "Knicks", "76ers", "Raptors", "Bulls", "Cavaliers", "Pistons", "Pacers", "Bucks", "Hawks", "Hornets", "Heat", "Magic", "Wizards", "Nuggets", "Timberwolves", "Thunder", "Trail Blazers", "Jazz", "Warriors", "Clippers", "Lakers", "Suns", "Kings", "Mavericks", "Rockets", "Grizzlies", "Pelicans", "Spurs"]

    schedule = client.season_schedule(season_end_year=2024)

    for team in allTeams:
        arrHomeDates = get_team_home_dates(team, schedule)
        for date in arrHomeDates:
            dateArr = date.split("-") #YYYY-MM-DD
            analyzer.process_team_games(team, dateArr[0], dateArr[1], dateArr[2]) #team, year, month, day

    ansArr = analyzer.calculateMinuteAndYearlyAverages()
    
    minuteAveragesDict = ansArr[0]

    minuteYearlyAveragesDict = ansArr[1]

    print("minuteAvg: " + str(minuteAveragesDict)) #empty for some reason?

    print("minuteYearlyAvg: " + str(minuteYearlyAveragesDict)) #empty for some reason?

    plot_ft_percentages(minuteAveragesDict, minuteYearlyAveragesDict)

    exit()

if __name__ == '__main__':
    main()
