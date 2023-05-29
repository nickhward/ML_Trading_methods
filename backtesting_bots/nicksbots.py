import pandas as pd
import numpy as np 
import Indicators
import yfinance as yf
import datetime
import seaborn as sns
import matplotlib.pyplot as plt
from time import sleep
import MetaTrader5 as mt5
import pandas_ta as ta

class NicksBots:
    def __init__(self):
        self.accountBalance = 200_000
        self.risk = 0.01
        self.pipValue = 10

    def _get_mt5_data(self, ticker: str, timeFrame: str) -> pd.DataFrame:
        if not mt5.initialize():
            print("initialize() failed, error code =",mt5.last_error())
            quit()
        
        time_dict = {
            '1m' : mt5.TIMEFRAME_M1,
            '3m' : mt5.TIMEFRAME_M3,
            '5m' : mt5.TIMEFRAME_M5,
            '15m' : mt5.TIMEFRAME_M15,
            '1h' : mt5.TIMEFRAME_H1,
            '1d' : mt5.TIMEFRAME_D1,
        }

        rates = mt5.copy_rates_from_pos(ticker, time_dict[timeFrame], 0, 30_000)
        df = pd.DataFrame(rates)
        print(df)
        df['Time'] = pd.to_datetime(df['time'], unit='s')
        renameCols = {'close' : 'Close', 'open' : 'Open', 'high':'High', 'low':'Low'}
        df.rename(columns=renameCols, inplace=True)
        print(df)

        return df

    
    def crossing_macd_strat(self):
  
        csvFileName = 'us30uptodate.csv'

        data = self._get_lots_data()

        data.reset_index(inplace = True)
        print(data)

        data = data.rename(columns={'Last' : 'Close'})
        print(data)

        data['Time'] = pd.to_datetime(data['Time'], format='%m/%d/%Y %H:%M')

        data = data[(data['Time'].dt.time <= datetime.time(16,0,0))]
        data = data[data['Time'].dt.time >= datetime.time(9,30,0)]
        

        macd_df = self._get_macd(data['Close'], 26, 12, 9)
        print(macd_df)
             
        data = pd.concat([data, macd_df], axis=1)
        data['SMA_200'] = Indicators.sma(data, 200)
        data['SMA_21'] = Indicators.sma(data, 21)
        data['SMA_50'] = Indicators.sma(data, 50)
        data['SMA_100'] = Indicators.sma(data, 100)
        #data['EMA_200'] = pd.Series.ewm(data['Close'], span=200).mean()
        data['EMA_200'] = data['Close'].ewm(span=200, adjust=False).mean()
        data = data.drop(data.index[range(600)])
        data['PrevDayLow'] = data['Low'].shift(1)
        data['PrevDayHigh'] = data['High'].shift(1)
        data['macdPrevDay'] = data['macd'].shift(1)
        data['signalPrevDay'] = data['signal'].shift(1)
        data['NextDayLow'] = data['Low'].shift(-1)
        data['NextDayHigh'] = data['High'].shift(-1)

        print(data)

        buyCount = 0
        sellCount = 0
        totalProfit = 0
        challengeProf = 0
        challengeProfArr = []
        totalProfitArr = []
        final_total = 0
        outcome = []
        trackSL = []
        trackTP = []
        tradeDate = []
        entryTrack = []
        trades = {}
        amounts = []
        dailyProf = 0
        orderTrack = []
        finalTotalArr = []
        emaTrack = []
        pointsTrack = []
        macdTrack = []
        signalTrack = []
        rr = 1.5
        badMonths = []
        dont_trade = False
        print(data)
        dailyLoss = 0
        openTrades = 0
        for _, row in data.iterrows():#17-22:55
            date = row['Time']
            str_date = str(date)
           
            if (row['macd'] < 0) and (row['signal'] < 0) and datetime.time(10,0,0) <= date.time() <= datetime.time(16,0,0): #Looking for a buy
                sellCount = 0
                if buyCount < 1:
                    buyCount += 1
                    currentLow = row['Low']
                else:
                    currentLow = row['Low'] if row['Low'] < currentLow else currentLow
                    buyCount+=1

                if row['macd'] < row['signal'] and row['macdPrevDay'] > row['signalPrevDay'] and (row['Close'] > row['EMA_200']):
                    sl = currentLow
                    #sl = row['SMA_200']
                    #sl = row['Low']
                    stopPips = abs(row['Close'] - sl) / 0.0001
                    lessThanOne = (row['macd'] < -1) and (row['signal'] < -1) and (row['signalPrevDay'] < -1) and (row['macdPrevDay'] < -1)
                    slPoints = abs(sl - row['Close'])
                    tp = row['Close'] + (slPoints * rr)

                    if sl == row['Low']: dont_trade = True

                    if 5 <= slPoints and dailyLoss < 1 and openTrades < 1 and lessThanOne and not dont_trade:
                        lotSize = (100 / slPoints) * 20
                        openTrades+=1
                        #tp = row['Close'] + (abs(row['Close'] - sl) * rr)
                        #lotSize = (self.accountBalance * self.risk) / (stopPips * self.pipValue)
                    
                        trades[date] = {
                            'Order' : 'BUY', 
                            'Date' : date, 
                            'Stop Loss' : sl, 
                            'Take Profit' : tp, 
                            'Stop Loss Points' : slPoints,
                            'EMA' : row['EMA_200'],
                            'Lot Size' : lotSize,
                            'Entry' : row['Close'],
                            'macd' : row['macd'],
                            'signal' : row['signal'],
                        }
                    dont_trade = False
                elif row['macd'] > row['signal'] and row['macdPrevDay'] < row['signalPrevDay'] and (row['Close'] > row['EMA_200']):
                    sl = currentLow
                    slPoints = abs(sl - row['Close'])
                    
                    lessThanOne = (row['macd'] < -1) and (row['signal'] < -1) and (row['signalPrevDay'] < -1) and (row['macdPrevDay'] < -1)
                    tp = row['Close'] + (slPoints * rr)
                    if sl == row['Low']: dont_trade = True
                    if 5 <= slPoints and dailyLoss < 1 and openTrades < 1 and lessThanOne and not dont_trade: 
                        lotSize = (100 / slPoints) * 20
                        openTrades+=1
                        trades[date] = {
                            'Order' : 'BUY', 
                            'Date' : date, 
                            'Stop Loss' : sl, 
                            'Take Profit' : tp, 
                            'Stop Loss Points' : slPoints,
                            'EMA' : row['EMA_200'],
                            'Lot Size' : lotSize,
                            'Entry' : row['Close'],
                            'macd' : row['macd'],
                            'signal' : row['signal'],
                        }
                    dont_trade = False
            
            elif (row['macd'] > 0) and (row['signal'] > 0) and datetime.time(11,0,0) <= date.time() <= datetime.time(15,0,0): #Looking for sell:
                buyCount = 0
                if sellCount < 1:
                    sellCount += 1
                    currentHigh = row['High']
                else:
                    currentHigh = row['High'] if row['High'] > currentHigh else currentHigh
                    sellCount += 1
                
                if row['macd'] < row['signal'] and row['macdPrevDay'] > row['signalPrevDay'] and (row['Close'] < row['EMA_200']):
                    sl = currentHigh
                    slPoints = abs(sl - row['Close'])
                    tp = row['Close'] - (slPoints * rr)
                    greaterThanOne = abs(row['macd'] - row['signal']) > 1
                    if sl == row['High']: dont_trade = True
                    if 5 <= slPoints and dailyLoss < 1 and openTrades < 1 and greaterThanOne and not dont_trade:
                        lotSize = (100 / slPoints) * 20
                        openTrades+=1
                        trades[date] = {
                            'Order' : 'SELL', 
                            'Date' : date,
                            'Stop Loss' : sl, 
                            'Take Profit' : tp, 
                            'Stop Loss Points' : slPoints,
                            'EMA' : row['EMA_200'],
                            'Lot Size' : lotSize,
                            'Entry' : row['Close'],
                            'macd' : row['macd'],
                            'signal' : row['signal'],
                        }
                    dont_trade = False

                elif row['macd'] > row['signal'] and row['macdPrevDay'] < row['signalPrevDay'] and (row['Close'] < row['EMA_200']):
                    sl = currentHigh
                    slPoints = abs(sl - row['Close'])
                    greaterThanOne = abs(row['macd'] - row['signal']) > 1
                    tp = row['Close'] - (slPoints * rr)
                    if sl == row['High']: dont_trade = True
                    if 5 <= slPoints and dailyLoss < 1 and openTrades < 1 and greaterThanOne and not dont_trade:
                        lotSize = (100 / slPoints) * 20
                        openTrades +=1
                        trades[date] = {
                            'Order' : 'SELL', 
                            'Date' : date, 
                            'Stop Loss' : sl, 
                            'Take Profit' : tp, 
                            'Stop Loss Points' : slPoints,
                            'Lot Size' : lotSize,
                            'EMA' : row['EMA_200'],
                            'Entry' : row['Close'],
                            'macd' : row['macd'],
                            'signal' : row['signal'],
                        }
                    dont_trade = False
                                                 
            if (row['macd'] > 0) and (row['signal'] > 0):
                buyCount = 0
            elif (row['macd'] < 0) and (row['signal'] < 0):
                sellCount = 0

            keysToRemove = []
            for key in trades:
                if trades[key]['Take Profit'] <= row['NextDayHigh'] and trades[key]['Order'] == 'BUY':
                    profit = trades[key]['Stop Loss Points'] * trades[key]['Lot Size'] * rr
                    totalProfit += profit
                    challengeProf += profit
                    dailyProf += profit
                    challengeProfArr.append(challengeProf)
                    totalProfitArr.append(totalProfit)
                    outcome.append('WIN')
                    trackSL.append(trades[key]['Stop Loss'])
                    trackTP.append(trades[key]['Take Profit'])
                    amounts.append(profit)
                    tradeDate.append(trades[key]['Date'])
                    entryTrack.append(trades[key]['Entry'])
                    orderTrack.append(trades[key]['Order'])
                    emaTrack.append(trades[key]['EMA'])
                    pointsTrack.append(trades[key]['Stop Loss Points'])
                    macdTrack.append(trades[key]['macd'])
                    signalTrack.append(trades[key]['signal'])
                    openTrades -= 1
                    keysToRemove.append(key)

                elif trades[key]['Stop Loss'] >= row['NextDayLow'] and trades[key]['Order'] == 'BUY':
                    loss = trades[key]['Stop Loss Points'] * trades[key]['Lot Size']
                    totalProfit -= loss
                    challengeProf -= loss
                    dailyProf -= loss
                    amounts.append(-loss)
                    challengeProfArr.append(challengeProf)
                    outcome.append('LOSS')
                    trackSL.append(trades[key]['Stop Loss'])
                    trackTP.append(trades[key]['Take Profit'])
                    totalProfitArr.append(totalProfit)
                    tradeDate.append(trades[key]['Date'])
                    entryTrack.append(trades[key]['Entry'])
                    orderTrack.append(trades[key]['Order'])
                    emaTrack.append(trades[key]['EMA'])
                    pointsTrack.append(trades[key]['Stop Loss Points'])
                    macdTrack.append(trades[key]['macd'])
                    signalTrack.append(trades[key]['signal'])
                    dailyLoss += 1
                    openTrades -= 1
                    
                    keysToRemove.append(key) 

                elif trades[key]['Take Profit'] >= row['NextDayLow'] and trades[key]['Order'] == 'SELL':
                    profit = trades[key]['Stop Loss Points'] * trades[key]['Lot Size'] * rr 
                    totalProfit += profit
                    challengeProf += profit
                    dailyProf += profit
                    challengeProfArr.append(challengeProf)
                    totalProfitArr.append(totalProfit)
                    outcome.append('WIN')
                    trackSL.append(trades[key]['Stop Loss'])
                    trackTP.append(trades[key]['Take Profit'])
                    amounts.append(profit)
                    tradeDate.append(trades[key]['Date'])
                    entryTrack.append(trades[key]['Entry'])
                    orderTrack.append(trades[key]['Order'])
                    emaTrack.append(trades[key]['EMA'])
                    pointsTrack.append(trades[key]['Stop Loss Points'])
                    macdTrack.append(trades[key]['macd'])
                    signalTrack.append(trades[key]['signal'])
                    openTrades -= 1

                    keysToRemove.append(key)

                elif trades[key]['Stop Loss'] <= row['NextDayHigh'] and trades[key]['Order'] == 'SELL':
                    loss = trades[key]['Stop Loss Points'] * trades[key]['Lot Size'] 
                    totalProfit -= loss
                    challengeProf -= loss
                    dailyProf -= loss
                    amounts.append(-loss)
                    challengeProfArr.append(challengeProf)
                    outcome.append('LOSS')
                    trackSL.append(trades[key]['Stop Loss'])
                    trackTP.append(trades[key]['Take Profit'])
                    totalProfitArr.append(totalProfit)
                    tradeDate.append(trades[key]['Date'])
                    entryTrack.append(trades[key]['Entry'])
                    orderTrack.append(trades[key]['Order'])
                    emaTrack.append(trades[key]['EMA'])
                    pointsTrack.append(trades[key]['Stop Loss Points'])
                    macdTrack.append(trades[key]['macd'])
                    signalTrack.append(trades[key]['signal'])
                    dailyLoss += 1
                    keysToRemove.append(key) 
                    openTrades -= 1
        
            if len(keysToRemove) > 0 : [trades.pop(key) for key in keysToRemove]
            #print(date.time())
            if date.time() == datetime.time(16,0,0):
                
                dailyProf = 0
                dailyLoss = 0
                dont_trade = False
                
                delta = datetime.timedelta(days=1)
                next_day = date + delta
                if row['Time'].month != next_day.month:
                    if totalProfit > 0:
                        final_total += totalProfit
                        finalTotalArr.append(final_total)
                        totalProfit = 0
                    challengeProf = 0
                    
                    tradeCount = 0
        print(final_total)
                

        final_dict = {
            'Outcome' : outcome,
            'Order' : orderTrack,
            'Date' : tradeDate,
            'EMA' : emaTrack,
            'Points' : pointsTrack,
            'Take Profit' : trackTP,
            'Stop Loss' : trackSL,
            'Entry' : entryTrack,
            'Amount' : amounts,
            'Profit' : totalProfitArr,
            'Challenge Profit' : challengeProfArr,
            
        }

        final_df = pd.DataFrame(final_dict)
        final_df.to_csv('macd_strat.csv')

        print(final_df['Outcome'].value_counts())
        sns.lineplot(data=final_df['Profit'])
        plt.show()
        sns.lineplot(finalTotalArr)
        plt.show()
        sns.lineplot(data=final_df['Points'])
        plt.show()

    def crossing_macd_trailing(self):
        
        csvFileName = 'us30uptodate.csv'

        data = self._get_lots_data()
        data.reset_index(inplace = True)
        print(data)

        data = data.rename(columns={'Last' : 'Close'})

        data['Time'] = pd.to_datetime(data['Time'], format='%m/%d/%Y %H:%M')

        data = data[(data['Time'].dt.time <= datetime.time(16,0,0))]
        data = data[data['Time'].dt.time >= datetime.time(9,30,0)]
       
        macd_df = self._get_macd(data['Close'], 26, 12, 9)
             
        data = pd.concat([data, macd_df], axis=1)
        data['SMA_200'] = Indicators.sma(data, 200)
        data['SMA_21'] = Indicators.sma(data, 21)
        data['SMA_50'] = Indicators.sma(data, 50)
        data['SMA_100'] = Indicators.sma(data, 100)
        data['EMA_200'] = data['Close'].ewm(span=200, adjust=False).mean()
        data = data.drop(data.index[range(600)])
        data['PrevDayLow'] = data['Low'].shift(1)
        data['PrevDayHigh'] = data['High'].shift(1)
        data['macdPrevDay'] = data['macd'].shift(1)
        data['signalPrevDay'] = data['signal'].shift(1)
        data['NextDayLow'] = data['Low'].shift(-1)
        data['NextDayHigh'] = data['High'].shift(-1)
     
        buyCount = 0
        sellCount = 0
        totalProfit = 0
        challengeProf = 0
        challengeProfArr = []
        totalProfitArr = []
        final_total = 0
        outcome = []
        trackSL = []
        trackTP = []
        tradeDate = []
        entryTrack = []
        trades = {}
        amounts = []
        dailyProf = 0
        orderTrack = []
        finalTotalArr = []
        emaTrack = []
        pointsTrack = []
        macdTrack = []
        signalTrack = []
        rr = 1.5
        badMonths = []
      
        print(data)
        dailyLoss = 0
        openTrades = 0
        no_more_trading = False
    
        for _, row in data.iterrows():#17-22:55

            date = row['Time']

            if totalProfit > 10_000: 
                no_more_trading = True
            else:
                no_more_trading = False
            if (row['macd'] < 0) and (row['signal'] < 0) and datetime.time(10,0,0) <= date.time() <= datetime.time(15,0,0) and not no_more_trading: #Looking for a buy
              
               
                sellCount = 0
                if buyCount < 1:
                    buyCount += 1
                    currentLow = row['Low']
                else:
                    currentLow = row['Low'] if row['Low'] < currentLow else currentLow
                    buyCount+=1

                if row['macd'] < row['signal'] and row['macdPrevDay'] > row['signalPrevDay'] and (row['Close'] > row['EMA_200']):
                    
                    sl = currentLow
                    stopPips = abs(row['Close'] - sl) / 0.0001
                    lessThanOne = (row['macd'] < -1) and (row['signal'] < -1) and (row['signalPrevDay'] < -1) and (row['macdPrevDay'] < -1)

                    slPoints = abs(sl - row['Close'])
                    tpOne = row['Close'] + slPoints
                    tpTwo = row['Close'] + (slPoints * rr)

                    no_clear_pull = (row['Low'] == currentLow)

                    if 5 <= slPoints and dailyLoss < 2 and lessThanOne and sl > row['EMA_200'] and not no_clear_pull:
                        lotSize = (100 / slPoints) * 20
                        openTrades+=1
                       
                        trades[date] = {
                            'Order' : 'BUY', 
                            'Date' : date, 
                            'Stop Loss' : sl, 
                            'Take Profit One' : tpOne, 
                            'Take Profit Two' : tpTwo,
                            'Which Take Profit' : 0,
                            'Stop Loss Points' : slPoints,
                            'EMA' : row['EMA_200'],
                            'Lot Size' : lotSize,
                            'Entry' : row['Close'],
                            'macd' : row['macd'],
                            'signal' : row['signal'],
                        }

                elif row['macd'] > row['signal'] and row['macdPrevDay'] < row['signalPrevDay'] and (row['Close'] > row['EMA_200']):
                    sl = currentLow
                    slPoints = abs(sl - row['Close'])
                    lessThanOne = (row['macd'] < -1) and (row['signal'] < -1) and (row['signalPrevDay'] < -1) and (row['macdPrevDay'] < -1)
                    
                    tpOne = row['Close'] + slPoints
                    tpTwo = row['Close'] + (slPoints * rr)
                    no_clear_pull = (row['Low'] == currentLow)
                    if 5 <= slPoints and dailyLoss < 2 and lessThanOne and sl > row['EMA_200'] and not no_clear_pull: 
                        lotSize = (100 / slPoints) * 20
                        openTrades+=1

                        trades[date] = {
                            'Order' : 'BUY', 
                            'Date' : date, 
                            'Stop Loss' : sl, 
                            'Take Profit One' : tpOne, 
                            'Take Profit Two' : tpTwo,
                            'Which Take Profit' : 0,
                            'Stop Loss Points' : slPoints,
                            'EMA' : row['EMA_200'],
                            'Lot Size' : lotSize,
                            'Entry' : row['Close'],
                            'macd' : row['macd'],
                            'signal' : row['signal'],
                        }
            
            elif (row['macd'] > 0) and (row['signal'] > 0) and datetime.time(10,0,0) <= date.time() <= datetime.time(15,0,0) and not no_more_trading: #Looking for sell:
                buyCount = 0
                if sellCount < 1:
                    sellCount += 1
                    currentHigh = row['High']
                else:
                    currentHigh = row['High'] if row['High'] > currentHigh else currentHigh
                   
                    sellCount += 1
                
                if row['macd'] < row['signal'] and row['macdPrevDay'] > row['signalPrevDay'] and (row['Close'] < row['EMA_200']):
                    sl = currentHigh
                    slPoints = abs(sl - row['Close'])
                    tpOne = row['Close'] - (slPoints)
                    tpTwo = row['Close'] - (slPoints * rr)

                    greaterThanOne = (row['macd'] > 1) and (row['signal'] > 1) and (row['signalPrevDay'] > 1) and (row['macdPrevDay']>1)
                    no_clear_pull = (row['High'] == currentHigh)
                    if 5 <= slPoints and dailyLoss < 2 and greaterThanOne and sl < row['EMA_200'] and not no_clear_pull:
                        lotSize = (100 / slPoints) * 20
                        openTrades+=1
                        trades[date] = {
                            'Order' : 'SELL', 
                            'Date' : date,
                            'Stop Loss' : sl, 
                            'Take Profit One' : tpOne, 
                            'Take Profit Two' : tpTwo,
                            'Which Take Profit' : 0,
                            'Stop Loss Points' : slPoints,
                            'EMA' : row['EMA_200'],
                            'Lot Size' : lotSize,
                            'Entry' : row['Close'],
                            'macd' : row['macd'],
                            'signal' : row['signal'],
                        }
                elif row['macd'] > row['signal'] and row['macdPrevDay'] < row['signalPrevDay'] and (row['Close'] < row['EMA_200']):
                    sl = currentHigh
                    #sl = row['SMA_200']
                    #sl = row['High']
                    slPoints = abs(sl - row['Close'])
                    greaterThanOne = (row['macd'] > 1) and (row['signal'] > 1) and (row['signalPrevDay'] > 1) and (row['macdPrevDay']>1)
                
                    tpOne = row['Close'] - (slPoints)
                    tpTwo = row['Close'] - (slPoints * rr)
                    no_clear_pull = (row['High'] == currentHigh)
                    if 5 <= slPoints and dailyLoss < 2 and greaterThanOne and sl < row['EMA_200'] and not no_clear_pull:
                        lotSize = (100 / slPoints) * 20
                        openTrades +=1
                        #tp = row['Close'] - (abs(row['Close'] - sl) * 2)
                        #lotSize = (self.accountBalance * self.risk) / (stopPips * self.pipValue)
                        trades[date] = {
                            'Order' : 'SELL', 
                            'Date' : date, 
                            'Stop Loss' : sl, 
                            'Take Profit One' : tpOne, 
                            'Take Profit Two' : tpTwo,
                            'Which Take Profit' : 0,
                            'Stop Loss Points' : slPoints,
                            'Lot Size' : lotSize,
                            'EMA' : row['EMA_200'],
                            'Entry' : row['Close'],
                            'macd' : row['macd'],
                            'signal' : row['signal'],
                        }
                                                 



            if (row['macd'] > 0) and (row['signal'] > 0):
                buyCount = 0
            elif (row['macd'] < 0) and (row['signal'] < 0):
                sellCount = 0

            keysToRemove = []
            
            for key in trades:
                #if trades[key]['Take Profit'] <= row['NextDayHigh'] and trades[key]['Order'] == 'BUY':
                if trades[key]['Order'] == 'BUY':
                    
                    if trades[key]['Take Profit Two'] <= row['NextDayHigh'] and (trades[key]['Which Take Profit'] == 0 or trades[key]['Which Take Profit'] == 1):
                        profit = trades[key]['Stop Loss Points'] * trades[key]['Lot Size'] * rr
                        totalProfit += profit
                        challengeProf += profit
                        dailyProf += profit
                        challengeProfArr.append(challengeProf)
                        totalProfitArr.append(totalProfit)
                        outcome.append('WIN')
                        trackSL.append(trades[key]['Stop Loss'])
                        trackTP.append(trades[key]['Take Profit Two'])
                        amounts.append(profit)
                        tradeDate.append(trades[key]['Date'])
                        entryTrack.append(trades[key]['Entry'])
                        orderTrack.append(trades[key]['Order'])
                        emaTrack.append(trades[key]['EMA'])
                        pointsTrack.append(trades[key]['Stop Loss Points'])
                        macdTrack.append(trades[key]['macd'])
                        signalTrack.append(trades[key]['signal'])
                        openTrades -= 1
                        keysToRemove.append(key)
                        
                    elif trades[key]['Take Profit One'] <= row['NextDayHigh'] and trades[key]['Which Take Profit'] == 0:
                        trades[key]['Which Take Profit'] = 1
                        
                    elif trades[key]['Entry'] >= row['NextDayLow'] and trades[key]['Which Take Profit'] == 1:
                        keysToRemove.append(key)
                        openTrades -= 1
                   
                if trades[key]['Stop Loss'] >= row['NextDayLow'] and trades[key]['Order'] == 'BUY' and key not in keysToRemove:
                    if trades[key]['Which Take Profit'] == 1:
                        openTrades -= 1
                        keysToRemove.append(key) 
                    else:
                        loss = trades[key]['Stop Loss Points'] * trades[key]['Lot Size']
                        totalProfit -= loss
                        challengeProf -= loss
                        dailyProf -= loss
                        amounts.append(-loss)
                        challengeProfArr.append(challengeProf)
                        outcome.append('LOSS')
                        trackSL.append(trades[key]['Stop Loss'])
                        trackTP.append(trades[key]['Take Profit Two'])
                        totalProfitArr.append(totalProfit)
                        tradeDate.append(trades[key]['Date'])
                        entryTrack.append(trades[key]['Entry'])
                        orderTrack.append(trades[key]['Order'])
                        emaTrack.append(trades[key]['EMA'])
                        pointsTrack.append(trades[key]['Stop Loss Points'])
                        macdTrack.append(trades[key]['macd'])
                        signalTrack.append(trades[key]['signal'])
                        dailyLoss += 1
                        openTrades -= 1
                       
                        keysToRemove.append(key) 

                #elif trades[key]['Take Profit'] >= row['NextDayLow'] and trades[key]['Order'] == 'SELL':
                elif trades[key]['Order'] == 'SELL':
                    if trades[key]['Take Profit Two'] >= row['NextDayLow'] and (trades[key]['Which Take Profit'] == 0 or trades[key]['Which Take Profit'] == 1):
                        profit = trades[key]['Stop Loss Points'] * trades[key]['Lot Size'] * rr 
                        totalProfit += profit
                        challengeProf += profit
                        dailyProf += profit
                        challengeProfArr.append(challengeProf)
                        totalProfitArr.append(totalProfit)
                        outcome.append('WIN')
                        trackSL.append(trades[key]['Stop Loss'])
                        trackTP.append(trades[key]['Take Profit Two'])
                        amounts.append(profit)
                        tradeDate.append(trades[key]['Date'])
                        entryTrack.append(trades[key]['Entry'])
                        orderTrack.append(trades[key]['Order'])
                        emaTrack.append(trades[key]['EMA'])
                        pointsTrack.append(trades[key]['Stop Loss Points'])
                        macdTrack.append(trades[key]['macd'])
                        signalTrack.append(trades[key]['signal'])
                        openTrades -= 1

                        keysToRemove.append(key)
                    

                    
                    elif trades[key]['Take Profit One'] >= row['NextDayLow'] and trades[key]['Which Take Profit'] == 0:
                        trades[key]['Which Take Profit'] = 1
                    elif trades[key]['Entry'] <= row['NextDayHigh'] and trades[key]['Which Take Profit'] == 1:
                        keysToRemove.append(key)
                        openTrades -= 1
                  
                if trades[key]['Stop Loss'] <= row['NextDayHigh'] and trades[key]['Order'] == 'SELL' and key not in keysToRemove:

                    loss = trades[key]['Stop Loss Points'] * trades[key]['Lot Size'] 
                    totalProfit -= loss
                    challengeProf -= loss
                    dailyProf -= loss
                    amounts.append(-loss)
                    challengeProfArr.append(challengeProf)
                    outcome.append('LOSS')
                    trackSL.append(trades[key]['Stop Loss'])
                    trackTP.append(trades[key]['Take Profit Two'])
                    totalProfitArr.append(totalProfit)
                    tradeDate.append(trades[key]['Date'])
                    entryTrack.append(trades[key]['Entry'])
                    orderTrack.append(trades[key]['Order'])
                    emaTrack.append(trades[key]['EMA'])
                    pointsTrack.append(trades[key]['Stop Loss Points'])
                    macdTrack.append(trades[key]['macd'])
                    signalTrack.append(trades[key]['signal'])
                    
                    
                    keysToRemove.append(key) 
                    openTrades -= 1
                    dailyLoss += 1
        
            if len(keysToRemove) > 0 : [trades.pop(key) for key in keysToRemove]
            #print(date.time())
            if date.time() == datetime.time(15,0,0):
                
                dailyProf = 0
                dailyLoss = 0
                
                delta = datetime.timedelta(days=1)
                next_month = date + datetime.timedelta(days=32)

                next_day = date + delta
                
                if row['Time'].month != next_day.month:
                    
                    # finalYearlyProfit += tradeProfit
                    if totalProfit > 0:
                        final_total += totalProfit
                        finalTotalArr.append(final_total)
                        totalProfit = 0
                    challengeProf = 0
                    
                    tradeCount = 0
        print(final_total)
                

        final_dict = {
            'Outcome' : outcome,
            'Order' : orderTrack,
            'Date' : tradeDate,
            'EMA' : emaTrack,
            'Points' : pointsTrack,
            'Take Profit' : trackTP,
            'Stop Loss' : trackSL,
            'Entry' : entryTrack,
            'Amount' : amounts,
            'Profit' : totalProfitArr,
            'Challenge Profit' : challengeProfArr,
            
        }

        final_df = pd.DataFrame(final_dict)
        final_df.to_csv('macd_strat.csv')

        print(final_df['Outcome'].value_counts())
        sns.lineplot(data=final_df['Profit'])
        plt.show()
        sns.lineplot(finalTotalArr)
        plt.show()
        sns.lineplot(data=final_df['Points'])
        plt.show()
    def _get_lots_data(self) -> pd.DataFrame:
        data_dict = {}
        for i in range(1,16):
            data_dict[f'data_{i}'] = pd.read_csv(f'data/us30_{i}.csv')
        
        df = pd.DataFrame()

        for key, value in data_dict.items():
            df = pd.concat([df, value], ignore_index=True)
        
        return df[::-1]

    def _get_data_csv(self, fileName: str) -> pd.DataFrame:
        """Gets the stock data from a csv file

        Args:
            fileName(str): Name of csv file with all the candlestick data

        Returns:
            pd.DataFrame: Returns a dataframe with all the candlestick data
        """
        return pd.read_csv(fileName)
    
    def _get_yf_data(self)-> pd.DataFrame:
        return yf.download('^DJI', period='60d', interval='5m')

    def _get_macd(self, price: pd.Series, slow: int,fast: int, smooth: int) -> pd.DataFrame:
        """gets the macd values

        Args:
            price (pd.Series): closing price
            slow (int): ema with a longer period
            fast (int): ema with a faster period
            smooth (int): period of the signal line

        Returns:
            pd.DataFrame: dataframe with macd values
        """
        exp1 = price.ewm(span = fast, adjust = False).mean()
        exp2 = price.ewm(span = slow, adjust = False).mean()
        macd = pd.DataFrame(exp1 - exp2).rename(columns = {'Close':'macd'})
        signal = pd.DataFrame(macd.ewm(span = smooth, adjust = False).mean()).rename(columns = {'macd':'signal'})
        hist = pd.DataFrame(macd['macd'] - signal['signal']).rename(columns = {0:'hist'})
        frames =  [macd, signal, hist]
        return pd.concat(frames, join = 'inner', axis = 1)
    