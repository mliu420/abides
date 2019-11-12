from agent.TradingAgent import TradingAgent
import pandas as pd
import math

class mliu420_blazeit(TradingAgent):
    """
    This agent was built on the market maker agent with some caveats.
    Prices are determined by a variable pricingVolume. Roughly the price
    of a stock is going to be the average price if to buy/sell pricingVolume
    amount of stock. This average between the buy and sell for 100 shares
    is the price.
    
    My first iteration of this agent tried to be fancy with calculations
    of price happening at different times to speed up the order placing process.
    This caused issues with too many iterations.
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
        self.pricingVolume = 100
        self.depthLevels = 10
        self.starting_cash = starting_cash
        self.pOrders = 0

    def kernelStarting(self, startTime):
        super().kernelStarting(startTime)

    def wakeup(self, currentTime):
        """ Agent wakeup is determined by self.wake_up_freq """
        can_trade = super().wakeup(currentTime)
        if not can_trade: return
        self.cancelOrders()
        self.getCurrentSpread(self.symbol, depth=self.depthLevels)
        self.state = 'AWAITING_SPREAD'
        print('true holdings??')
        print(self.holdings)

    def receiveMessage(self, currentTime, msg):
        """ Market Maker actions are determined after obtaining the bids and asks in the LOB """
        super().receiveMessage(currentTime, msg)
        if self.state == 'AWAITING_SPREAD' and msg.body['msg'] == 'QUERY_SPREAD':
            self.calculateAndOrder(currentTime)
#         if msg.body['msg'] = 'ORDER_ACCEPTED':
#             self.pOrders -= 1
        print(msg)
    def cancelOrders(self):
        """ cancels all resting limit orders placed by the market maker """
        for _, order in self.orders.items():
            self.cancelOrder(order)
            
    def calculateAndOrder(self, currentTime):
        bid, ask = self.getKnownBidAsk(self.symbol, best=False)
        print('got bid and ask')
        if bid and ask:
            print('bid and ask')
            print(bid)
            print(ask)
            sumBid = 0
            sumBidVol = 0
            sumAsk = 0
            sumAskVol = 0
            try:
                for i in range(self.depthLevels):
                    if sumBidVol < 100:
                        if sumBidVol + bid[i][1] > self.pricingVolume:
                            sumBid += (self.pricingVolume - sumBidVol) * bid[i][0]
                            sumBidVol = self.pricingVolume
                        else:
                            sumBid += bid[i][1] * bid[i][0]
                            sumBidVol += bid[i][1]
                    if sumAskVol < 100:
                        if sumAskVol + ask[i][1] > self.pricingVolume:
                            sumAsk += (self.pricingVolume - sumAskVol) * ask[i][0]
                            sumAskVol = self.pricingVolume
                        else:
                            sumAsk += ask[i][1] * ask[i][0]
                            sumAskVol += ask[i][1]
                            
                            
                if sumBidVol == sumAskVol:
                    if sumBidVol == self.pricingVolume:
                        askP = sumAsk / self.pricingVolume
                        bidP = sumBid / self.pricingVolume
                        bidVol = math.floor(max(0, self.holdings['CASH']) / bidP / 2)
                        askVol = math.floor(max(0, self.holdings['CASH']) / askP / 2)
                        try:
                            print('bidvol, askvol, jpm, cash',bidVol, askVol, self.holdings[self.symbol],self.holdings['CASH'])
                            bidVol = max(0,bidVol - self.holdings[self.symbol])
                            askVol = max(0,askVol + self.holdings[self.symbol])
                            print('bidvol, askvol, jpm',bidVol, askVol, self.holdings)
                        except:
                            pass
                        midP = (askP + bidP) / 2
                        askP = max(midP + 30, askP)
                        bidP = min(midP - 30, bidP)
                        dist = askVol / (askVol + bidVol)
                        if dist > 0.7:
                            askP = round(0.9 * askP + (0.1) * midP)
                            bidP = round(1.1 * bidP + (-0.1) * midP)
                        elif dist < 0.3:
                            askP = round(1.1 * askP + (-0.1) * midP)
                            bidP = round(0.9 * bidP + (0.1) * midP)
                        else:
                            askP = round(askP)
                            bidP = round(bidP)
                        
                        
                        if bidVol > 0:
                            self.placeLimitOrder(self.symbol, bidVol, True, bidP)
                            #self.pOrders += 1
                        if askVol > 0:
                            self.placeLimitOrder(self.symbol, askVol, False, askP)
                            #self.pOrders += 1
                        print('placed order')
            except Exception as e:
                print(e)
                pass
            self.state = 'AWAITING_WAKEUP' #place orders and await execution
            self.setWakeup(currentTime + self.getWakeFrequency())
    def getWakeFrequency(self):
        return pd.Timedelta(self.wake_up_freq)