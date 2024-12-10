import json
import os

# Initialize dictionary to store total attempts per minute
total_attempts = {}

# Process each season's attempt counter file
for year in range(1997, 2024):
    season = f"{year}-{year+1}"
    filename = os.path.join('dataForEachYear', f'attempt_counter_{season}.txt')
    
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            
            # Add attempts for each minute to total
            for minute, attempts in data.items():
                if minute not in total_attempts:
                    total_attempts[minute] = 0
                total_attempts[minute] += attempts
                
    except FileNotFoundError:
        print(f"File not found: {filename}")
        continue
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {filename}")
        continue

# Sort by minute (convert to int for proper numerical sorting)
sorted_attempts = dict(sorted(total_attempts.items(), key=lambda x: int(x[0])))

# Save the combined data
output_file = "attempt_counter_1997-2024.txt"
with open(output_file, 'w') as f:
    json.dump(sorted_attempts, f, indent=4)

print(f"Combined attempt counter saved to {output_file}")