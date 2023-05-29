# Trading Strategy Outcome Prediction

## Introduction
This project is an attempt to predict the outcome (win or loss) of a trading strategy. While many approaches focus on precise time-series predictions using models like LSTM, this project adopts a unique perspective. Instead of predicting exact prices, we are developing a model that classifies whether a particular trading strategy will result in a win or loss based on a specific set of rules.

The hypothesis we put forward is that, instead of predicting specific price points, useful insights can be obtained by focusing on classifications of trade outcomes. To narrow down the scope, we are examining trades separately, distinguishing between buy trades and sell trades.

Our focus is on day trading, particularly on strategies utilizing 1-minute and 5-minute time frames. This is because we need thousands of trades for robust analysis and model building.

## Replicating the Project

If you'd like to replicate this project for other trading strategies, here are the steps:

1. **Backtesting Bot**: Create a backtesting bot capable of gathering high, low, open, and close data, outputting the results to a CSV file.
2. **Feature Creation**: Use the CSV file data to create new features that could enhance a model's predictive power.
3. **Real-time Implementation**: Implement the model in real-world scenarios using the MT5 trading API. (The MT5 API works very well with Python)

## Potential Challenges

You may encounter the following challenges:

1. **Data Insufficiency**: One of the most significant challenges is the lack of sufficient data. For example, an attempt to build a model for a MACD cross-over strategy on a 5-minute interval yielded only about 700 trades over seven years. The dearth of data led to poor predictive performance and, when multiple features were introduced, overfitting became a serious issue despite the use of cross-validation.
2. **Imbalanced Dataset**: Another challenge to consider is the prevalence of imbalanced datasets. Depending on the risk to reward settings of your trading strategy, you may find that you have significantly more wins or losses. This imbalance needs to be appropriately addressed during model development.

## Conclusion

This project aims to shift focus from predicting exact future prices to identifying whether a trading strategy will be successful. Emphasis is placed on having sufficient data and managing imbalanced datasets to build a robust and effective predictive model.
