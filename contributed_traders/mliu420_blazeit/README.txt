Author: Mingchun Liu
gatechID: mliu420
Agent name:blazeit

I've provided a general description of how the agent works, with the specific math within the code.

Description:
Each time this agent wakes up it cancels all orders and gets the prices. 

Using the pricings, it calculates the average price to buy and sell 100 shares. This average price is used to prevent being duped by other agents placing single orders.

The price this agent places is based on how much it holds and standard deviation calculations. If short this agent tends to make higher bids and if long, lower asks.
This is to reduce inventory and thus inventory exposure as agent wants to just make money on the bid-ask spread.

Part of the price is based on standard deviation of bid-ask spreads for current day, in order to accuractely price orders. To maximize profit via high bid-ask spreads but also more order executions.

Another part of this inventory exposure reduction strategy is that if an order is executed, it won't do anything on next wake up but will proceed the following wake up. This is so the other side of the order has a chance to execute.
This agent is a market maker and wishes to reduce exposure as much as possible and this is one such way it does that.

When an order is placed the agent waits for it's corresponding order acceptance from broker. This is to prevent too many orders being placed and the agent being overleveraged. The agent
tries to hold shares it can afford so it is not overleveraged long or short.

Lastly the agent dumps shares 5 minutes from EOD. This is to maximize trading time. Another option was to stop trading once 5% was made, this would be better for the competition but unrealistic in real life as a successful trading
algorithm wants to trade as long as possible. :)

Programming:
A few tricks were used to program the agent to respond quickly to prices. For example code that did not need to be run between requesting spread and placing an order was placed either before or after.