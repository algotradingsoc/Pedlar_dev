
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
import portcalc

logger = logging.getLogger(__name__)

# pylint: disable=broad-except,too-many-instance-attributes,too-many-arguments

Holding =  ['exchange', 'ticker', 'volume']
Tick = ['time', 'exchange', 'ticker', 'bid', 'ask', 'bidsize', 'asksize']
Book = ['exchange', 'ticker', 'bid', 'ask', 'bidsize', 'asksize', 'time']


class Agent:
    """Base class for Pedlar trading agent."""

    

    def __init__(self, maxsteps=20, universe=None, ondatafunc=None, ondataparams=None,
    username="nobody", agentname='myfirstagent', truefxid='', truefxpassword='', pedlarurl='https://pedlardev.herokuapp.com/'):
        
        self.truefxid = truefxid
        self.truefxpassword = truefxpassword

        self.maxlookup = 1000
        self.tradesession = 0
        self.endpoint = pedlarurl
        self.username = username  
        self.agentname = agentname
        self.maxsteps = maxsteps
        
        self.history = pd.DataFrame(columns=Tick).set_index(['time', 'exchange', 'ticker'])
        self.orderbook = pd.DataFrame(columns=Book).set_index(['exchange', 'ticker'])
        
        # List of holding history to be merge at the end of trading session 
        self.holdingshistory = []
        self.pnlhistory = [] 

        # caplim is the max amount of capital allocated 
        # shorting uses up caplim but gives cash 
        # check caplim at each portfolio rebalance and scale down the target holding if that exceeds caplim
        self.startcash = 50000
        self.portfoval = 50000
        self.caplim = self.portfoval * 2
        self.pnl = 0
        self.cash = 50000
        
        # User defined functions 
        self.universe = universe
        self.ondata = ondatafunc
        self.ondatauserparms = ondataparams

    @classmethod
    def from_args(cls, parents=None):
        """Create agent instance from command line arguments."""
        parser = argparse.ArgumentParser(description="Pedlar trading agent.",
                                                                         fromfile_prefix_chars='@',
                                                                         parents=parents or list())
        parser.add_argument("-u", "--username", default="nobody", help="Pedlar Web username.")
        parser.add_argument("-f", "--truefxid", default="", help="Username for Truefx")
        parser.add_argument("-p", "--truefxpassword", default="", help="Truefc password.")
        parser.add_argument("-s", "--pedlarurl", default="", help="Algosoc Server")
        return cls(**vars(parser.parse_args()))


    def start_agent(self, verbose=False):
        # create user profile in MongoDB if not exist 
        if self.connection:
            payload = {'user':self.username,'agent':self.agentname}
            r = requests.post(self.endpoint+"/user", json=payload)
            data = r.json()
            self.tradesession = data['tradesession']
            print('Tradesession: {}'.format(self.tradesession))
            print('User: {} Agent: {}'.format(self.username,self.agentname))
            print()
        # create truefx session 
        session, session_data, flag_parse_data, authrorize = truefx.config(api_format ='csv', flag_parse_data = True, username=self.truefxid, password=self.truefxpassword)
        self.truefxsession = session
        self.truefxsession_data = session_data
        self.truefxparse = flag_parse_data
        self.truefxauthorized = authrorize
        # connect to other datasource 
        # set up trading universe
        self.step = 0
        self.create_portfolio(self.universe,verbose)
        return None


    def create_portfolio(self, tickerlist=None, verbose=False):

        if tickerlist is None:
            tickerlist = [('TrueFX','GBP/USD'), ('TrueFX','EUR/USD'), ('TrueFX','JPY/USD'),
                        ('TrueFX','CHF/USD'),('TrueFX','CAD/USD'),('TrueFX','AUD/USD'),
                        ('IEX','SPY'), ('IEX','QQQ')]

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
        truefxdata.set_index('ticker',inplace=True)
        Reverse_pairs = ['USD/CHF','USD/JPY','USD/CAD']
        for p in Reverse_pairs:
            pinv = p[4:7] + '/' + p[0:3]
            truefxdata.loc[pinv,:] = truefxdata.loc[p,:]
            truefxdata.loc[pinv,'bid'] = 1 / truefxdata.loc[p,'bid']
            truefxdata.loc[pinv,'ask'] = 1 / truefxdata.loc[p,'ask']
        USD_based = ['GBP/USD','EUR/USD','JPY/USD','CHF/USD','CAD/USD','AUD/USD']
        truefxdata = truefxdata.loc[USD_based]
        truefxdata.reset_index(inplace=True)
        iexdata = iex.get_TOPS(self.iextickernames)
        return truefxdata, iexdata

    def extract_tick(self):
        truefxdata = pd.DataFrame()
        iexdata = pd.DataFrame()
        return truefxdata, iexdata 

    def update_history(self, live=True, verbose=False):
        
        if not live:
            truefx, iex = self.extract_tick()
        else:
            truefx, iex = self.download_tick()
        self.historysize = truefx.shape[0] + iex.shape[0]

        # build order book 
        self.orderbook = pd.DataFrame(columns=Book).set_index(['exchange', 'ticker'])
        self.orderbook = self.orderbook.append(truefx.set_index(['exchange', 'ticker']))
        self.orderbook = self.orderbook.append(iex.set_index(['exchange', 'ticker']))
        self.orderbook['mid'] = (self.orderbook['ask'] + self.orderbook['bid'])/2

        # update price history 
        self.history = self.history.append(truefx.set_index(['time', 'exchange', 'ticker']))
        self.history = self.history.append(iex.set_index(['time', 'exchange', 'ticker']))

        # Ensure uniquess in price history
        self.history = self.history[~self.history.index.duplicated(keep='first')]
        # Remove old data in price history
        self.history = self.history.iloc[-self.maxlookup*self.historysize:,:]

        if verbose:
            print('Orderbook')
            print(self.orderbook)

    def rebalance(self, new_weights, verbose=False):
        """
        Input: new_weights: dataframe with same index as portfolio
        """
        # add historical holdingshistory
        time_format = "%Y_%m_%d_%H_%M_%S"
        now = datetime.now().strftime(time_format)
        current_holdings = self.portfolio.transpose().set_index(np.array([now]))
        current_holdings['porftoliovalue'] = self.portfoval
        self.holdingshistory.append(current_holdings)
        # send results to pedlar
        if self.connection:
            _payload = current_holdings.to_dict('record')[0] 
            payload = dict([(k[0]+k[1],v) for k,v in _payload.items()])
            # wrap current orderbook value to dictionary 
            user = {'user_id':self.username,'agent':self.agentname, 'tradesession':self.tradesession, 'time':now}
            payload.update(user)
            r = requests.post(self.endpoint+"/portfolio/"+str(self.tradesession), json=payload)
        # construct changes 
        self.holdings_change = new_weights - self.portfolio
        # perform orders wrt to cash 
        # check asset allocation limit 
        self.abspos = np.sum(np.abs(new_weights['volume']) * self.orderbook['mid']) + self.cash
        if self.abspos > self.caplim:
            raise ValueError('Portfolio allocation cannot exceed capital limit')
        # check cash must be positive 
        self.holdings_change['transact'] = np.where(self.holdings_change['volume']>0, self.orderbook.loc[self.holdings_change.index,:]['ask'],self.orderbook.loc[self.holdings_change.index,:]['bid']) * self.holdings_change['volume']
        self.cash = self.cash - np.sum(self.holdings_change['transact'])
        if self.cash < 0:
            raise ValueError('Cash cannot be negative')
        # update to target holdings 
        self.portfolio = new_weights
        if verbose:
            print(self.holdings_change)
        return None 

    def save_record(self):
        # upload to pedlar server 
        if self.connection:
            payload = {'user_id':self.username,'agent':self.agentname, 'tradesession':self.tradesession, 'pnl':self.pnl, 'sharpe':self.sharpe}
            r = requests.post(self.endpoint+"/tradesession", json=payload)
            self.tradesession = r.json()['tradesession']
        time_format = "%Y_%m_%d_%H_%M_%S" # datetime column format
        timestamp = datetime.now().strftime(time_format)
        pricefilename = 'Historical_Price_{}_{}_Step_{}.csv'.format(self.agentname,self.tradesession,self.step)
        tradefilename = 'Portfolio_Holdings_{}_{}_Step_{}.csv'.format(self.agentname,self.tradesession,self.step)
        # save price history 
        self.history.to_csv(pricefilename)
        self.history_trades = pd.concat(self.holdingshistory,axis=0)
        self.history_trades.to_csv(tradefilename)
        return None 

    def delay(self,n_seconds=2):
        dt = datetime.now()
        time.sleep(n_seconds-dt.microsecond/1000000)
        return None

    def run(self, live=True, verbose=False, backtestfile=None):

        if live:
            self.connection = True
        else:
            self.connection = False 
        
        self.start_agent(verbose)
        # starting portfolio with zero holding 
        new_weights = self.portfolio

        

        while self.step < self.maxsteps:
            self.update_history(live=live,verbose=False)
            self.rebalance(new_weights,verbose=verbose)
            # Update capital limit 
            self.portfoval = np.sum(self.portfolio['volume'] * self.orderbook['mid']) + self.cash
            self.caplim = self.portfoval * 2 
            # Run user provided function to get target portfolio weights for the next data
            if not self.ondatauserparms:
                self.ondatauserparms = {}
            new_weights = self.ondata(step=self.step, history=self.history, portfolio=self.portfolio,  caplim=self.caplim, **self.ondatauserparms)

            # portfolio performance 
            self.pnl = self.portfoval - self.cash 
            self.pnlhistory.append(self.portfoval)
            if self.step >0:
                self.sharpe = portcalc.sharpe_ratio(self.pnlhistory)
            else:
                self.sharpe = 0 
            self.step += 1
            if live:
                if self.step % self.maxlookup == (self.maxlookup-1):
                    self.save_record()
                    self.holdingshistory = []
                    self.pnlhistory = [] 
                else:
                    self.delay()
            if verbose:
                print('Step {} {}'.format(self.step, self.portfoval))
                print()
                print('Orderbook')
                print(self.orderbook)
                print()
        # save record at the end of backtest
        self.save_record()

if __name__=='__main__':

    def ondata(step, history, portfolio, caplim):
        target_portfolio = portfolio.copy()
        # calculate target portfolio which is random for this example
        target_portfolio['volume'] = np.random.random()* 1000 - 500 
        return target_portfolio

    tickerlist = [  ('TrueFX','GBP/USD'), ('TrueFX','EUR/USD'), ('TrueFX','JPY/USD'),
                    ('TrueFX','CHF/USD'), ('TrueFX','CAD/USD'), ('TrueFX','AUD/USD'),
                    ('IEX','SPY'), ('IEX','QQQ'), ('IEX','EEM'), ('IEX','TLT') , ('IEX','SHY')]

    agent = Agent(ondatafunc=ondata,pedlarurl='http://127.0.0.1:5000',universe=tickerlist)
    agent.run(verbose=True,live=True)


            




    