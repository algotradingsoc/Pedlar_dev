import os
import datetime
import csv
import time
import json 

import requests

import pandas as pd
import numpy as np

iexbaseurl = 'https://api.iextrading.com/1.0'

def get_TOPS(tickerstring):
    iextopsurl = iexbaseurl + '/tops?symbols='
    query = iextopsurl + tickerstring
    r = requests.get(query)
    data = r.json()
    if data:
        snapshot = pd.DataFrame(data)
        snapshot['exchange'] = 'IEX'
        snapshot = snapshot.rename(columns={"symbol": "ticker", "bidPrice": "bid", 'askPrice':'ask', 'bidSize':'bidsize', 'askSize':'asksize', 'lastUpdated':'time'})
        snapshot['time'] = pd.to_datetime(snapshot['time'], unit='ms')  
        columns = ['time', 'exchange', 'ticker', 'bid', 'ask', 'bidsize', 'asksize']
        return snapshot[columns] 
    else:
        return pd.DataFrame(columns=['time', 'exchange', 'ticker', 'bid', 'ask', 'bidsize', 'asksize'])

if __name__=='__main__':
    get_TOPS('FB,APPL')

