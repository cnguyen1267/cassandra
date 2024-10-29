from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import pandas as pd
from datetime import datetime
from .services import run_ml_backtest
from .models import BacktestResults, BacktestTrade
from stock_data.models import StockPrice
from django.core.exceptions import ObjectDoesNotExist

@csrf_exempt
def backtest_view(request, symbol):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests allowed'}, status=400)
    
    try:
        data = json.loads(request.body)
        
        # Parse date parameters
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Validate date format if provided
        try:
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'error': 'Invalid date format. Please use YYYY-MM-DD'
            }, status=400)
        
        # Build the query
        query = StockPrice.objects.filter(symbol=symbol)
        if start_date:
            query = query.filter(date__gte=start_date)
        if end_date:
            query = query.filter(date__lte=end_date)
            
        # Fetch historical data
        historical_data = query.order_by('date').values('date', 'close_price')
        
        if not historical_data:
            error_msg = f'No historical data found for symbol {symbol}'
            if start_date or end_date:
                error_msg += ' in the specified date range'
            return JsonResponse({'error': error_msg}, status=404)
        
        # Create DataFrame from DB data
        stock_data = pd.DataFrame(historical_data)
        stock_data = stock_data.rename(columns={'close_price': 'close'})
        
        # Validate predictions
        predictions = data.get('predictions')
        if not predictions:
            return JsonResponse({
                'error': 'Predictions are required in request body'
            }, status=400)
            
        if len(predictions) != len(stock_data):
            return JsonResponse({
                'error': (
                    f'Number of predictions ({len(predictions)}) does not match '
                    f'historical data length ({len(stock_data)}) for the specified '
                    f'date range ({stock_data.date.min()} to {stock_data.date.max()})'
                )
            }, status=400)
            
        stock_data['predicted_price'] = predictions

        # Run backtest
        result = run_ml_backtest(
            stock_data=stock_data,
            symbol=symbol,
            initial_capital=float(data.get('initial_capital', 10000)),
            prediction_threshold=float(data.get('prediction_threshold', 0.02)),
            stop_loss=float(data.get('stop_loss', 0.05)),
            take_profit=float(data.get('take_profit', 0.05))
        )

        # Get trades from DB for this backtest
        trades = BacktestTrade.objects.filter(backtest=result).values(
            'entry_date', 
            'entry_price', 
            'exit_date', 
            'exit_price', 
            'shares', 
            'profit_loss', 
            'exit_reason'
        )

        return JsonResponse({
            'backtest_id': result.id,
            'symbol': symbol,
            'total_return': float(result.total_return),
            'num_trades': result.num_trades,
            'max_drawdown': float(result.max_drawdown),
            'data_period': {
                'start_date': stock_data['date'].min().strftime('%Y-%m-%d'),
                'end_date': stock_data['date'].max().strftime('%Y-%m-%d'),
                'total_days': len(stock_data)
            },
            'parameters_used': {
                'initial_capital': float(data.get('initial_capital', 10000)),
                'prediction_threshold': float(data.get('prediction_threshold', 0.02)),
                'stop_loss': float(data.get('stop_loss', 0.05)),
                'take_profit': float(data.get('take_profit', 0.05))
            },
            'trades': list(trades)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)