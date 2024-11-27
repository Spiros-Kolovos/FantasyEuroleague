# Load the libraries
from euroleague_api.EuroLeagueData import EuroLeagueData
from euroleague_api.boxscore_data import BoxScoreData

import pandas as pd
pd.set_option('future.no_silent_downcasting', True)

# Firstly, we need to do some Data processing
# First of all, we download the data which contain all statistics

previous_season = 2023
current_season = 2024
game_code = 1
competition_code = "E"

season_data = EuroLeagueData(competition_code)
df_season_data_previous = season_data.get_game_metadata_season(season=previous_season)
df_season_data_current = season_data.get_game_metadata_season(season=current_season)

df_season_data_previous['season'] = previous_season
df_season_data_current['season'] = current_season

df_season_data = pd.concat([df_season_data_previous, df_season_data_current])

# Combine the 'date' and 'time' columns into a single column
df_season_data['datetime'] = df_season_data['date'] + ' ' + df_season_data['time']

# Convert the combined column into a datetime object
df_season_data['datetime'] = pd.to_datetime(df_season_data['datetime'], format='%b %d, %Y %H:%M')

# drop date, time
df_season_data.drop(['date', 'time'], inplace=True, axis=1)

df_season_data = df_season_data.sort_values(by='datetime')

# Initialize an empty DataFrame to hold all player statistics
all_player_stats = pd.DataFrame()

boxscore = BoxScoreData(competition_code)

# Iterate over the matches DataFrame
for _, row in df_season_data.iterrows():
    season = row['season']
    gamenumber = row['gamenumber']
    
    # Fetch player statistics for the current game using boxscore.get_boxscore_data
    player_stats = boxscore.get_player_boxscore_stats_data(season=season, gamecode = gamenumber)
    
    # Assuming player_stats is already a DataFrame, or you can convert it to one
    # Append the fetched statistics to the all_player_stats DataFrame
    all_player_stats = pd.concat([all_player_stats, player_stats], ignore_index=True)
    
    print('Gamenumber: ', gamenumber, 'Season: ', season)

# Display the final DataFrame with all player statistics
print(all_player_stats)

# Replace 'DNP' in the 'Minutes' column with '00:00' and convert them to float
all_player_stats.loc[:, 'Minutes'] = all_player_stats['Minutes'].replace('DNP', '00:00')

# Convert minutes variable to float
def convert_minutes_to_float(minutes_str):
    # Split the string by colon into minutes and seconds
    minutes, seconds = map(int, minutes_str.split(':'))
    
    # Convert to total minutes as a float (seconds are converted to fraction of minutes)
    total_minutes = minutes + seconds / 60
    
    # Round to two decimal places
    return round(total_minutes, 2)

# Apply the conversion function to the 'Minutes' column
all_player_stats['Minutes'] = all_player_stats['Minutes'].apply(convert_minutes_to_float)

# Next data processing steps:
# 1. Remove data that is not of a single player (i.e., Team, Total)
all_player_stats = all_player_stats[~all_player_stats['Player_ID'].isin(['Total', 'Team'])]

# 2. Add the position of each player and remove players that do not have position
# To add the position, you need to load the 'concatenated_players.csv' file, which is the combined
# files of 'players_season_2023_2024.csv' and 'players_season_2024_2025.csv'. 

df_concat = pd.read_csv('Concatenated_players.csv', sep=';', index_col=False)
df_concat = df_concat.loc[:, ~df_concat.columns.str.contains('^Unnamed')]

# Function to convert "LASTNAME, FIRSTNAME" to "F. Lastname"
def format_name(name):
    last, first = name.split(', ')
    return f"{first[0]}. {last.capitalize()}"

all_player_stats.loc[:,'PlayerName'] = all_player_stats['Player'].apply(format_name)

# Perform a left merge on the 'PlayerName' column
all_player_stats = pd.merge(all_player_stats, df_concat, on='PlayerName', how='left')

# 3. Add the team score and opponent score
# Step 1: Create the 'gamecode' column in all_player_stats
all_player_stats['gamecode'] = 'E' + all_player_stats['Season'].astype(str) + '_' + all_player_stats['Gamecode'].astype(str)

# Step 2: Merge the all_player_stats with df_season_data on the 'gamecode' column
all_player_stats = pd.merge(all_player_stats, df_season_data[['group', 'homescore', 'awayscore', 'datetime', 'gamecode']], on='gamecode', how='left')

# Step 3: Assign TeamScore and OpponentScore based on the 'Home' column
# If Home == 1, TeamScore = homescore, OpponentScore = awayscore
# If Home == 0, TeamScore = awayscore, OpponentScore = homescore
all_player_stats['TeamScore'] = all_player_stats.apply(
    lambda row: row['homescore'] if row['Home'] == 1 else row['awayscore'], axis=1
)
all_player_stats['OpponentScore'] = all_player_stats.apply(
    lambda row: row['awayscore'] if row['Home'] == 1 else row['homescore'], axis=1
)

# Drop the homescore and awayscore columns, as they are no longer needed
all_player_stats = all_player_stats.drop(columns=['homescore', 'awayscore'])

# 4. Caclulate the fantasy points 
def fp_calculation(row):
    # Calculating the base fantasy points based on the given formula
    fantasy_points = (
        row['Points'] 
        + row['TotalRebounds'] 
        + row['Assistances'] 
        + row['Steals'] 
        - row['Turnovers'] 
        + row['BlocksFavour'] 
        - row['BlocksAgainst'] 
        + row['FoulsReceived']
        - row['FoulsCommited'] 
        - (row['FreeThrowsAttempted'] - row['FreeThrowsMade']) 
        - (row['FieldGoalsAttempted2'] - row['FieldGoalsMade2']) 
        - (row['FieldGoalsAttempted3'] - row['FieldGoalsMade3'])
    )
    
    # If the player's team wins, increase the fantasy points by 10%
    if row['TeamScore'] > row['OpponentScore']:
        fantasy_points += 0.1 * abs(fantasy_points)  # Add 10% bonus if the team wins

    return fantasy_points

all_player_stats['total_fp'] = all_player_stats.apply(fp_calculation, axis=1)


