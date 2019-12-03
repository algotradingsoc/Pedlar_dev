"""mt5 zmq test client."""
import argparse
from collections import namedtuple
from datetime import datetime
import logging
import re
import struct

import json
import pandas as pd

import requests
import zmq

logger = logging.getLogger(__name__)
logger.info("libzmq: %s", zmq.zmq_version())
logger.info("pyzmq: %s", zmq.pyzmq_version())

# pylint: disable=broad-except,too-many-instance-attributes,too-many-arguments

Order = namedtuple('Order', ['id', 'exchange', 'ticker', 'price', 'volume', 'type'])

# Context are thread safe already,
# we'll create one global one for all agents
context = zmq.Context()


class Agent:
  """Base class for Pedlar trading agent."""
  name = "agent"
  polltimeout = 2000 # milliseconds
  csrf_re = re.compile('name="csrf_token" type="hidden" value="(.+)"')
  time_format = "%Y.%m.%d %H:%M:%S" # datetime column format

  def __init__(self, backtest=None, username="nobody", password="",
               ticker="tcp://localhost:7000",
               endpoint="http://localhost:5000"):
    self.backtest = backtest # backtesting file in any
    self._last_order_id = 0 # auto increment id for backtesting

    self.username = username # pedlarweb username
    self.password = password # pedlarweb password
    self.endpoint = endpoint # pedlarweb endpoint
    self._session = None # pedlarweb requests Session
    self.ticker = ticker # Ticker url
    self._socket = None # Ticker socket
    self._poller = None # Ticker socket polling object

    # Orders are stored as a dictionary/ Redis Cache 
    # Balance: PnL figure 
    # Cash: Leverage limit on orders, so need to adjust for place_order methods 
    self.orders = dict() # Orders indexed using order id
    self.cash = 1000000 # Initial capital
    self.balance = 0 # PnL 

    # Porfolio are stored as a dictionary/ Redis Cache 

    # Recent market data should be a dictionary of dictionary/ Redis Cache 
    self._last_tick = (None, None) # last tick price for backtesting

  @classmethod
  def from_args(cls, parents=None):
    """Create agent instance from command line arguments."""
    parser = argparse.ArgumentParser(description="Pedlar trading agent.",
                                     fromfile_prefix_chars='@',
                                     parents=parents or list())
    parser.add_argument("-b", "--backtest", help="Backtest agaisnt given file.")
    parser.add_argument("-u", "--username", default="nobody", help="Pedlar Web username.")
    parser.add_argument("-p", "--password", default="", help="Pedlar Web password.")
    parser.add_argument("-t", "--ticker", default="tcp://localhost:7000", help="Ticker endpoint.")
    parser.add_argument("-e", "--endpoint", default="http://localhost:8000", help="Pedlar Web endpoint.")
    return cls(**vars(parser.parse_args()))

  def connect(self):
    """Attempt to connect pedlarweb and ticker endpoints."""
    #-- pedlarweb connection
    # We will adapt to the existing web login rather than
    # creating a new api endpoint for agent requests
    logger.info("Attempting to login to Pedlar web.")
    _session = requests.Session()
    try:
      r = _session.get(self.endpoint+"/login") # CSRF protected
      r.raise_for_status()
    except:
      logger.critical("Failed to connect to Pedlar web.")
      raise RuntimeError("Connection to Pedlar web failed.")
    try:
      csrf_token = self.csrf_re.search(r.text).group(1)
    except AttributeError:
      raise Exception("Could not find CSRF token in auth.")
    payload = {'username': self.username, 'password': self.password,
               'csrf_token': csrf_token}
    r = _session.post(self.endpoint+"/login", data=payload, allow_redirects=False)
    r.raise_for_status()
    if not r.is_redirect or not r.headers['Location'].endswith('/'):
      raise Exception("Failed login into Pedlar web.")
    self._session = _session
    logger.info("Pedlar web authentication successful.")
    #-- ticker connection
    socket = context.socket(zmq.SUB)
    # Set topic filter, this is a binary prefix
    # to check for each incoming message
    # set from server as uchar topic = X
    # We'll subsribe to everything for now
    socket.setsockopt(zmq.SUBSCRIBE, bytes())
    # socket.setsockopt(zmq.SUBSCRIBE, bytes.fromhex('00'))
    logger.info("Connecting to ticker: %s", self.ticker)
    socket.connect(self.ticker)
    self._socket = socket
    self._poller = zmq.Poller()
    self._poller.register(socket, zmq.POLLIN)

  def disconnect(self):
    """Close server connection gracefully in any."""
    # Clean up remaining orders
    self.close()
    # Ease the burden on server and logout
    logger.info("Logging out of Pedlar web.")
    r = self._session.get(self.endpoint+"/logout", allow_redirects=False)
    if not r.is_redirect:
      logger.warning("Could not logout from Pedlar web.")

  def on_order(self, order):
    """Called on successful order."""
    pass

  def talk(self, order_id=0, volume=0.01, action=0, exchange='Sample', ticker='ICL'):
    """Make a request response attempt to Pedlar web."""
    payload = {'order_id': order_id, 'volume': volume, 'action': action,
               'exchange': exchange, 'ticker': ticker, 'name': self.name, }
    try:
      r = self._session.post(self.endpoint+'/trade', json=payload)
      r.raise_for_status()
      resp = r.json()
    except Exception as e:
      logger.error("Pedlar web communication error: %s", str(e))
      raise IOError("Pedlar web server communication error.")
    return resp

  def _place_order(self, otype="buy", volume=0.01, exchange='Sample', ticker='ICL', single=True, reverse=True):
    """Place a buy or a sell order."""
    
    # Whether to close existing orders is debatable 
    # otype can be extended to support 
    # Market buy/ Market sell 
    # Short-sell restrictions? 


    ootype = "sell" if otype == "buy" else "buy" # Opposite order type
    if (reverse and
        not self.close([oid for oid, o in self.orders.items() if o.type == ootype])):
      # Attempt to close all opposite orders first
      return
    if single and [1 for o in self.orders.values() if o.type == otype]:
      # There is already an order of the same type
      return

    
    # Request the actual order
    logger.info("Placing a %s order.", otype)
    try:
      if self.backtest:
        # Check last tick exists:
        if self._last_tick[0] is None or self._last_tick[1] is None:
          raise ValueError(f"No last tick data: {self._last_tick}")
        # Place order locally
        bidaskidx = 0 if otype == "buy" else 1
        order = Order(id=self._last_order_id+1, exchange='CSV', ticker='CSV', price=self._last_tick[bidaskidx],
                      volume=volume, type=otype)
      else:
        # Contact pedlarweb
        if otype == "buy":
          action = 2
        else:
          action = 3
        resp = self.talk(volume=volume, action=action, exchange=exchange, ticker=ticker)
        order = Order(id=resp['order_id'], price=resp['price'], volume=volume, type=otype , exchange=exchange, ticker=ticker)
      self._last_order_id = order.id
      self.orders[order.id] = order
      self.on_order(order)
    except Exception as e:
      logger.error("Failed to place %s order: %s", otype, str(e))

  def buy(self, volume=0.01, single=True, reverse=True , exchange='Sample', ticker='ICL'):
    """Place a new buy order and store it in self.orders
    :param volume: size of trade
    :param single: only place if there is not an already
    :param reverse: close sell orders if any
    """
    self._place_order(otype="buy", volume=volume, single=single, reverse=reverse , exchange=exchange, ticker=ticker)

  def sell(self, volume=1, single=True, reverse=True , exchange='Sample', ticker='ICL'):
    """Place a new sell order and store it in self.orders
    :param volume: size of trade
    :param single: only place if there is not an already
    :param reverse: close buy orders if any
    """
    self._place_order(otype="sell", volume=volume, single=single, reverse=reverse , exchange=exchange, ticker=ticker)

  def on_order_close(self, order, profit):
    """Called on successfull order close."""
    pass

  def close(self, order_ids=None):
    """Close open all orders or given ids
    :param order_ids: only close these orders
    :return: true on success false otherwise
    """
    oids = order_ids if order_ids is not None else list(self.orders.keys())
    for oid in oids:
      if self.backtest:
        # Execute order locally
        order = self.orders.pop(oid)
        closep = self._last_tick[0 if order.type == "buy" else 1]
        diff = closep - order.price if order.type == "buy" else order.price - closep
        # Assume 100 for leverage for now
        profit = round(diff*100*order.volume*1000*(1/closep), 2)
        logger.info("Closed order %s with profit %s", oid, profit)
        self.balance += profit
        self.on_order_close(order, profit)
      else:
        # Contact pedlarweb
        try:
          resp = self.talk(order_id=oid, action=1)
          order = self.orders.pop(oid)
          logger.info("Closed order %s with profit %s", oid, resp['profit'])
          self.balance += resp['profit']
          self.on_order_close(order, resp['profit'])
        except Exception as e:
          logger.error("Failed to close order %s: %s", oid, str(e))
          return False
    return True

  def onIEX(self, tickjson):
    """Called on IEX tick update 
    :param tickjson: json of tick data, example 
    {'symbol': 'TMO', 'sector': 'pharmaceuticalsbiotechnology', 'securityType': 'commonstock', 
    'bidPrice': 259.81, 'bidSize': 100, 'askPrice': 259.96, 'askSize': 200, 
    'lastUpdated': 1555612786973, 'lastSalePrice': 259.91, 
    'lastSaleSize': 100, 'lastSaleTime': 1555612745216, 'volume': 68225, 
    'marketPercent': 0.03438, 'seq': 13202}
    """
    pass

  def onSample(self, tickjson):
    """Called on IEX tick update 
    :param tickjson: json of tick data, example 
    {'symbol': 'ICL', 'bid': 100, 'ask': 100.5}
    """
    pass


  def onTrueFX(self, dataframe):
    """Called on IEX tick update 
    :param dataframe: pandas dataframe of bid ask quotes from TrueFx, index is by FX pairs 
    """
    pass




  def ondata(self, pricingsource, tickdata):
    """ Caleed on every data update
    :param pricingsource: name of pricing source such as IEX, TrueFX 
    :param tickdata: bytes representation of tickdata 
    """

    truefxheader = None
    truefxnames = ['Symbol', 'Date', 'Bid', 'Bid_point','Ask', 'Ask_point', 'High', 'Low', 'Open']

    def bytes2df(bytestream, header, names):
      data_io = pd.compat.StringIO(bytestream.decode())
      df = pd.read_csv(data_io, header=header, names=names)
      del data_io
      return df

    if pricingsource == 'IEX':
      d = json.loads(tickdata)
      self.onIEX(d)

    if pricingsource == 'TrueFX':
      df = bytes2df(tickdata, truefxheader, truefxnames)
      df['Date'] = pd.to_datetime(df['Date'], unit='ms')
      df.set_index('Symbol', inplace=True)
      self.onTrueFX(df)

    if pricingsource == 'Sample':
      d = json.loads(tickdata)
      self.onSample(d)
    
  

  def remote_run(self):
    """Start main loop and receive updates."""
    # Check connection
    if not self._session:
      self.connect()
    # We'll trade forever until interrupted
    logger.info("Starting main trading loop...")
    try:
      while True:
        socks = dict(self._poller.poll(self.polltimeout))
        if not socks:
          continue
        if socks[self._socket] == zmq.POLLIN:
          message = self._socket.recv_multipart()
          pricingsource = message[0].decode()
          tick = message[1]
          self.ondata(pricingsource, tick)
    finally:
      logger.info("Stopping agent...")
      self.disconnect()

  
  # Local Run Backtest 
  # Needs to design MongoDB and will be a major revision
  
  def local_run(self):
    """Run agaisnt local backtesting file."""
    import csv
    with open(self.backtest, newline='', encoding='utf-16') as csvfile:
      reader = csv.reader(csvfile)
      try:
        for row in reader:
          if row[0] == 'tick':
            # Check if time column exists
            time = datetime.strptime(row.pop(), self.time_format) if len(row) > 3 else None
            self._last_tick = tuple([float(x) for x in row[1:]])
            self.on_tick(*self._last_tick, time=time)
          elif row[0] == 'bar':
            # Check if time column exists
            time = datetime.strptime(row.pop(), self.time_format) if len(row) > 5 else None
            self.on_bar(*[float(x) for x in row[1:]], time=time)
      except KeyboardInterrupt:
        pass # Nothing to do
      finally:
        print("--------------")
        print("Final session balance:", self.balance)
        print("--------------")

  def run(self):
    """Run agent."""
    if self.backtest:
      self.local_run()
    else:
      self.remote_run()
