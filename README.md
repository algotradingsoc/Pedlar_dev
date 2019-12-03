# Pedlar_dev
New pedlar under development. This is NOT the official version that has support 

# Existing issues with pedlar

Currently, there are three major problems in pedlar that we need to address. 
 
Order management: Agents are allowed to have losing money orders open for an indefinite amount of time and thus leaderboard performance is inflated. 
Multi-asset trading: Pedlar supports GBP/USD trading only and there is a need to expand to other FX pairs and US Equities.
Dependencies: Agents relies on the pedlar server running to have price data and it can only be accessed through college network. Running pedlar relies on WebSockets and OO programming which might be not familiar to our members. This increases the burden of Tech support. 
Solution 1: Agents now instead provide target asset holdings at each price update which the portfolio will be rebalanced accordingly. Agents will not make direct buy and sell orders. 
 
Solution2: IEX and TrueFX data will be used.
 
Solution3: Pedlar2 will have fewer dependencies and supports local running. Students can generate local backtesting or live trading results without using any part of the college network. This lightweight version allows students to deploy their agent on Google-colab or Heroku for free without too much work. Another advantage is that instead of the need to support running programs on each laptop with different OS settings, it is easier to provide support on programs run on Google-colab since the machine settings are standardised. 
 
Pedlar2 will be provided as a python package with more streamlined API. Agents now provide functions instead of inheriting the base Agent class as the low level buy and sell functions can be moved to the backend. This can prevent users from cheating or modifying the Agent class attributes in an unwanted way.
 
Agents simply need to provide two functions, Universe selection and OnData. Universe selection returns a list of assets in IEX and TrueFX that the agent will trade. OnData is a function that maps the current price history, portfolio and trades made to target holdings.  
 
There will be risk limits of how much an agent can short. Errors will be raised if the limit is breached. This encourages students to think about risk management which is important. 
 
In pedlar2, the portfolio is now the centre of the trade agents as students are required to give target holdings. Each agent will start with the same amount of cash. Long an asset will reduce the cash balance and add the stock to the current portfolio, shorting an asset will increase the cash balance and add the negative holdings to the portfolio. 
At each timestamp, the portfolio value is the weighted sum of holdings with cash. The risk limit is determined by the absolute sum of holdings.  The exact implementation will be provided later. 
 
The building of data history, rebalancing of portfolio and keeping trade records are now done by the package at the backend. 
 

