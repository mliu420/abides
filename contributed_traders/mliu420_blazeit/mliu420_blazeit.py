from agent.TradingAgent import TradingAgent
import pandas as pd
import numpy as np
import os
import pandas as pd
from contributed_traders.util import get_file

class mliu420_blazeit(TradingAgent):
    """
    Mingchun Liu's Market Making Algo
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
        # Percentage of the order size to be placed at different levels is determined by levels_quote_dict
        ######################
        self.orders_executed = 0
        self.can_cancel_request = False
        self.paOrders = 0
        #parameters
        self.pricingVolume = 100
        self.depthLevels = 10

    def kernelStarting(self, startTime):
        super().kernelStarting(startTime)

    def wakeup(self, currentTime):
        """ Agent wakeup is determined by self.wake_up_freq """
        can_trade = super().wakeup(currentTime)
        if not can_trade: return
        #check if current time greater than wait time
        if self.cancelCheck(currentTime):
            self.cancelOrders()
        self.getCurrentSpread(self.symbol, depth=self.depthLevels)
        self.state = 'AWAITING_SPREAD'
        self.orders_executed = 0
    
    def receiveMessage(self, currentTime, msg):
        """ Market Maker actions are determined after obtaining the bids and asks in the LOB """
        super().receiveMessage(currentTime, msg)
        if msg.body['msg'] == 'ORDER_EXECUTED':
            self.orders_executed += 1
        if msg.body['msg'] == 'ORDER_ACCEPTED':
            self.can_cancel_request = True
        if self.state == 'AWAITING_SPREAD' and msg.body['msg'] == 'QUERY_SPREAD':
            self.calculateAndOrder()
            self.setWakeup(currentTime + self.getWakeFrequency())
        #do nothing till other leg executed
        elif self.state == 'AWAITING CONFIRMATION' and msg.body['msg'] == 'ORDER_ACCEPTED':
            self.paOrders -= 1
            if self.paOrders == 0:
                self.state = 'AWAITING EXECUTION'
                self.exec_time_order = currentTime
        elif self.state == 'AWAITING_EXECUTION' and msg.body['msg'] == 'ORDER_EXECUTED':
            #use a condition to see if holdings close to reduce exposure to JPM
            #self.fOrderTime = currentTime
            if len(self.orders) == 0:
                self.state == 'AWAITING_SPREAD'
                self.getCurrentSpread(self.symbol, depth=self.depthLevels)
                self.orders_executed = 0
            elif self.cancelCheck:
                self.cancelOrders()
        elif msg.body['msg'] == 'ORDER_CANCELLED':
            if len(self.orders) == 0:
                self.orders_executed = 0
                self.can_cancel_request = False
                self.state == 'AWAITING_SPREAD'
                self.getCurrentSpread(self.symbol, depth=self.depthLevels)
    
    def cancelOrders(self):
        """ cancels all resting limit orders placed by the market maker """
        for _, order in self.orders.items():
            self.cancelOrder(order)
        self.can_cancel_request = False
            
    def cancelCheck(self, currentTime):
        if self.orders and self.can_cancel_request:
            if self.orders_executed == 0:
                return True
            else:
                try:
                    if int(currentTime - self.exec_time_order).totalSeconds() >= 5:
                        return True
                except:
                    self.exec_time_order = currentTime
        return False
    
    def calculateAndOrder(self):
        bid, ask = self.getKnownBidAsk(self.symbol, best=False)
        if bid and ask:
            sumBid = 0
            sumBidVol = 0
            sumAsk = 0
            sumAskVol = 0
            for i in range(self.depthLevels):
                if sumBidVol + bid[i][1] > self.pricingVolume:
                    sumBidVol = self.pricingVolume
                    sumBid += (self.pricingVolume - bid[i][1]) * bid[i][0]
                else:
                    sumBid += bid[i][1] * bid[i][0]
                    
                if sumAskVol + ask[i][1] > self.pricingVolume:
                    sumAskVol = self.pricingVolume
                    sumAsk += (self.pricingVolume - ask[i][1]) * ask[i][0]
                else:
                    sumAsk += ask[i][1] * ask[i][0]
                
            if sumBid == sumAsk:
                if sumBid == self.pricingVolume:
                    askP = sumAsk / self.pricingVolume
                    bidP = sumBid / self.pricingVolume
                    self.placeLimitOrder(self.symbol, )
                    askVol = self.holdings['CASH'] / askP + max(0, self.holdings[self.symbol])
                    bidVol = self.holdings['CASH'] / bidP + max(0, -self.holdings[self.symbol])
                    self.placeLimitOrder(self.symbol, bidVol, True, bidP)
                    self.paOrders += 1
                    self.placeLimitOrder(self.symbol, askVol, False, askP)
                    self.paOrders += 1
                    self.state = 'AWAITING_CONFIRMATION' #place orders and await execution
    
    def getWakeFrequency(self):
        return pd.Timedelta(self.wake_up_freq)