# Purpose of project

The pupose of this project is to try and predict if a trading strategy will win or loss. I see a lot of times that people try to do basic time series analyis, using models like LSTM to predict exact prices but never get real results other wise everyone would be a millionaire overnight as these models are extremely easy to duplicate.

I purpose a hypothesis that we can actually gain useful classifications of whether or not we will loose or win a trade based off of a set of rules for a trading strategy.

# Steps to duplicate for other trading strategies. 

- Create a backtesting bot that can gather trade data through a csv file of high, low, open, close, data. 
- Use the csv file and create new features that can help increase a models predictive power
- Use model in realtime senarios using the MT5 trading api. (MT5 api works very well with python)
