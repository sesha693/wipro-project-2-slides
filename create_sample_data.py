import pandas as pd
from pathlib import Path

data = {
    'Revenue': pd.DataFrame({
        'ADH': ['Prachi', 'Other', 'TeamA'],
        'Account': ['Microsoft', 'Google', 'Amazon'],
        'Q1’27': [20.9, 10.0, 15.2],
        'Q2’27 Target': [21, 15, 18],
        'Q2’27': [15.6, 12.0, 16.5],
        'Pipeline': [0, 2, 1],
        'Locked-In': [0, 1, 2],
        'Risk': [0, 0.5, 1],
    }),
    'NTE': pd.DataFrame({
        'ADH': ['Prachi', 'Other', 'TeamA'],
        'Actuals': [10, 8, 9],
        'Target': [12, 9, 10],
        'People cost': [4, 3, 4],
        'Non-people cost': [6, 5, 5],
        'Total': [10, 8, 9],
        'Prev Week People Cost': [3, 2, 2],
        'Prev Week Non-People Cost': [5, 4, 4],
        'Curr Week People Cost': [4, 3, 3],
        'Curr Week Non-People Cost': [6, 5, 6],
    }),
    'GM': pd.DataFrame({
        'ADH': ['Prachi', 'Other', 'TeamA'],
        'Q1’27 Actuals': [0.35, 0.30, 0.33],
        'Q2’27 Target': [0.4, 0.35, 0.38],
        'WK01 P&L': [0.38, 0.33, 0.36],
        'WK02 P&L': [0.39, 0.34, 0.37],
        'Delta': [0.01, -0.02, 0.03],
        'WOW': [0.02, -0.01, 0.01],
        'GM Forecast': [0.41, 0.37, 0.39],
    }),
}
output_path = Path(__file__).resolve().parent / 'sample_data' / 'sample_input.xlsx'
output_path.parent.mkdir(parents=True, exist_ok=True)
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    for sheet_name, df in data.items():
        df.to_excel(writer, sheet_name=sheet_name, index=False)
print(f'Created {output_path}')
