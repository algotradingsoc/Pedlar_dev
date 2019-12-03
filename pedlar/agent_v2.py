
import argparse
from collections import namedtuple
from datetime import datetime
import logging
import re
import struct
import time

import json
import pandas as pd
import numpy as np

import requests

# Datafeed functions 
import truefx
import iex

logger = logging.getLogger(__name__)

# pylint: disable=broad-except,too-many-instance-attributes,too-many-arguments

Holding =  ['exchange', 'ticker', 'volume']
Order =  ['order_id', 'exchange', 'ticker', 'price', 'volume', 'type', 'time']
Trade = ['trade_id', 'exchange', 'ticker', 'entryprice', 'exitprice', 'volume', 'entrytime', 'exittime']
Tick = ['time', 'exchange', 'ticker', 'bid', 'ask', 'bidsize', 'asksize']
Book = ['exchange', 'ticker', 'bid', 'ask', 'bidsize', 'asksize', 'time']


class Agent:
    """Base class for Pedlar trading agent."""

    

    def __init__(self, maxsteps=10, universefunc=None, ondatafunc=None, username="nobody", truefxid='', truefxpassword='', pedlarurl='http://127.0.0.1:5000'):
        
        self.endpoint = pedlarurl
        self.username = username  
        self.maxsteps = maxsteps

        self.orders = pd.DataFrame(columns=Order).set_index('order_id')
        self.trades = pd.DataFrame(columns=Trade).set_index('trade_id')
        
        self.history = pd.DataFrame(columns=Tick).set_index(['time', 'exchange', 'ticker'])
        self.orderbook = pd.DataFrame(columns=Book).set_index(['exchange', 'ticker'])
        self.balance = 0 # PnL 

        self.holdings = []

        # caplim is the max amount of capital allocated 
        # shorting uses up caplim but gives cash 
        # check caplim at each portfolio rebalance and scale down the target holding if that exceeds caplim
         
        self.portfoval = 50000
        self.pnl = 0
        self.cash = 50000
        self.caplim = self.portfoval * 2
        
        self.orderid = 0 
        self.tradeid = 0
        self.tradesession = 0

        # User defined functions 
        self.universe_definition = universefunc
        self.ondata = ondatafunc 

    @classmethod
    def from_args(cls, parents=None):
        """Create agent instance from command line arguments."""
        parser = argparse.ArgumentParser(description="Pedlar trading agent.",
                                                                         fromfile_prefix_chars='@',
                                                                         parents=parents or list())
        parser.add_argument("-u", "--username", default="nobody", help="Pedlar Web username.")
        parser.add_argument("-t", "--truefxid", default="", help="Username for Truefx")
        parser.add_argument("-p", "--truefxpassword", default="", help="Truefc password.")
        parser.add_argument("-m", "--pedlarurl", default="", help="Algosoc Server")
        return cls(**vars(parser.parse_args()))


    def start_agent(self, verbose=False):
        # create user profile in MongoDB if not exist 
        try:
            payload = {'user':self.username}
            r = requests.post(self.endpoint+"/user", json=payload)
            data = r.json()
            if data['exist']:
                print('Existing user {} found'.format(data['username']))
            self.username = data['username']
            self.connection = True
            self.tradesession = data['tradesession']
        except:
            self.connection = False
        # create truefx session 
        session, session_data, flag_parse_data, authrorize = truefx.config(api_format ='csv', flag_parse_data = True)
        self.truefxsession = session
        self.truefxsession_data = session_data
        self.truefxparse = flag_parse_data
        self.truefxauthorized = authrorize
        # connect to other datasource 
        self.step = 0
        if self.universe_definition:
            self.universe = self.universe_definition()
        else:
            self.universe = None 
        self.create_portfolio(self.universe,verbose)
        return None

    def save_record(self):
        # upload to pedlar server 
        if self.connection:
            payload = {'user_id':self.username,'pnl':self.balance}
            r = requests.post(self.endpoint+"/tradesession", json=payload)
            self.tradesession = r.json()['tradesession']
        time_format = "%Y_%m_%d_%H_%M_%S" # datetime column format
        timestamp = datetime.now().strftime(time_format)
        pricefilename = 'Historical_Price_{}.csv'.format(self.tradesession)
        tradefilename = 'Trade_Record_{}.csv'.format(self.tradesession)
        # save price history 
        self.history.to_csv(pricefilename)
        self.history_trades = pd.concat(self.holdings,axis=0)
        self.history_trades.to_csv(tradefilename)
        # upload trades for a tradesession 
        if self.connection and False:
            self.trades['backtest_id'] = self.tradesession
            self.trades['entrytime'] = self.trades['entrytime'].astype(np.int64)/1000000
            self.trades['exittime'] = self.trades['exittime'].astype(np.int64)/1000000
            self.trades.reset_index(inplace=True)
            trades = self.trades.to_dict(orient='record')
            for t in trades:
                r = requests.post(self.endpoint+'/trade', json=t)
        return None 

    def create_portfolio(self, tickerlist=None, verbose=False):

        if tickerlist is None:
            tickerlist = [('TrueFX','GBP/USD'), ('TrueFX','EUR/USD'), ('IEX','SPY'), ('IEX','QQQ')]

        self.portfolio = pd.DataFrame(columns=['volume'], index=pd.MultiIndex.from_tuples(tickerlist, names=('exchange', 'ticker'))) 
        self.portfolio['volume'] = 0

        iextickers = [x[1] for x in tickerlist if x[0]=='IEX']
        self.iextickernames = ','.join(iextickers)
        if self.iextickernames == '':
            self.iextickernames = 'SPY,QQQ'

        if verbose:
            print('Portfolio')
            print(self.portfolio)

        self.tickers = tickerlist
        self.n_assets = len(self.tickers)

        return None 

    def download_tick(self):
        # implement methods to get price data in dataframes 
        truefxdata = truefx.read_tick(self.truefxsession, self.truefxsession_data, self.truefxparse, self.truefxauthorized) 
        iexdata = iex.get_TOPS(self.iextickernames)
        return truefxdata, iexdata

    def update_history(self, verbose=False):
        # get raw data 
        truefx, iex = self.download_tick()

        # build order book 
        self.orderbook = pd.DataFrame(columns=Book).set_index(['exchange', 'ticker'])
        self.orderbook = self.orderbook.append(truefx.set_index(['exchange', 'ticker']))
        self.orderbook = self.orderbook.append(iex.set_index(['exchange', 'ticker']))

        # update price history 
        self.history = self.history.append(truefx.set_index(['time', 'exchange', 'ticker']))
        self.history = self.history.append(iex.set_index(['time', 'exchange', 'ticker']))

        # Ensure uniquess in price history
        self.history = self.history[~self.history.index.duplicated(keep='first')]

        # Remove old data in price history 

        if verbose:
            print('Price History')
            print(self.history)
            print('Orderbook')
            print(self.orderbook)

#################################################################################################################

    def update_trades(self, exchange='TrueFX', ticker='GBP/USD', volume=1, entry_price=1.23, exit_price=1.24, entrytime=None, exittime=None):
        self.tradeid += 1
        self.trades.loc[self.tradeid] = [exchange, ticker, entry_price, exit_price, volume, entrytime, exittime]
        trade_pnl = volume * (exit_price - entry_price) 
        self.balance += trade_pnl
        self.portfolio.loc[(exchange, ticker)] -= volume
        # upload to pedlar server 
        if self.connection: 
            t = {'backtest_id': self.tradesession,'entrytime':entrytime.strftime("%s"), 'exittime':exittime.strftime("%s"), 'trade_id':self.tradeid,
                    'exchange':exchange, 'ticker':ticker, 'volume':volume, 'entryprice':entry_price, 'exitprice':'exit_price' }
            r = requests.post(self.endpoint+'/trade', json=json.dumps(t))

        return None 

    
    def create_order(self, exchange='TrueFX', ticker='GBP/USD', price=1.23, volume=1, otype='market'):
        self.orderid += 1
        ref_price_slice = self.orderbook.loc[(exchange,ticker)]
        if otype=='market':
            if volume>0:
                ref_price = ref_price_slice['ask']
                ref_volume = min(volume,ref_price_slice['asksize'])
                self.portfolio.loc[(exchange,ticker)] += ref_volume
            else:
                ref_price = ref_price_slice['bid']
                ref_volume = min(volume,ref_price_slice['bidsize'])
                self.portfolio.loc[(exchange,ticker)] += ref_volume
        else:
            ref_price = price 
            ref_volume = volume 
        ref_time = ref_price_slice['time']
        self.orders.loc[self.orderid] = [exchange, ticker, ref_price, ref_volume, otype, ref_time ]
        return None

    def close_order(self, orderid=None):
        current_order = self.orders.loc[orderid]
        exchange = current_order['exchange']
        ticker = current_order['ticker']
        volume = current_order['volume']
        entryprice = current_order['price']
        entrytime = current_order['time']
        # get closing price
        quote = self.orderbook.loc[(exchange, ticker)]
        if volume > 0:
            exitprice = quote['bid']
        else:
            exitprice = quote['ask']
        exittime = quote['time']
        # update trade record
        self.update_trades(exchange=exchange, ticker=ticker, volume=volume, entry_price=entryprice, exit_price=exitprice, entrytime=entrytime, exittime=exittime)
        # delete order 
        self.orders = self.orders.drop(orderid)
        return None 

#######################################################################################################################
    

    def rebalance(self, new_weights, verbose=False):
        """
        Input: new_weights: dataframe with same index as portfolio
        """
        # add historical holdings
        # To Do: Add time to the portfolio holdings? 
        now = datetime.now()
        current_holdings = self.portfolio.transpose().set_index(np.array([now]))
        self.holdings.append(current_holdings)
        # construct changes 
        self.holdings_change = new_weights - self.portfolio
        # perform orders wrt to cash 
        # check asset allocation limit 
        self.portfoval = np.sum(self.portfolio['volume'] * self.orderbook['ask']) + self.cash
        self.caplim = self.portfoval * 2
        self.abspos = np.sum(np.abs(new_weights['volume']) * self.orderbook['ask'])
        if self.abspos > self.caplim:
            raise Error()
        # update to target portfolio
        # check cash must be positive 
        self.holdings_change['transact'] = np.where(self.holdings_change['volume']>0, self.orderbook.loc[self.holdings_change.index,:]['ask'],self.orderbook.loc[self.holdings_change.index,:]['bid']) * self.holdings_change['volume']
        self.cash = self.cash - np.sum(self.holdings_change['transact'])
        if self.cash<0:
            raise Error()
        self.portfolio = new_weights 
        return None 



    def run_agents(self, verbose=False):

        self.start_agent(verbose)
        if verbose:
            print(self.portfolio)

        # starting portfolio with zero holding 
        new_weights = self.portfolio

        while self.step < self.maxsteps:
            self.update_history(False)
            self.rebalance(new_weights)
            new_weights = self.ondata(history=self.history, portfolio=self.portfolio, trades=self.trades)
            self.portfoval = np.sum(self.portfolio['volume'] * self.orderbook['ask']) + self.cash
            self.step += 1
            time.sleep(2)
            if verbose:
                print('Step {} {}'.format(self.step, self.portfoval))
                print()
                print('Portfolio')
                print(self.portfolio)
                print()
        
        self.save_record()

if __name__=='__main__':

    def ondata(history, portfolio, trades):
        # copy 
        target_portfolio = portfolio.copy()
        # calculate target portfolio 
        target_portfolio['volume'] = (np.random.random() - 0.5) * 10000
        return target_portfolio

    agent = Agent(ondatafunc=ondata)
    agent.run_agents(verbose=True)


            




    