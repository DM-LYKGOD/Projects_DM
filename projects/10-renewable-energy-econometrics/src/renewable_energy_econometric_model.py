from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "energy_transition_model_data.xlsx"

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Missing input data: {DATA_PATH}. Place the workbook in the project's data directory."
    )

data = pd.ExcelFile(DATA_PATH).parse("Sheet1")

# Interpolate missing numeric data for Capital and Labour
data['Capital'] = data['Capital'].interpolate(method='linear', limit_direction='both')
data['Labour'] = data['Labour'].interpolate(method='linear', limit_direction='both')
data['RE share of electricity capacity (%)'] = data['RE share of electricity capacity (%)'].interpolate(method='linear', limit_direction='both')

# Select relevant columns and drop rows with missing values
selected_data = data[['Year', 'GDP', 'Capital', 'Labour', 'RE share of electricity capacity (%)']].dropna()

# Log-transform the relevant variables
selected_data['ln_GDP'] = selected_data['GDP'].apply(lambda x: np.log(x))
selected_data['ln_Capital'] = selected_data['Capital'].apply(lambda x: np.log(x))
selected_data['ln_Labour'] = selected_data['Labour'].apply(lambda x: np.log(x))
selected_data['ln_RE_Share'] = selected_data['RE share of electricity capacity (%)'].apply(lambda x: np.log(x))

# Define the independent variables (add constant for intercept)
X = selected_data[['ln_Capital', 'ln_Labour', 'ln_RE_Share']]
X = sm.add_constant(X)

# Define the dependent variable
y = selected_data['ln_GDP']

# Perform the regression
model = sm.OLS(y, X).fit()

# Summarize the results
print(model.summary())

