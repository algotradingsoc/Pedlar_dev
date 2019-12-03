"""Basic echo agent."""
from agent import Agent


class EchoAgent(Agent):

  def __init__(self, **kwargs):
    self.counter = 0
    self.previous = 0
    self.history = []
    super().__init__(**kwargs)

  def onIEX(self, tickerjson):
    if tickerjson['symbol'] == 'SPY':
      self.counter +=1
      if self.counter%6 == 0:
        self.buy(exchange='IEX',ticker='SPY')
      if self.counter%200 == 0:
        self.close()

  def onTrueFX(self,tickerjson):
    print(tickerjson)



if __name__ == "__main__":
  import logging
  
  logging.basicConfig(level=logging.DEBUG)
  agent = EchoAgent.from_args()
  agent.run()
