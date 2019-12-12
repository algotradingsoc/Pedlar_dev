# help of arctic
# https://github.com/manahl/arctic/blob/master/howtos/how_to_use_arctic.py
# install mongodb windows
# https://docs.mongodb.com/manual/tutorial/install-mongodb-on-windows/

# Need to run this in cmd for starting Local MongoDB at D drive
# "C:\Program Files\MongoDB\Server\4.0\bin\mongod.exe" --dbpath D:/TSDB

from arctic import Arctic

import arctic

import os 
import pymongo
import pandas as pd

import timeit
import time
import json
import datetime
import random

import logging

def _prasename(x):
    import re
    y=re.sub(r'\W+', '', x,count=0)
    return y

def _currentdatetime():
    return datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

# =============================================================================
# Folders and files 
# list files and subfolders 
# =============================================================================

def list_files(currentpath):
    from os import listdir 
    from os.path import isfile, join 
    files = [f for f in listdir(currentpath) if isfile(join(currentpath, f))]
    return files

def list_folders(currentpath):
    from os import listdir 
    from os.path import isdir, join 
    folders = [join(currentpath, f) for f in listdir(currentpath) if isdir(join(currentpath, f))]
    return folders

# =============================================================================
# Datafeed conversions 
# Mongodb, Arctic, csv, google drive api, gspraed, pydrive
# =============================================================================

def mongoclient(url):
    return pymongo.MongoClient(url)

def csv2mongo(client,dbname,collectionname,filename):

    try:
        db = client.get_database(dbname)
        db_cm = db[collectionname]
        tlist = pd.read_csv(filename)
        db_cm.insert_many(tlist.to_dict('records'))
        client.close()
    except:
        print('File not uploaded ', filename)

def df2mongo(client,dbname,collectionname,df):

    try:
        db = client.get_database(dbname)
        db_cm = db[collectionname]
        db_cm.insert_many(df.to_dict('records'))
        client.close()
    except:
        print('Not uploaded ', dbname,collectionname)
        
# Read dataframe from mongo, used for pricing data,
def mongo2df(client,dbname,collectionname):
    
    db = client.get_database(dbname)
    df = pd.DataFrame(list(db[collectionname].find({})))
    try:
        df.drop(['_id'], axis=1,inplace=True)
        df.drop_duplicates(keep='last', inplace=True)
    except:
        print('Record not found',collectionname)
    client.close()
    return df 

def mongo2csv(client,dbname,collectionname,filepath):
    
    db = client.get_database(dbname)
    df = pd.DataFrame(list(db[collectionname].find({})))
    try:
        df.drop(['_id'], axis=1,inplace=True)
        df.drop_duplicates(keep='last', inplace=True)
        df.to_csv(filepath,index=False)
    except:
        print('Record not found',collectionname)
    client.close()
    return df 


def mongo2mongo(client1,dbname1,collectionname1,client2,dbname2,collectionname2):
    # Move a collection from a mongodb to another 
    return None 

def arctichost(host):
    return Arctic(host)

# Download data to arctic db, try to append to existing table or create a bigger table 
def df2arctic(df,store,arcticcollectionname,ticker):
    # download df from mongo
    # remove duplicate documents(rows)
    # try to append to exisiting table in arctic 
    # if not possible then merge the existing tables to form a bigger table
    
    # Create library if not exist
    try:
        library = store[arcticcollectionname]
    except:
        store.initialize_library(arcticcollectionname)       
    library = store[arcticcollectionname]

    # trying to append the data 
    try:
        library.append(ticker,df, metadata={'lastupdate': datetime.datetime.now()})
        downloaded=True
    except:
        # Try to merge with the old dataframe
        try:
            temp=library.read(ticker)
            olddf=temp.data  
            indexname=olddf.index.name
            olddf.reset_index(inplace=True)
            df.reset_index(inplace=True)
            newdf=olddf.merge(df,how='outer')
            newdf.set_index(indexname,inplace=True)
            library.write(ticker,newdf, metadata={'lastupdate': datetime.datetime.now()})
            downloaded=True
        except:
            logging.warning(ticker,' not updated')
            downloaded=False
    return [downloaded,ticker]

# Move data between arctic collections with option to drop duplicates
def arctic2arctic(store1,arcticcollectionname1,ticker1,store2,arcticcollectionname2,ticker2,cleandata=True):
        
    library1 = store1[arcticcollectionname1]
    try:
        library2=store2[arcticcollectionname2]
    except:
        store2.initialize_library(arcticcollectionname2)
    library2=store2[arcticcollectionname2]

    df=library1.read(ticker1).data
    if cleandata:
        newdf=df.drop_duplicates(keep='last')
    else:
        newdf=df
    library2.write(ticker2,newdf, metadata={'source': 'QT'})

# read historical data from arctic 
def arctic2df(store,arcticcollectionname,ticker,start=None,end=None):
    # if start and end not provided, get the whole series
    # if end not provided, assume to get to latest data
    df=store[arcticcollectionname].read(ticker).data
    return df 
    
# =============================================================================
# Database maintenance 
# =============================================================================

def mongoclean(client,dbname,collectionname):
    db = client.get_database(dbname)
    db_cm = db[collectionname]
    db_cm.delete_many({})
    client.close()

def arcticclean(store,collection):

    library = store[collection]
    list=library.list_symbols()
    for sec in list:
        library.delete(sec)
        print('Security is deleted: ',sec)
        
def arctic_list_all_document(store,collectionname,download=False,path='ArcticData/',cleanup=False):
    library=store[collectionname]
    symbollist=library.list_symbols()
    for sec in symbollist:
        ts=library.read(sec)
        df=ts.data
        if not download:
            logging.info(collectionname+' '+sec)
        if cleanup:
            df.drop_duplicates(inplace=True)
            df.sort_index(inplace=True)
            if collectionname=='iex':
                try:
                    df=iex_preprocessing(df)
                except:
                    logging.warning('Preprocess error '+collectionname+' '+sec)
            library.write(sec,df, metadata={'lastupdate': datetime.datetime.now()})
            logging.info('Updated '+collectionname+' '+sec)
        if download:
            if cleanup:
                df=library.read(sec).data
            try:
                filename=path+_prasename(collectionname)+'_'+_prasename(sec)+'.csv'
                df.to_csv(filename)
            except:
                logging.warning('Security name '+sec+' Collection '+collectionname+' not downloaded')


def arctic_list_all(store,download=False,path='ArcticData/',cleanup=False):
    if not os.path.exists(path):
        os.makedirs(path)
    for i in store.list_libraries():
        arctic_list_all_document(store,i,download,path,cleanup)

def mongo_list_all_document(client,dbname,collectionname):
    return None

def mongo_list_all(client,dbname):
    return None 

        
# =============================================================================
# Data Pre-proessing  
# For each data source, write a preprocess function to remove duplicate and set index 
# =============================================================================    

def iex_preprocessing(df):
    newdf=df[ (df['high']>0) | (df['marketHigh']>0) ]
    return newdf    


# =============================================================================
# Datetime functions 
# Trading calendars 
# https://github.com/ThomasWongMingHei/pandas_market_calendars/blob/master/README.rst
# To create new calendars, need to fork the above github repo and add new exchange_calendar_qtcustom.py
# and then import this to  calendar_utils.py
# More details will be given on how to create new calendars 
# =============================================================================         

def shiftdate(date,shift):
    date2=pd.to_datetime(date)+pd.Timedelta(datetime.timedelta(days=shift))
    return date2

# shifttime('2018-06-05','09:00:00',1,'09:00:00')
def shifttime(date,time,shiftdate,shifttime):
    time2=pd.to_datetime(date+' '+time)
    mydelta=pd.to_timedelta(str(shiftdate)+' days '+shifttime)
    time3=time2+mydelta 
    return time3

######################################################
# Call this function to debug all database
#
###########################################################

if __name__=='__main__':
    if not os.path.exists('log/'):
        os.makedirs('log/')
    logname='log/'+_currentdatetime()+'_arctic.log'
    logging.basicConfig(filename=logname,level=logging.WARNING)
    store=arctichost('localhost')
    arctic_list_all(store,download=True,path='ArcticData/',cleanup=True)

