# # from basketball_reference_web_scraper import client
# # from basketball_reference_web_scraper.data import OutputType, Team

# # # # Get all 2017-2018 regular season player box scores for Russell Westbrook
# # # print("Getting 2017-2018 regular season player box scores for Russell Westbrook")
# # # print(client.regular_season_player_box_scores(player_identifier="westbru01", season_end_year=2018))

# # # # Get all 2017-2018 regular season player box scores for Russell Westbrook in JSON format
# # # print("Getting 2017-2018 regular season player box scores for Russell Westbrook in JSON format")
# # # print(client.regular_season_player_box_scores(player_identifier="westbru01", season_end_year=2018, output_type=OutputType.JSON))

# # # # Output all 2017-2018 regular season player box scores for Russell Westbrook in JSON format to 2017_2018_russell_westbrook_regular_season_box_scores.json
# # # print("Writing 2017-2018 regular season player box scores for Russell Westbrook to JSON file")
# # # client.regular_season_player_box_scores(player_identifier="westbru01", season_end_year=2018, output_type=OutputType.JSON, output_file_path="./2017_2018_russell_westbrook_regular_season_box_scores.json")

# # # # Output all 2017-2018 regular season player box scores for Russell Westbrook in CSV format to 2017_2018_russell_westbrook_regular_season_box_scores.csv
# # # print("Writing 2017-2018 regular season player box scores for Russell Westbrook to CSV file")
# # # client.regular_season_player_box_scores(player_identifier="westbru01", season_end_year=2018, output_type=OutputType.CSV, output_file_path="./2017_2018_russell_westbrook_regular_season_box_scores.csv")





# # # game = client.play_by_play(
# # #             home_team=Team.BOSTON_CELTICS,
# # #             year=2023,
# # #             month=10,
# # #             day=27
# # #         )

# # # for i in range(len(game)):
# # #     print(game[i])





# # # client.players_season_totals(
# # #     season_end_year=2018, 
# # #     output_type=OutputType.JSON, 
# # #     output_file_path="./2017_2018_player_season_totals.json"
# # # )

# # import time
# # import requests
# # from basketball_reference_web_scraper import client

# # # def get_season_stats_with_retry(season_end_year=2024):
# # #     try:
# # #         # Attempt to get the season stats
# # #         season_stats = client.players_season_totals(season_end_year=season_end_year)
# # #         print(str(season_stats))
# # #     except requests.exceptions.HTTPError as e:
# # #         # Check if it's a 429 error
# # #         if e.response.status_code == 429:
# # #             # Get the Retry-After header, if available
# # #             retry_after = e.response.headers.get("Retry-After")
# # #             if retry_after:
# # #                 # If Retry-After is in seconds, wait that long
# # #                 print(f"Rate limited. Retrying after {retry_after} seconds.")
# # #                 time.sleep(int(retry_after))
# # #                 # Retry the request
# # #                 return get_season_stats_with_retry(season_end_year)
# # #             else:
# # #                 print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
# # #                 time.sleep(60)  # Default wait time if Retry-After header is missing
# # #                 return get_season_stats_with_retry(season_end_year)
# # #         else:
# # #             # Re-raise if it's a different HTTP error
# # #             raise

# # # # Call the function
# # # get_season_stats_with_retry(season_end_year=2024)




# # try:
# #     sch = client.season_schedule(
# #     season_end_year=2023,
# #     )

# #     # print(str(sch))
# # except requests.exceptions.HTTPError as e:
# #     if e.response.status_code == 429:
# #         # Get the Retry-After header, if available
# #         retry_after = e.response.headers.get("Retry-After")
# #         if retry_after:
# #             # If Retry-After is in seconds, wait that long
# #             print(f"Rate limited. Retrying after {retry_after} seconds.")
# #             time.sleep(int(retry_after))
# #             # Retry the request
# #             sch = client.season_schedule(
# #             season_end_year=2024, 
# #             )

# #             # print(str(sch))
# #         else:
# #             print("Rate limited. No Retry-After header found. Waiting 60 seconds before retrying.")
# #             time.sleep(60)  # Default wait time if Retry-After header is missing
# #             sch = client.season_schedule(
# #             season_end_year=2024,
# #             )

# #             # print(str(sch))
# #     else:
# #         raise


# # for game in sch:
# #     if game['home_team'] == Team.BOSTON_CELTICS:
# #         print(game)

# # #testing verison of main below to test rate limits


# # # import time
# # # from requests.exceptions import HTTPError

# # # def test_single_game():
# # #     print("Testing access to a single game...")
# # #     try:
# # #         # Try with a 2022 game instead (older data might be more accessible)
# # #         game = client.play_by_play(
# # #             home_team=Team.BOSTON_CELTICS,
# # #             year=2023,
# # #             month=10,
# # #             day=27
# # #         )
        
# # #         print("Successfully accessed game!")
# # #         print("\nFirst 5 plays:")
# # #         for play in game[:5]:
# # #             print(play)
            
# # #     except HTTPError as e:
# # #         if "429" in str(e):
# # #             print("Rate limit hit. Need to wait longer between requests")
# # #             print("Trying again in 60 seconds...")
# # #             time.sleep(60)
# # #             try:
# # #                 client.play_by_play(
# # #                     home_team=Team.BOSTON_CELTICS, 
# # #                     year=2023, month=10, day=27, 
# # #                     output_type=OutputType.JSON
# # #                 )
# # #                 print("Success on second attempt!")
# # #             except Exception as e2:
# # #                 print(f"Second attempt failed: {e2}")
# # #         else:
# # #             print(f"Error: {e}")

# # # def main():
# # #     test_single_game()

# # # if __name__ == '__main__':
# # #     main()









# # from basketball_reference_web_scraper import client

# # # Try a recent completed season
# # season_stats = client.players_season_totals(season_end_year=2015)

# # print(str(season_stats))



# import csv
# from basketball_reference_web_scraper import client
# import time
# import requests
# from basketball_reference_web_scraper.data import Team, OutputType
# from datetime import datetime
# from typing import Dict, List, Set
# import math
# from basketball_reference_web_scraper.data import Team, Location
# import matplotlib.pyplot as plt
# import numpy as np
# from datetime import datetime, timedelta
# import csv
# import pytz
# import pandas as pd
# from bs4 import BeautifulSoup
# def get_player_ft_pct(player_name): 
#         #number_repeated represents how many consequetive times a player's ft average comes from another team
        
#         with open("./2023_2024_player_season_totals.csv") as file:
#             reader = csv.reader(file, delimiter=',')
#             # Skip the header row
#             next(reader)
#             #indcies 12 and 13 are made and attempted respectively
#             for i, row in enumerate(reader):
#                 # player_row = row[0]
#                 if row[0] == player_name:
#                     if row[13] > 0:# avoid division by zero
#                         made = row[12]
#                         attempted = row[13]
#                         if reader[i+1][0] != player_name:
#                             print("player only appeared once")
#                             return (made / attempted) * 100 #calculates average
#                         else:
#                             indicesToCheck = []
#                             j = i+1
#                             while j < len(reader):
#                                 if reader[j][0] == player_name:
#                                     indicesToCheck.append(j)
#                                 j += 1

#                             for k in range(len(indicesToCheck)):
#                                 if reader[k][13] > 0:
#                                     made += reader[k][12]
#                                     attempted += reader[k][13]
#                             print("player was traded mid season")
#                             return (made / attempted) * 100
#             return None #if player requested wasn't in season stats


# print(get_player_ft_pct("Giannis Antetokounmpo"))


def changeToFirst(word):
            if word == "Scotty Pippen Jr.": #edge case with scotty pippen Jr.
                return "S. Pippen "
            if word == "Sasha Vezenkov":
                return "A. Vezenkov"
            if word == "Dariq Whitehead":
                return "D. Miller-Whitehead"

            stringArr = word.split(" ")
            firstString = stringArr[0][0] + "." #gets first letter of first name
            secondString = stringArr[1] #gets second string
            fullString = firstString + " " + secondString

            return fullString

print(changeToFirst("Hunter Tyson"))