from decimal import Decimal
import pandas as pd
from .models import BacktestResults, BacktestTrade

# backtesting/services.py
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
from .models import BacktestResults, BacktestTrade

# backtesting/services.py
def run_ml_backtest(
    stock_data: pd.DataFrame,
    symbol: str,
    initial_capital: float = 10000,
    cash_reserve: float = 0,
    position_size: float = 1,
    prediction_threshold: float = 0.02,
    stop_loss: float = 0.05,
    take_profit: float = 0.05
):
    """
    Run ML strategy backtest and store results in DB
    """
    # Make a copy of the dataframe and prep the data
    df = stock_data.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    # Initialize tracking variables
    capital = float(initial_capital)
    position = None
    highest_capital = float(initial_capital)
    max_drawdown = 0.0

    # Create initial backtest record
    backtest = BacktestResults.objects.create(
        stock_symbol=symbol,
        start_date=df['date'].min(),
        end_date=df['date'].max(),
        initial_capital=Decimal(str(initial_capital)),
        final_capital=Decimal(str(initial_capital)),
        total_return=Decimal('0'),
        num_trades=0,
        max_drawdown=Decimal('0')
    )

    for i in range(len(df) - 1):
        today = df.iloc[i]
        tomorrow = df.iloc[i + 1]
        
        current_price = float(today['close'])
        next_price = float(tomorrow['close'])  # Look at next day's price for exit conditions
        
        # Buy logic
        if position is None:
            predicted_price = float(today['predicted_price'])
            predicted_return = (predicted_price - current_price) / current_price
            
            print(f"Day {today['date']}: Price=${current_price:.2f}, Predicted=${predicted_price:.2f}, Return={predicted_return:.2%}")
            
            if predicted_return > prediction_threshold:
                available_capital = capital * (1 - cash_reserve)
                max_shares = int((available_capital * position_size) // current_price)
                shares = max_shares
                if shares > 0:
                    position = {
                        'entry_date': today['date'],
                        'entry_price': current_price,
                        'shares': shares,
                        'take_profit_price': current_price * (1 + take_profit),
                        'stop_loss_price': current_price * (1 - stop_loss)
                    }
                    capital -= shares * current_price
                    
                    trade = BacktestTrade.objects.create(
                        backtest=backtest,
                        entry_date=today['date'],
                        entry_price=Decimal(str(current_price)),
                        shares=shares
                    )
                    position['trade_id'] = trade.id
                    print(f"Bought {shares} shares at ${current_price:.2f}")
                    print(f"Take profit at ${position['take_profit_price']:.2f}")
                    print(f"Stop loss at ${position['stop_loss_price']:.2f}")
        
        # Sell logic
        elif position is not None:
            should_sell = False
            exit_reason = None
            exit_price = next_price  # Default to next day's price
            
            # Check if next day's price would trigger take profit or stop loss
            if next_price >= position['take_profit_price']:
                should_sell = True
                exit_reason = 'take_profit'
                exit_price = position['take_profit_price']  # Use take profit price instead of overshoot
                print(f"Take profit triggered: Next price ${next_price:.2f} >= ${position['take_profit_price']:.2f}")
            
            elif next_price <= position['stop_loss_price']:
                should_sell = True
                exit_reason = 'stop_loss'
                exit_price = position['stop_loss_price']  # Use stop loss price instead of overshoot
                print(f"Stop loss triggered: Next price ${next_price:.2f} <= ${position['stop_loss_price']:.2f}")
            
            if should_sell:
                trade = BacktestTrade.objects.get(id=position['trade_id'])
                trade.exit_date = tomorrow['date']  # Use next day's date for exit
                trade.exit_price = Decimal(str(exit_price))
                trade.profit_loss = Decimal(str(((exit_price - position['entry_price']) / position['entry_price']) * 100))
                trade.exit_reason = exit_reason
                trade.save()
                
                capital += position['shares'] * exit_price
                print(f"Sold {position['shares']} shares at ${exit_price:.2f} due to {exit_reason}")
                position = None
        
        # Track maximum drawdown
        current_total = capital
        if position:
            current_total += position['shares'] * current_price
        highest_capital = max(highest_capital, current_total)
        current_drawdown = (highest_capital - current_total) / highest_capital
        max_drawdown = max(max_drawdown, current_drawdown)

    # Close any open positions at the end
    if position is not None:
        final_price = float(df.iloc[-1]['close'])
        trade = BacktestTrade.objects.get(id=position['trade_id'])
        trade.exit_date = df.iloc[-1]['date']
        trade.exit_price = Decimal(str(final_price))
        current_return = (final_price - position['entry_price']) / position['entry_price']
        trade.profit_loss = Decimal(str(current_return * 100))
        trade.exit_reason = 'end_of_period'
        trade.save()
        
        capital += position['shares'] * final_price
        print(f"Closed final position: {position['shares']} shares at ${final_price:.2f}")

    # Update final results
    final_return = Decimal(str(((capital - float(initial_capital)) / float(initial_capital)) * 100))

    backtest.final_capital = Decimal(str(capital))
    backtest.total_return = final_return.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    backtest.num_trades = BacktestTrade.objects.filter(backtest=backtest).count()
    backtest.max_drawdown = Decimal(str(max_drawdown * 100)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    backtest.save()

    return backtest