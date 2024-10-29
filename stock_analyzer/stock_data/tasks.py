# stock_data/tasks.py
from .models import StockPrice
from .services import AlphaVantageService, StockDataService
from django.db import transaction
from datetime import datetime, timedelta
import time

def fetch_stock_data(symbol: str) -> dict:
    """
    Fetch and store stock data for a given symbol.
    Returns dictionary with status and message.
    """
    service = AlphaVantageService()
    
    try:
        # Fetch the data
        data = service.fetch_daily_prices(symbol)
        
        if not data:
            return {
                'status': 'error',
                'message': f'Failed to fetch data for {symbol}'
            }
            
        # Store the data
        with transaction.atomic():
            for price_data in data:
                StockPrice.objects.update_or_create(
                    symbol=price_data['symbol'],
                    date=price_data['date'],
                    defaults={
                        'open_price': price_data['open_price'],
                        'high_price': price_data['high_price'],
                        'low_price': price_data['low_price'],
                        'close_price': price_data['close_price'],
                        'volume': price_data['volume']
                    }
                )
                
        return {
            'status': 'success',
            'message': f'Successfully updated data for {symbol}'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error processing {symbol}: {str(e)}'
        }

def get_stock_data_task(symbol: str, start_date=None, end_date=None):
    data = StockDataService.get_stock_history(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date
    )
    
    prices = [{
        'date': stock.date,
        'open': stock.open_price,
        'close': stock.close_price,
        'volume': stock.volume
    } for stock in data]

    return {
        'symbol': symbol,
        'timeframe': 'daily',
        'data': prices,
        'metadata': {
            'count': len(prices),
            'start_date': start_date,
            'end_date': end_date
        }
    }