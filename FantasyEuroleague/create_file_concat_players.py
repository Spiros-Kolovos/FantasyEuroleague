import pandas as pd

df_players_prev_season = pd.read_csv('Players_season_2023_2024.csv', sep=';')
df_players_curr_season = pd.read_csv('Players_season_2024_2025.csv', sep=';')

# Step 1: Concatenate the two DataFrames
df_concat = pd.concat([df_players_prev_season, df_players_curr_season])

# Step 2: Remove duplicate players (keeping only the last occurrence)
df_concat = df_concat.drop_duplicates(subset=['Player'], keep='last')

# Step 3: Keep only 'Player' and 'Pos' columns
df_concat = df_concat[['Player', 'Pos']]

# Step 4: Rename 'Player' column to 'PlayerName' to match the first table
df_concat.rename(columns={'Player': 'PlayerName'}, inplace=True)

# Step 5: Save dataframe to csv file
df_concat.to_csv('Concatenated_players.csv')