from agent.TradingAgent import TradingAgent
import pandas as pd
import numpy as np
import os
#import math

class mliu420_blazeit(TradingAgent):

# Author: Mingchun Liu
# bazeit: 
#
# The author of this code hereby permits it to be included as a part of the ABIDES distribution, 
# and for it to be released under any open source license the ABIDES authors choose to release ABIDES under.
    """
    This agent is based on the market maker agent with some caveats.
    Prices are determined by a variable pricingVolume. Roughly the price
    of a stock is going to be the average price if to buy/sell pricingVolume
    amount of stock. This average between the buy and sell for 100 shares
    is the price. This is so that someon doesn't place a sneaky order of one stock.
    And mess up my pricing :)
    
    My first iteration of this agent tried to be fancy with calculations
    of price happening at different times to speed up the order placing process.
    This caused timing issues so I've simplified it drastically.
    """

    def __init__(self, id, name, type, symbol, starting_cash, min_size, max_size , wake_up_freq='10s',
                 log_orders=False, random_state=None):

        super().__init__(id, name, type, starting_cash=starting_cash, log_orders=log_orders, random_state=random_state)
        self.symbol = symbol      # Symbol traded
        self.min_size = min_size  # Minimum order size
        self.max_size = max_size  # Maximum order size
        self.size = round(self.random_state.randint(self.min_size, self.max_size) / 2) # order size per LOB side
        self.wake_up_freq = wake_up_freq # Frequency of agent wake up
        self.log_orders = log_orders
        self.state = "AWAITING_WAKEUP"
        #parameters
        self.sc = starting_cash
        self.pricingVolume = 100
        self.depthLevels = 10
        self.starting_cash = starting_cash
        self.pOrders = 0
        self.stdSpread = pd.DataFrame([50, 51])
        self.close = False
        self.wait = 0

    def kernelStarting(self, startTime):
        super().kernelStarting(startTime)

    def wakeup(self, currentTime):
        """ Agent wakeup is determined by self.wake_up_freq """
        can_trade = super().wakeup(currentTime)
        if not can_trade: return
        if self.wait <= 0 and self.pOrders == 0:
            self.cancelOrders()
            try:
                self.stdS = self.stdSpread.std()[0]
            except:
                self.stdS = 50
            if not(self.close):
                self.state = 'AWAITING_SPREAD'
            self.getCurrentSpread(self.symbol, depth=self.depthLevels)
        else:
            self.wait -= 1
            self.state = 'AWAITING_WAKEUP'
            self.setWakeup(currentTime + self.getWakeFrequency())
        if self.close:
            self.cancelOrders()
            self.dump_shares()
            
    def receiveMessage(self, currentTime, msg):
        """ Market Maker actions are determined after obtaining the bids and asks in the LOB """
        super().receiveMessage(currentTime, msg)
        
        if self.close:
            if msg.body['msg'] == 'ORDER_EXECUTED':
                try:
                    if self.holdings[self.symbol] != 0:
                        self.cancelOrders()
                        self.dump_shares()
                        self.state = 'AWAITING_WAKEUP'
                except:
                    pass
        elif self.state == 'AWAITING_SPREAD' and msg.body['msg'] == 'QUERY_SPREAD':
            self.calculateAndOrder(currentTime)
            dt = (self.mkt_close - currentTime) / np.timedelta64(1, 'm')
            if dt < 5:
                self.close = True
                self.dump_shares()
            self.state = 'AWAITING_WAKEUP' #place orders and await execution
            self.setWakeup(currentTime + self.getWakeFrequency())
        elif self.state == 'AWAITING_WAKEUP' and msg.body['msg'] == 'ORDER_EXECUTED':
            if len(self.orders) > 0 and self.wait == 0:
                self.wait = 1
            else:
                self.wait = 0
        elif msg.body['msg'] == 'ORDER_ACCEPTED':
            self.pOrders -= 1

    def cancelOrders(self):
        """ cancels all resting limit orders placed by the market maker """
        for _, order in self.orders.items():
            self.cancelOrder(order)
            
    def calculateAndOrder(self, currentTime):
        bid, ask = self.getKnownBidAsk(self.symbol, best=False)
        if bid and ask:
            sumBid = 0
            sumBidVol = 0
            sumAsk = 0
            sumAskVol = 0
            try:
                for i in range(self.depthLevels):
                    if sumBidVol < self.pricingVolume:
                        if sumBidVol + bid[i][1] > self.pricingVolume:
                            sumBid += (self.pricingVolume - sumBidVol) * bid[i][0]
                            sumBidVol = self.pricingVolume
                        else:
                            sumBid += bid[i][1] * bid[i][0]
                            sumBidVol += bid[i][1]
                    if sumAskVol < self.pricingVolume:
                        if sumAskVol + ask[i][1] > self.pricingVolume:
                            sumAsk += (self.pricingVolume - sumAskVol) * ask[i][0]
                            sumAskVol = self.pricingVolume
                        else:
                            sumAsk += ask[i][1] * ask[i][0]
                            sumAskVol += ask[i][1]
                    if sumAskVol == self.pricingVolume and sumBidVol == self.pricingVolume:
                        break
                if sumBidVol == sumAskVol:
                    if sumBidVol == self.pricingVolume:
                        askM = sumAsk / self.pricingVolume
                        bidM = sumBid / self.pricingVolume
                        midM = (askM + bidM) / 2
                        bidVol = int(np.floor(max(0, self.holdings['CASH'] / midM)))
                        try:
                            askVol = int(np.floor(max(0,2 * max(0,self.holdings[self.symbol])+(self.holdings['CASH'] - 2*abs(min(0,self.holdings[self.symbol]*askM))) / midM  )))
                        except:
                            askVol = int(np.floor(max(0,self.holdings['CASH']  / midM  ) ))
                        #Hate inventory exposure like I do? I change prices to move shares close to zero
                        midP = midM + self.stdS / 7 * bidVol / (bidVol + askVol) - self.stdS / 14
                        bidP = int(np.floor( min(midP - self.stdS/1.5, bidM + 1) ))
                        askP = int(np.ceil( max(midP + self.stdS/1.5, askM - 1) ))
                        if bidVol > 0:
                            self.placeLimitOrder(self.symbol, bidVol, True, bidP)
                            #orders sent and accepted are tracked so agent doesn't overleverage
                            self.pOrders += 1
                        if askVol > 0:
                            self.placeLimitOrder(self.symbol, askVol, False, askP)
                            self.pOrders += 1
                        self.stdSpread = self.stdSpread.append([askM-bidM], ignore_index=True)
            except Exception as e:
                pass
            
    def dump_shares(self):
        # get rid of any outstanding shares we have
        if self.symbol in self.holdings:
            bid, _, ask, _ = self.getKnownBidAsk(self.symbol)
            order_size = self.holdings[self.symbol]
            if order_size > 0:
                if bid:
                    self.placeLimitOrder(self.symbol, quantity=order_size, is_buy_order=False, limit_price=0)
            if order_size < 0:
                if ask:
                    self.placeLimitOrder(self.symbol, quantity=abs(order_size), is_buy_order=True, limit_price=round(2 * ask))
    
    def getWakeFrequency(self):
        return pd.Timedelta(self.wake_up_freq)
    def author(self):              
        return 'mliu420' # replace tb34 with your Georgia Tech username  