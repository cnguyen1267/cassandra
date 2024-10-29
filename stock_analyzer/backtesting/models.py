from django.db import models

class BacktestResults(models.Model):
    stock_symbol = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField()
    initial_capital = models.DecimalField(max_digits=10, decimal_places=2)
    final_capital = models.DecimalField(max_digits=10, decimal_places=2)
    total_return = models.DecimalField(max_digits=10, decimal_places=2)
    num_trades = models.IntegerField()
    max_drawdown = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.stock_symbol} backtest ({self.start_date} to {self.end_date})"

class BacktestTrade(models.Model):
    backtest = models.ForeignKey(BacktestResults, on_delete=models.CASCADE, related_name='trades')
    entry_date = models.DateField()
    entry_price = models.DecimalField(max_digits=10, decimal_places=2)
    exit_date = models.DateField(null=True)  # null=True because we might not have exited yet
    exit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    shares = models.IntegerField()
    profit_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    exit_reason = models.CharField(max_length=50, null=True)  # 'take_profit', 'stop_loss', etc.