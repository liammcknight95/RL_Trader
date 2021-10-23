import math
import backtrader as bt

class GoldenCross(bt.Strategy):
    params = ( # override default bt parameters
        ('fast', 50), 
        ('slow', 100), 
        ('order_percentage', 0.95), # pctg of cash invested
        ('ticker', 'BTC'),
        ('stop_loss', 0.02),  # price is 2% less than the entry point
        ('trail', False)
    )


    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.datetime(0)
        print('%s, %s' % (dt.isoformat(), txt))


    def __init__(self):

        self.dataclose = self.datas[0].close

        # crossover indicator
        self.fast_moving_average = bt.indicators.SMA(
            self.data.close, period=self.params.fast, plotname='fast MA'
        )
        self.fast_moving_average.csv = True

        self.slow_moving_average = bt.indicators.SMA(
            self.data.close, period=self.params.slow, plotname='slow MA'
        )
        self.slow_moving_average.csv = True

        self.crossover = bt.indicators.CrossOver(
            self.fast_moving_average, 
            self.slow_moving_average
        )
        self.crossover.csv = True

    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Size: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Size: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None


    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))


    def stops(self, direction):
        if not self.params.trail:

            if direction == 'long':
                stop_price = self.data.close[0] * (1.0 - self.params.stop_loss)
                self.sell(exectype=bt.Order.Stop, price=stop_price)
                print(f"Stop loss on Long position at {stop_price}")

            elif direction == 'short':
                stop_price = self.data.close[0] * (1.0 + self.params.stop_loss)
                self.buy(exectype=bt.Order.Stop, price=stop_price)
                print(f"Stop loss on Short position at {stop_price}")
            
        # else:
        #     self.sell(exectype=bt.Order.StopTrail,
        #                 trailamount=self.params.trail)

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])

        # if neutral
        if self.position.size == 0: # if not position open
            # investment size
            amount_to_invest = (self.params.order_percentage * self.broker.cash)
            self.size = math.floor(amount_to_invest / self.data.close)

            if self.crossover > 0: # if crossover is +1
                print(f"Buy {self.size} shares of {self.params.ticker} at {self.data.close[0]}")
                self.buy(size=self.size)
                self.stops('long')

            if self.crossover < 0: # if crossover is -1
                print(f"Sell {self.size} shares of {self.params.ticker} at {self.data.close[0]}")
                self.sell(size=self.size)
                self.stops('short')

        # if already invested
        if self.position.size > 0: 
            if self.crossover < 0: # bearish signal
                print(f"Close {self.size} long and Sell {self.size} shares of {self.params.ticker} at {self.data.close[0]}")
                self.close()
                self.sell(size=self.size) # close long and go short
                self.stops('short')

        # if short
        if self.position.size < 0: 
            if self.crossover > 0: # bullish signal
                print(f"Close {self.size} short and Buy {self.size} shares of {self.params.ticker} at {self.data.close[0]}")
                self.close()
                self.buy(size=self.size) # close short and go long
                self.stops('long')


