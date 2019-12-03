import os
import datetime
import csv
import time

import requests


import pandas as pd
import numpy as np
pd.set_option('expand_frame_repr', False)
pd.set_option('max_columns', 12)

from datetime import timedelta
from pandas.io.common import urlencode
from io import StringIO 


SYMBOLS_NOT_AUTH = ['EUR/USD', 'USD/JPY', 'GBP/USD', 'EUR/GBP', 'USD/CHF', 
    'EUR/JPY', 'EUR/CHF', 'USD/CAD', 'AUD/USD', 'GBP/JPY']

SYMBOLS_ALL = ['EUR/USD', 'USD/JPY', 'GBP/USD', 'EUR/GBP', 'USD/CHF', 'AUD/NZD', 
    'CAD/CHF', 'CHF/JPY', 'EUR/AUD', 'EUR/CAD', 'EUR/JPY', 'EUR/CHF', 'USD/CAD', 
    'AUD/USD', 'GBP/JPY', 'AUD/CAD', 'AUD/CHF', 'AUD/JPY', 'EUR/NOK', 'EUR/NZD', 
    'GBP/CAD', 'GBP/CHF', 'NZD/JPY', 'NZD/USD', 'USD/NOK', 'USD/SEK']



def _send_request(session, params):
    base_url = "http://webrates.truefx.com/rates"
    endpoint = "/connect.html"
    url = base_url + endpoint
    s_url = url + '?' + urlencode(params)
    response = session.get(url, params=params)
    return(response)


def _connect(session, username, password, lst_symbols, qualifier, \
        api_format, snapshot):
    s = 'y' if snapshot else 'n'
    params = {
        'u': username,
        'p': password,
        'q': qualifier,
        'c': ','.join(lst_symbols),
        'f': api_format,
        's': s
    }
    response = _send_request(session, params)
    if response.status_code != 200:
        raise(Exception("Can't connect"))
    session_data = response.text
    session_data = session_data.strip()
    return(session_data)


def _disconnect(session, session_data):
    params = {
        'di': session_data,
    }
    response = _send_request(session, params)
    return(response)


def _query_auth_send(session, session_data):
    params = {
        'id': session_data,
    }
    response = _send_request(session, params)
    return(response)

def _query_not_auth(session, lst_symbols, api_format, snapshot):
    s = 'y' if snapshot else 'n'

    params = {
        'c': ','.join(lst_symbols),
        'f': api_format,
        's': s
    }

    response = _send_request(session, params)
    if response.status_code != 200:
        raise(Exception("Can't connect"))

    return(response)


def _is_registered(username, password):
    return(not (username=='' and password==''))


def _init_session(session=None):
    if session is None:
        return(requests.Session())
    else:
        return(session)



def _init_credentials(username='', password=''):
    if username=='OS':
        username = os.getenv('TRUEFX_USERNAME').rstrip()
    if password=='OS':
        password = os.getenv('TRUEFX_PASSWORD').rstrip()
    return username, password


def _get_session(expire_after, cache_name='cache'):
    session = requests.Session()
    return session

def _parse_data(data):
    data_io = StringIO(data)
    df = pd.read_csv(data_io, header=None, \
    names=['ticker', 'time', 'bid', 'Bid_point', \
            'ask', 'Ask_point', 'High', 'Low', 'Open']    )

    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df['Bid_point'] = df['Bid_point'].map(str).str.zfill(3)
    df['Ask_point'] = df['Ask_point'].map(str).str.zfill(3)
    df['bid'] = (df['bid'].map(str).str.ljust(4, '0').str.slice(stop=4) + df['Bid_point'].map(str)).map(np.float64)
    df['ask'] = (df['ask'].map(str).str.ljust(4, '0').str.slice(stop=4) + df['Ask_point'].map(str)).map(np.float64)
    df['exchange'] = 'TrueFX'
    df['bidsize'] = 100
    df['asksize'] = 100
    columns = ['time', 'exchange', 'ticker', 'bid', 'ask', 'bidsize', 'asksize']
    return df[columns]
    
def _query(symbols='', qualifier='default', api_format='csv', snapshot=True, \
        username='', password='', force_unregistered=False, flag_parse_data=True, session=None):    

    (username, password) = _init_credentials(username, password)
    session = _init_session(session)
    is_registered = _is_registered(username, password)

    symbols = list(map(lambda s: s.upper(), symbols))

    if symbols == ['']:
        if not is_registered:
            symbols = SYMBOLS_NOT_AUTH
        else:
            symbols = SYMBOLS_ALL
    
    if not is_registered or force_unregistered:
        response = _query_not_auth(session, symbols, api_format, snapshot)
        return session,response,flag_parse_data,False
    else:
        session_data = _connect(session, username, password, symbols, qualifier, \
            api_format, snapshot)
        error_msg = 'not authorized'
        if error_msg in session_data:
            raise(Exception(error_msg))
        return session,session_data,flag_parse_data,True
    
def read_tick(session,session_data,flag_parse_data,authrozied):
    if authrozied:
        response = _query_auth_send(session, session_data)
        data = response.text
    else:
        response=_query_not_auth(session, SYMBOLS_NOT_AUTH, 'csv', True)
        data = response.text
    if flag_parse_data:
        df = _parse_data(data)
        return df
    else:
        return data

def config(symbols='', 
          username='', password='', 
          force_unregistered='', expire_after='-1', snapshot=True, api_format = 'csv',flag_parse_data = True):
    session = _get_session(expire_after)
    username, password = _init_credentials(username, password)
    is_registered = _is_registered(username, password)
    qualifier = 'default'
    session, session_data, flag_parse_data, authrorized = _query(symbols, qualifier, api_format, snapshot, username, password,
        force_unregistered, flag_parse_data, session)
    return session, session_data, flag_parse_data, authrorized

if __name__ == '__main__':
    session, session_data, flag_parse_data, authrorized = config(api_format ='csv', flag_parse_data = True)
    while True:
        data=read_tick(session, session_data,flag_parse_data,authrorized)      
        print(data)
        time.sleep(2)
