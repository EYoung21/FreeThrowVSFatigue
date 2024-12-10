import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import stats
import json
import os

# Read and parse the JSON data from the correct directory
data_dir = 'dataForEachYear'
with open(os.path.join(data_dir, 'attempt_counter_1997-1998.txt'), 'r') as f:
    attempts_data = json.load(f)
    
with open(os.path.join(data_dir, 'minute_averages_1997-1998.txt'), 'r') as f:
    minute_averages = json.load(f)
    
with open(os.path.join(data_dir, 'yearly_averages_1997-1998.txt'), 'r') as f:
    yearly_averages = json.load(f)

if not os.path.exists('dataForEachYear'):
    os.makedirs('dataForEachYear')

# Convert and sort minutes, ensuring integer keys
minutes = sorted([float(k) for k in minute_averages.keys()])
ft_percentages = [minute_averages[str(int(m)) if m.is_integer() else str(m)] for m in minutes]
yearly_percentages = [yearly_averages[str(int(m)) if m.is_integer() else str(m)] for m in minutes]
differences = [ft_percentages[i] - yearly_percentages[i] for i in range(len(minutes))]

# Create and save difference averages
diff_df = pd.DataFrame({
    'Minute': minutes,
    'Difference': differences
})
diff_df.to_csv(os.path.join('dataForEachYear', 'difference_averages_1997-1998.txt'), index=False)

# Calculate regression statistics
slope, intercept, r_value, p_value, std_err = stats.linregress(ft_percentages, yearly_percentages)

# Save regression stats
with open('1997-1998_regression_stats.txt', 'w') as f:
    f.write("Analysis for 1997-1998 NBA Seasons\n")
    f.write("="*40 + "\n\n")
    f.write("Linear Regression Between Minute FT% and Yearly FT%:\n")
    f.write(f"  Slope: {slope:.4f}\n")
    f.write(f"  Intercept: {intercept:.4f}\n")
    f.write(f"  R-squared: {r_value**2:.4f}\n")
    f.write(f"  P-value: {p_value:.4e}\n")
    f.write(f"  Standard Error: {std_err:.4f}\n")

regression_line = slope * np.array(ft_percentages) + intercept

# Save regression analysis
regression_df = pd.DataFrame({
    'Minute_FT%': ft_percentages,
    'Yearly_FT%': yearly_percentages,
    'Regression_Predicted': regression_line
})
regression_df.to_csv('1997-1998_regression_analysis.csv', index=False)

# Save full dataset
df = pd.DataFrame({
    'Minute': minutes,
    'Minute_Average_FT%': ft_percentages,
    'Season_Average_FT%': yearly_percentages,
    'Difference': differences
})
df.to_csv('1997-1998_ft_percentage_data.csv', index=False)

# Calculate trend lines
slope_ft, intercept_ft, r_value_ft, p_value_ft, std_err_ft = stats.linregress(minutes, ft_percentages)
line_ft = slope_ft * np.array(minutes) + intercept_ft

slope_yearly, intercept_yearly, r_value_yearly, p_value_yearly, std_err_yearly = stats.linregress(minutes, yearly_percentages)
line_yearly = slope_yearly * np.array(minutes) + intercept_yearly

slope_diff, intercept_diff, r_value_diff, p_value_diff, std_err_diff = stats.linregress(minutes, differences)
line_diff = slope_diff * np.array(minutes) + intercept_diff

# Create regression plot first
plt.figure(figsize=(6, 6))
plt.scatter(ft_percentages, yearly_percentages, color='blue', alpha=0.5)
plt.plot(ft_percentages, regression_line, 'm--', 
        label=f'Regression (R²: {r_value**2:.4f})', linewidth=2)
plt.xlabel('Minute FT%', fontsize=12)
plt.ylabel('Season Average FT%', fontsize=12)
plt.title('Regression: Minute FT% vs Season Average FT%')
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()
plt.tight_layout()
plt.savefig('1997-1998_regression_plot.png', bbox_inches='tight', dpi=300)
plt.close()

# Create percentage analysis plot
plt.figure(figsize=(12, 8))
plt.plot(minutes, ft_percentages, 'b-', label='Actual FT% at minute', linewidth=2)
plt.plot(minutes, yearly_percentages, 'g-', label='Players\' Season Average', linewidth=2)
plt.plot(minutes, differences, 'r-', label='Difference', linewidth=2)
plt.plot(minutes, line_ft, 'b:', label=f'FT% Trend (slope: {slope_ft:.4f})', linewidth=1)
plt.plot(minutes, line_yearly, 'g:', label=f'Season Avg Trend (slope: {slope_yearly:.4f})', linewidth=1)
plt.plot(minutes, line_diff, 'r:', label=f'Difference Trend (slope: {slope_diff:.4f})', linewidth=1)

stats_text = f'Regression Statistics:\nSlope: {slope:.4f}\nIntercept: {intercept:.4f}\nR²: {r_value**2:.4f}'
plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
        verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))

# Calculate total attempts and makes from the loaded data
total_attempts = sum(attempts_data.values())
total_makes = sum(v * minute_averages[k] / 100 for k, v in attempts_data.items())
percentage = round(total_makes/total_attempts * 100, 2) if total_attempts > 0 else ""

plt.title(f'Free Throw Percentage by Minutes Played for 1997-1998 Season\nFTA: {total_attempts}, FTs Made: {int(total_makes)}, %: {percentage}%', 
          fontsize=14, pad=20)
plt.xlabel('Minutes Played', fontsize=12)
plt.ylabel('Free Throw Percentage', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')
plt.axhline(y=0, color='k', linestyle='-', alpha=0.1)
plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1f}%'.format(y)))
plt.tight_layout()
plt.savefig('1997-1998_ft_percentage_analysis.png', bbox_inches='tight', dpi=300)
plt.close()