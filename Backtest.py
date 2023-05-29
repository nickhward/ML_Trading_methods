import numpy as np
import pandas as pd

import yfinance as yf

import Indicators
from Graphing import Graphing
import datetime
import seaborn as sns
import matplotlib.pyplot as plt

class Backtesting:
    def __init__(self):
        self.window_21 = 21
        self.window_50 = 50
        self.window_100 = 100
        self.window_200 = 200        
        self.data = None
        self.multiple = 1.5
        self.accountSize = 20
        self.profit = 0
        
    def backtesting(self, ticker: str, start_date: str, end_date: str, i: str) -> None:

        self.data = self._get_csv_data()
        
        self.data['SMA_21'] = Indicators.sma(self.data, self.window_21)
        self.data['SMA_50'] = Indicators.sma(self.data, self.window_50)
        self.data['SMA_100'] = Indicators.sma(self.data, self.window_100)
        self.data['SMA_200'] = Indicators.sma(self.data, self.window_200)

        self._engulfing()
        self.trade_2Strikes()

    def _get_data(self, ticker: str, start_date: str, end_date: str, i: str) -> pd.DataFrame:
        data = yf.download(tickers=ticker, period="60d", interval="5m")
        return data

    def _get_csv_data(self):
        return pd.read_csv('us30uptodate.csv')

    def _bullish_bearish(self) -> None:
        """returns true to collumn dataframe if candle is bulish, if candle is bearish returns false"""

        self.data['bearish_bullish'] = self.data['Close'] > self.data['Open']

    def _engulfing(self) -> None:
        """In the collumns of bullish_engulfing and bearish engulfing will be true and if not will be false."""

        self._bullish_bearish()

        openBarCurrent = self.data['Open']
        openBarPrevious = self.data['Open'].shift()
        closeBarCurrent = self.data['Close']
        closeBarPrevious = self.data['Close'].shift()

        openThree = self.data['Open'].shift(3)
        closeThree = self.data['Close'].shift(3)
        openTwo = self.data['Open'].shift(2)
        closeTwo = self.data['Close'].shift(2)
        
        self.data['bullish 3LS'] = ((closeThree < openThree)
                                     & (closeTwo < openTwo)
                                     & (closeBarPrevious < openBarPrevious)
                                     & (closeBarCurrent > openBarPrevious))
        
        self.data['bearish 3LS'] = ((closeThree > openThree)
                                     & (closeTwo > openTwo)
                                     & (closeBarPrevious > openBarPrevious)
                                     & (closeBarCurrent < openBarPrevious))
        


        self.data['bullish_engulfing'] = ((openBarCurrent <= closeBarPrevious) 
                                          & (openBarCurrent < openBarPrevious) 
                                          & (closeBarCurrent > openBarPrevious))
        
        self.data['bearish_engulfing'] = ((openBarCurrent >= closeBarPrevious) 
                                          & (openBarCurrent > openBarPrevious)
                                          & (closeBarCurrent < openBarPrevious))


    def _calculate_trade_params(self, row, order):
        trade_params = {}
        if order == "BUY":
            stop_loss = abs(abs(row['Low'] - row['Close']) - row['Close'])
            stop_points = abs(row['Low'] - row['Close'])
        else:  # order == "SELL"
            stop_loss = abs(abs(row['High'] - row['Close']) + row['Close'])
            stop_points = abs(row['High'] - row['Close'])

        take_profit = abs((stop_points * self.multiple) + row['Close'])            
        if abs(row['Close'] - row['Open']) != 0:        
            lot_size = (100 / abs(row['Close'] - row['Open'])) * self.accountSize
        
        trade_params = {'Order': order, 'Take Profit': take_profit, 'Stop Loss': stop_loss, 
                        'Entry': row['Close'], 'Lot Size': lot_size}
        return trade_params

    def _record_trade_outcome(self, trades, trade_key, result):
        profit = self.profit if result == "WIN" else -self.loss
        self.tradeProfit += profit
        self.dayNet += profit
        self.challengeProf += profit
        self.totalProf += profit
        self.currentNet.append(self.tradeProfit)
        self.everyTradePL.append(profit)     
        self.outcome.append(result)
        self.tradeDate.append(trades[trade_key]['Date']) 
        self.tradeOrder.append(trades[trade_key]['Order'])  
        self.lotSizeData.append(trades[trade_key]['Lot Size']) 
        self.challengeVals.append(self.challengeProf)
        self.totalProfArray.append(self.totalProf)

    def trade_2Strikes(self) -> None:
        # Initialized outside the loop
        tradeCount = 0
        trades = {}
        self.currentNet = []
        self.tradeProfit = 0
        self.challengeProf = 0
        self.totalProf = 0
        self.everyTradePL = []
        dayNet = 0
        self.outcome = []
        self.tradeDate = []
        self.tradeOrder = []
        self.lotSizeData = []
        self.challengeVals = []
        self.totalProfArray = []
        withdrawalProfs = 0

        self.data['NextDayLow'] = self.data['Low'].shift(-1)
        self.data['NextDayHigh'] = self.data['High'].shift(-1)
        self.data['PrevDayLow'] = self.data['Low'].shift(1)
        self.data['PrevDayHigh'] = self.data['High'].shift(1)

        for _, row in self.data.iterrows():
            date = datetime.datetime.strptime((row['Datetime'] + ' ' + row['Time']), "%Y.%m.%d %H:%M:%S")
            smaBuyAlign = row['SMA_21'] > row['SMA_50'] > row['SMA_200']
            smaSellAlign = row['SMA_21'] < row['SMA_50'] < row['SMA_200']

            if datetime.time(17,0,0) <= date.time() <= datetime.time(22,0,0) :
                if smaBuyAlign and (row['bullish 3LS'] and row['bullish_engulfing']) and tradeCount < 6 and row['Low'] > row['SMA_21']:
                    tradeCount += 1
                    trades[date] = self._calculate_trade_params(row, "BUY")

                elif smaSellAlign and (row['bearish 3LS'] and row['bearish_engulfing']) and tradeCount < 6 and row['High'] < row['SMA_21']:
                    tradeCount += 1
                    trades[date] = self._calculate_trade_params(row, "SELL")
                
           
            keysToRemove = []
            for key in trades:
                if trades[key]['Take Profit'] <= row['NextDayHigh'] and trades[key]['Order'] == 'BUY':
                    self._record_trade_outcome(trades, key, "WIN")
                    keysToRemove.append(key)

                elif trades[key]['Stop Loss'] >= row['NextDayLow'] and trades[key]['Order'] == 'BUY':
                    self._record_trade_outcome(trades, key, "LOSS")
                    keysToRemove.append(key)        
                    
                elif trades[key]['Take Profit'] >= row['NextDayLow'] and trades[key]['Order'] == 'SELL':
                    self._record_trade_outcome(trades, key, "WIN")
                    keysToRemove.append(key)
                    
                elif trades[key]['Stop Loss'] <= row['NextDayHigh'] and trades[key]['Order'] == 'SELL':
                    self._record_trade_outcome(trades, key, "LOSS")
                    keysToRemove.append(key)
        
            if len(keysToRemove) > 0:
                [trades.pop(key) for key in keysToRemove]
            
            if date.time() == datetime.time(23, 0, 0):
                delta = datetime.timedelta(days=1)
                next_day = date + delta
                if date.month != next_day.month:
                    if self.tradeProfit > 0:
                        withdrawalProfs += self.tradeProfit
                        self.tradeProfit = 0
                    self.challengeProf = 0
                    
                tradeCount = 0
                trades = {}

        finalDict = {
            'Outcome' : self.outcome, 
            'Date' : self.tradeDate, 
            'Order' : self.tradeOrder, 
            'Lot Size' : self.lotSizeData, 
            'Profit/Loss' : self.everyTradePL, 
            'NetProfit' : self.currentNet, 
            'Challenge Profit' : self.challengeVals,
            'Total Amount' : self.totalProfArray
            }
        df = pd.DataFrame(finalDict)
        
        df.to_csv('backtest2.csv')
        sns.lineplot(data=df['Challenge Profit'])
        plt.show()

        print(df['Outcome'].value_counts())
        print(withdrawalProfs)


    def trade(self) -> None:

        maxPrice = float('-inf')
        minPrice = float('inf')

        totalTradeInfo = {}


        trades = {}
        fibTrades = {}
        tradeCount = 0
        tradeProfit = 0
        tradeLoss = 0
        everyTradePL = []
      
        tradeDate = []
        tradeOrder = []
        lotSizeData = []
        outcome = []
        currentNet = []
        checkcurrentprice = []
        longTermProfArr = []
        dayNet = 0
        finalYearlyProfit = 0
        longTermProf = 0
        finalProfit = 0

        order = "NONE"

        fibTotal = 0
        fibMonthly = 0
        fibChallenge = 0 
        fibTotalArr = []
        fibMonthlyArr = []
        fibChallengeArr = []
        fibDates = []
        fibOutcome = []
        fibOrderType = []
        highest = float('-inf')
        lowest = float('inf')
        fibCount = 0

        interval = 0

        self.data['NextDayLow'] = self.data['Low'].shift(-1)
        self.data['NextDayHigh'] = self.data['High'].shift(-1)
        self.data['PrevDayLow'] = self.data['Low'].shift(1)
        self.data['PrevDayHigh'] = self.data['High'].shift(1)

        self.data = self.data.drop(self.data.index[range(200)])
        
        keepGoing = True
        badMonths=[6, 7,11,12]

        for _, row in self.data.iterrows():
            date = datetime.datetime.strptime((row['Datetime'] + ' ' + row['Time']), "%Y.%m.%d %H:%M:%S")

            smaBuyAlign = row['SMA_21'] > row['SMA_50'] and row['SMA_50'] > row['SMA_200']
            smaSellAlign = row['SMA_21'] < row['SMA_50'] and row['SMA_50'] < row['SMA_200']

            #9:30=16:30
            if (datetime.time(16,30,0) <= date.time() <= datetime.time(23,0,0)) and date.month not in badMonths:
                

                if date.time() >= datetime.time(16,30,0) and date.time() <= datetime.time(18,0,0):
                    if row['High'] > maxPrice:
                        maxPrice = row['High']
                    if row['Low'] < minPrice:
                        minPrice = row['Low']
                
                elif date.time() >= datetime.time(18,5,0) and date.time() < datetime.time(22,0,0) and keepGoing:
                    halfMAXMIN = ((maxPrice - minPrice)/2) + minPrice
                    if order == 'NONE':
                        if row['Close'] > maxPrice:
                            order = 'BUY'
                        elif row['Close'] < minPrice:
                            order = 'SELL'
                    if order == 'BUY' and halfMAXMIN > row['Close']:
                        keepGoing = False
                    elif order == 'SELL' and halfMAXMIN < row['Close']:
                        keepGoing = False
                    if order == 'BUY' and (row['bullish_engulfing'] or row['bullish 3LS']) and smaBuyAlign:
                        tradeCount += 1
                        stopLoss = row['Low'] if abs(row['Low'] - row['Open']) > 1 else row['PrevDayLow']                    
                        #stopLoss = row['Low']
                        entry = row['Close']
                        #print(row['Datetime'])
                        if abs(entry - row['Open']) != 0:
                            lotSize = (100 / abs(entry - row['Open'])) * 20
                            #lotSize = (100 / abs(entry - stopLoss)) * 20
                        
                            takeProfit = (3 * abs(row['Open'] - row['Close'])) + row['Close']
                            potentialLoss = (entry - stopLoss) * lotSize   
                            if dayNet + potentialLoss > -10_000: 
                                if abs(row['Open'] - entry) >= 15:
                                    trades[date] = {'Date': date, 'Order' : order, 'Take Profit' : takeProfit, 'Stop Loss' : stopLoss, 'Entry' : entry, 'Lot Size' : lotSize}
                    if order == 'SELL' and (row['bearish_engulfing'] or row['bearish 3LS']) and smaSellAlign:
                        tradeCount += 1
                        stopLoss = row['High'] if abs(row['High'] - row['Open']) > 1 else row['PrevDayHigh']
                        entry = row['Close']
                        if abs(entry - row['Open']) != 0 :
                            lotSize = (100 / abs(entry - row['Open'])) * 20
                            #lotSize = (100 / abs(entry - stopLoss)) * 20
                            takeProfit = abs((3 * abs(row['Open'] - row['Close'])) - row['Close'])
                            potentialLoss = abs(entry - stopLoss) * lotSize
                            if dayNet + potentialLoss > -10_000:
                                
                                if abs(row['Open'] - entry) >= 15:
                                    trades[date] = {'Date': date, 'Order' : order, 'Take Profit' : takeProfit, 'Stop Loss' : stopLoss, 'Entry' : entry, 'Lot Size' : lotSize}
                    
                if date.time() == datetime.time(22,0,0):
                    maxPrice = float('-inf')
                    minPrice = float('inf')


                keysToRemove = []
                for key in trades:
                    if trades[key]['Take Profit'] <= row['NextDayHigh'] and trades[key]['Order'] == 'BUY':
                        profit = abs(trades[key]['Take Profit'] - trades[key]['Entry']) * trades[key]['Lot Size']                            
                        tradeProfit += profit
                        longTermProf += profit
                        dayNet += profit
                        longTermProfArr.append(longTermProf)
                        currentNet.append(tradeProfit)
                        everyTradePL.append(profit)     
                        outcome.append('WIN')
                        tradeDate.append(trades[key]['Date']) 
                        tradeOrder.append(trades[key]['Order'])  
                        lotSizeData.append(trades[key]['Lot Size'])
                        
                        keysToRemove.append(key)
                                
                        
                        tradeCount -= 1

                    elif trades[key]['Stop Loss'] >= row['NextDayLow'] and trades[key]['Order'] == 'BUY':
                        loss = abs(trades[key]['Entry'] - trades[key]['Stop Loss']) * trades[key]['Lot Size']                            
                        tradeProfit -= loss
                        longTermProf -= loss
                        dayNet -= loss
                        longTermProfArr.append(longTermProf)
                        currentNet.append(tradeProfit)
                        everyTradePL.append(-loss)     
                        outcome.append('LOSS')
                        tradeDate.append(trades[key]['Date']) 
                        tradeOrder.append(trades[key]['Order'])  
                        lotSizeData.append(trades[key]['Lot Size'])
                        keysToRemove.append(key)
                        
                        tradeCount -= 1
                    elif trades[key]['Take Profit'] >= row['NextDayLow'] and trades[key]['Order'] == 'SELL':
                        profit = abs(trades[key]['Entry'] - trades[key]['Take Profit']) * trades[key]['Lot Size']
                        tradeProfit += profit
                        dayNet += profit
                        longTermProf+=profit
                        longTermProfArr.append(longTermProf)
                        currentNet.append(tradeProfit)
                        everyTradePL.append(profit) 
                        outcome.append('WIN')
                        tradeDate.append(trades[key]['Date']) 
                        tradeOrder.append(trades[key]['Order'])  
                        lotSizeData.append(trades[key]['Lot Size'])

                        
                        keysToRemove.append(key)
                        tradeCount -= 1
                    elif trades[key]['Stop Loss'] <= row['NextDayHigh'] and trades[key]['Order'] == 'SELL':
                        loss = abs(trades[key]['Stop Loss'] - trades[key]['Entry']) * trades[key]['Lot Size']
                        tradeProfit -= loss
                        dayNet -= loss
                        longTermProf-=loss
                        longTermProfArr.append(longTermProf)
                        currentNet.append(tradeProfit)
                        everyTradePL.append(-loss)     
                        outcome.append('LOSS')
                        tradeDate.append(trades[key]['Date']) 
                        tradeOrder.append(trades[key]['Order'])  
                        lotSizeData.append(trades[key]['Lot Size'])
                        keysToRemove.append(key)
            
                        tradeCount -= 1
                #print(dayNet)
                if len(keysToRemove) > 0:
                    [trades.pop(key) for key in keysToRemove]
            
            if (datetime.time(16,30,0) <= date.time() <= datetime.time(22,0,0)) and date.month in badMonths:
                
                dayStart = datetime.time(16,30,0)
                currentTime = date.time()
                
                fibRatio = 1.43



                if currentTime == dayStart : initOpen = row['Open']
                if currentTime == datetime.time(16,45,0) : finalClose = row['Close']
                
                if dayStart <= currentTime <= datetime.time(16,45,0):
                    
                    highest = row['High'] if row['High'] > highest else highest
                    lowest = row['Low'] if row['Low'] < lowest else lowest
                    
                if currentTime > datetime.time(16,45,0):           
                    if self._fib_dir(initOpen, finalClose): #is a bullish 15 minute candle
                        fibVal = highest - (highest - lowest) * fibRatio
                        curLow = row['Low']
                        #print(f'Date: {date.date()}, fib value: {fibVal}, row low: {curLow}, Highest: {highest}, Lowest: {lowest}')
                        sl = fibVal - 75
                        tp = fibVal + 105
                        if row['Low'] <= fibVal and fibCount < 1:
                            fibTrades[currentTime] = {
                                'Date' : date,
                                'Order' : 'BUY',
                                'Stop Loss' : sl,
                                'Take Profit' : tp
                            }
                            fibCount += 1
                    elif not self._fib_dir(initOpen, finalClose) and fibCount < 1:
                        fibVal = highest + (highest - lowest) * fibRatio
                        sl = fibVal + 75
                        tp = fibVal - 105
                        print('looking for sell')
                        if row['High'] >= fibVal:
                            
                            fibTrades[currentTime] = {
                                'Date' : date,
                                'Order' : 'SELL',
                                'Stop Loss' : sl,
                                'Take Profit' : tp
                            }
                            fibCount += 1
                    fibKeysToRemove = []
                    for key in fibTrades:
                        if fibTrades[key]['Take Profit'] <= row['NextDayHigh'] and fibTrades[key]['Order'] == 'BUY':
                            fibTotal += 2800
                            fibChallenge += 2800
                            fibMonthly += 2800
                            fibTotalArr.append(fibTotal)
                            fibChallengeArr.append(fibChallenge)
                            fibMonthlyArr.append(fibMonthly)
                            fibDates.append(fibTrades[key]['Date'])
                            fibOutcome.append('WIN')
                            fibOrderType.append('BUY')
                            fibKeysToRemove.append(key)

                        elif fibTrades[key]['Stop Loss'] >= row['NextDayLow'] and fibTrades[key]['Order'] == 'BUY':
                            fibTotal -= 2000
                            fibChallenge -= 2000
                            fibMonthly -= 2000
                            fibTotalArr.append(fibTotal)
                            fibChallengeArr.append(fibChallenge)
                            fibMonthlyArr.append(fibMonthly)
                            fibDates.append(fibTrades[key]['Date'])
                            fibOutcome.append('LOSS')
                            fibOrderType.append('BUY')
                            fibKeysToRemove.append(key)

                        elif fibTrades[key]['Take Profit'] >= row['NextDayLow'] and fibTrades[key]['Order'] == 'SELL':
                            fibTotal += 2800
                            fibChallenge += 2800
                            fibMonthly += 2800
                            fibTotalArr.append(fibTotal)
                            fibChallengeArr.append(fibChallenge)
                            fibMonthlyArr.append(fibMonthly)
                            fibDates.append(fibTrades[key]['Date'])
                            fibOutcome.append('WIN')
                            fibOrderType.append('SELL')
                            fibKeysToRemove.append(key)

                        elif fibTrades[key]['Stop Loss'] <= row['NextDayHigh'] and fibTrades[key]['Order'] == 'SELL':
                            fibTotal -= 2000
                            fibChallenge -= 2000
                            fibMonthly -= 2000
                            fibTotalArr.append(fibTotal)
                            fibChallengeArr.append(fibChallenge)
                            fibMonthlyArr.append(fibMonthly)    
                            fibDates.append(fibTrades[key]['Date'])
                            fibOutcome.append('LOSS')
                            fibOrderType.append('SELL')
                            fibKeysToRemove.append(key)

                    if len(fibKeysToRemove) > 0: [fibTrades.pop(key) for key in fibKeysToRemove]

            if date.time() == datetime.time(23,0,0):
                tradeCount = 0
                order = 'NONE'
                dayNet = 0
                keepGoing = True
                trades = {}
                delta = datetime.timedelta(days=1)
                next_day = date + delta

                highest = float('-inf')
                lowest = float('inf')
                fibCount = 0
                


                if date.month != next_day.month:
                    # finalYearlyProfit += tradeProfit
                    tradeProfit = 0
                    if longTermProf > 0:
                        finalProfit += longTermProf
                        longTermProf = 0
                    
                    fibChallenge = 0
                    if fibMonthly > 0:
                        fibMonthly = 0
                    
                    

        finalDict = {
            'Outcome' : outcome, 
            'Date' : tradeDate, 
            'Order' : tradeOrder, 
            'Lot Size' : lotSizeData, 
            'Profit/Loss' : everyTradePL, 
            'NetProfit' : currentNet, 
            'Long Term Prof' : longTermProfArr
        }
        df = pd.DataFrame(finalDict)
        print(df)
        df.to_csv('backtest1.csv')
        print(finalYearlyProfit)
        sns.lineplot(data=df['NetProfit'])
        plt.show()
        sns.lineplot(data=df['Long Term Prof'])
        plt.show()
        print(finalProfit)


        fibDict = {
            'Outcome' : fibOutcome,
            'Date' : fibDates,
            'Order' : fibOrderType,
            'Net Profit' : fibTotalArr,
            'Challenge Profit' : fibChallengeArr,
            'Monthly Profit' : fibMonthlyArr
        }
        df_fib = pd.DataFrame(fibDict)
        df_fib.to_csv('fib.csv')
        sns.lineplot(data=df_fib['Net Profit'])
        plt.show()
        sns.lineplot(data=df_fib['Challenge Profit'])
        plt.show()
    


                 
    def _fib_dir(self, init: int, final: str) -> bool:
        """ Decides if the first 15 minute candle is Bullish or Bearish

        Args:
            init (int): first candle opening in the 15 minute interval
            final (str): last candle closing in the 15 minute interval

        Returns:
            bool: returns true if bullish 15 minute candle, returns false if bearish 15 minute candle
        """
        
        return True if init < final else False
            

    
    



        