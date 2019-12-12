import pandas as pd
import numpy as np

pd.set_option('use_inf_as_na', True)

def sharpe_ratio(pnlhist,riskless=0):
    returns = pd.Series(pnlhist).pct_change().dropna()
    expected_returns = np.mean(returns) * 252 
    volatility = np.std(returns) * np.sqrt(252)
    sharpe = (expected_returns - riskless)/volatility 
    return sharpe




