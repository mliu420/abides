from agent.TradingAgent import TradingAgent
import pandas as pd


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

    def kernelStarting(self, startTime):
        super().kernelStarting(startTime)

    def wakeup(self, currentTime):
        """ Agent wakeup is determined by self.wake_up_freq """
        can_trade = super().wakeup(currentTime)
        if not can_trade: return
        self.cancelOrders()
        self.getCurrentSpread(self.symbol, depth=5)
        self.state = 'AWAITING_SPREAD'

    def receiveMessage(self, currentTime, msg):
        """ Market Maker actions are determined after obtaining the bids and asks in the LOB """
        super().receiveMessage(currentTime, msg)
        if self.state == 'AWAITING_SPREAD' and msg.body['msg'] == 'QUERY_SPREAD':
            self.calculateAndOrder(currentTime)
            
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
                        print('PRICE ASK', askP)
                        print('PRICE BID', bidP)
                        print('bid stats')
                        print(self.holdings['CASH'])
                        print(bidP)
                        print(self.holdings)
                        print(max(0, -self.holdings[self.symbol]))
                        bidVol = self.holdings['CASH'] / bidP + max(0, -self.holdings[self.symbol])
                        print('ask stats')
                        print(self.holdings['CASH'])
                        print(bidP)
                        print(max(0, self.holdings[self.symbol]))
                        askVol = self.holdings['CASH'] / askP + max(0, self.holdings[self.symbol])
                        print(askVol)

                        self.placeLimitOrder(self.symbol, bidVol, True, bidP)
                        self.placeLimitOrder(self.symbol, askVol, False, askP)
                        print('placed order')
            except Exception as e:
                print(e)
                pass
            self.state = 'AWAITING_WAKEUP' #place orders and await execution
            self.setWakeup(currentTime + self.getWakeFrequency())
    def getWakeFrequency(self):
        return pd.Timedelta(self.wake_up_freq)