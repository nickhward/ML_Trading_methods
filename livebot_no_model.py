import pandas as pd 
import numpy as np
import datetime
import MetaTrader5 as mt5
from datetime import datetime, time

import pytz
import Indicators
from time import sleep

class MacdNoModelLiveBot:
    SYMBOL = 'US30'
    RISK = 1_000
    CONTRACT_SIZE = 100
    DEVIATION = 20
    MAGIC = 234000

    def __init__(self):
        self._init_metatrader()

    def _create_trade_request(self, action_type, symbol, price, sl, tp):
        sl_points = abs(sl - price)
        lot_size = (self.RISK) / (sl_points * self.CONTRACT_SIZE)
        print('Making trade request')
        return {
            "action": action_type,
            "symbol": symbol,
            "volume": round(lot_size, 2),
            "type": action_type,
            "price": price,
            "sl": sl+2,
            "tp": tp+2,
            "deviation": self.DEVIATION,
            "magic": self.MAGIC,
            "comment": "python script open",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        } 

    def live_trading(self):
        symbol = 'US30'
        self._init_metatrader()
        self._start_live_trading(symbol)

    def _start_live_trading(self, symbol):
        column_mappings = self._get_column_mappings()
        columns_to_drop = ['tick_volume', 'spread', 'real_volume']

        while True:
            wait_time = self._calculate_wait_time()
            print(f'Minutes till next 5 min interval: {wait_time/60}')
            sleep(wait_time)
            print(f'is 5 min interval: {datetime.now()}')

            data = self._prepare_data(symbol, column_mappings, columns_to_drop)
            lastRow = data[-1:]
            request = self._trade_request(lastRow=lastRow, symbol=symbol)

            if request:
                self._send_order(request=request)
            print(request)

    def _calculate_wait_time(self):
        t = datetime.now()
        s = (t.second + 60*t.minute) % 300
        print(datetime.now())
        return 300 - s

    def _prepare_data(self, symbol, column_mappings, columns_to_drop):
        data = self._get_mt5_data(ticker=symbol, timeFrame='5m')
        macd_df = self._get_macd(data['close'], 26, 12, 9)  

        data.rename(columns=column_mappings, inplace=True)
        data = data.drop(columns=columns_to_drop, axis=1)
        data = pd.concat([data, macd_df], axis=1)
        data['SMA_200'] = Indicators.sma(data, 200)
        data['macdPrevDay'] = data['macd'].shift(1)
        data['signalPrevDay'] = data['signal'].shift(1)
        return data

    def _get_column_mappings(self):
        return {
            'close' : 'Close', 
            'open' : 'Open', 
            'high' : 'High', 
            'low' : 'Low', 
            'time' : 'Time' 
        }

    def _trade_request(self, lastRow: pd.DataFrame, symbol: str, ) -> dict:
        rr = 1
        deviation = 20
        request = {}

        for _, row in lastRow.iterrows():
            date = self._parse_date(row['Time'])
            print(date.time())

            if self._is_buy_condition(row) and self._is_time_between(date):
                request = self._process_condition(row, symbol, mt5.TRADE_ACTION_DEAL, True, rr)

            elif self._is_sell_condition(row) and self._is_time_between(date):  
                print('looking for sell')
                request = self._process_condition(row, symbol, mt5.TRADE_ACTION_DEAL, False, rr)

        return request  

    def _parse_date(self, time_str):
        return datetime.strptime(str(time_str), "%Y-%m-%d %H:%M:%S")
    
    def _is_buy_condition(self, row):
        return (row['Low'] > row['SMA_200']) and (row['macd'] < 0) and (row['signal'] < 0)
    
    def _is_sell_condition(self, row):
        return (row['High'] < row['SMA_200']) and (row['macd'] > 0) and (row['signal'] > 0)

    def _is_time_between(self, date):
        return time(15,0,0) <= date.time() <= time(22,55,0)

    def _process_condition(self, row, symbol, action, is_buy, rr):
        sl, slPoints, tp = self._calculate_trade_params(row, is_buy, rr)
        if 5 <= slPoints <= 100:
            price = mt5.symbol_info_tick(symbol).bid
            return self._create_trade_request(action, symbol, price, sl, tp)
        else:
            return {}

    def _calculate_trade_params(self, row, is_buy, rr):
        if is_buy:
            sl = row['Low']
        else:
            sl = row['High']
        slPoints = abs(sl - row['Close'])
        if is_buy:
            tp = row['Close'] + (slPoints * rr)
        else:
            tp = row['Close'] - (slPoints * rr)
        return sl, slPoints, tp

    def _send_order(self, request: dict) -> None: 
        # send a trading request

        result = mt5.order_send(request)
        # check the execution result
        print("1. order_send(): by {} {} lots at {} with deviation={} points".format(request['symbol'],request['volume'],request['price'],request['deviation']))
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print("2. order_send failed, retcode={}".format(result.retcode))
            # request the result as a dictionary and display it element by element
            result_dict=result._asdict()
            for field in result_dict.keys():
                print("   {}={}".format(field,result_dict[field]))
                # if this is a trading request structure, display it element by element as well
                if field=="request":
                    traderequest_dict=result_dict[field]._asdict()
                    for tradereq_filed in traderequest_dict:
                        print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
            print("shutdown() and quit")
            mt5.shutdown()
            quit()
        
        print("2. order_send done, ", result)
        print("   opened position with POSITION_TICKET={}".format(result.order))
        print("   sleep 2 seconds before closing position #{}".format(result.order))

    def _init_metatrader(self) -> None:
        if not mt5.initialize():
            print("initialize() failed, error code =",mt5.last_error())
            quit()
        
    def _get_mt5_data(self, ticker: str, timeFrame: str) -> pd.DataFrame:

        time_dict = {
            '1m' : mt5.TIMEFRAME_M1,
            '5m' : mt5.TIMEFRAME_M5,
            '15m' : mt5.TIMEFRAME_M15,
            '1h' : mt5.TIMEFRAME_H1,
            '1d' : mt5.TIMEFRAME_D1,
        }

        rates = mt5.copy_rates_from_pos(ticker, time_dict[timeFrame], 0, 30_000)
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        return df
    
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
        macd = pd.DataFrame(exp1 - exp2).rename(columns = {'close':'macd'})
        signal = pd.DataFrame(macd.ewm(span = smooth, adjust = False).mean()).rename(columns = {'macd':'signal'})
        hist = pd.DataFrame(macd['macd'] - signal['signal']).rename(columns = {0:'hist'})
        frames =  [macd, signal, hist]
        return pd.concat(frames, join = 'inner', axis = 1)