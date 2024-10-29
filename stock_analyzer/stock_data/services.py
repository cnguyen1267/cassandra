# stock_data/services.py
import requests
import os
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

from .models import StockPrice

load_dotenv()

class AlphaVantageService:
    def __init__(self):
        self.api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        self.base_url = 'https://www.alphavantage.co/query'
        
    def fetch_daily_prices(self, symbol: str) -> Optional[List[Dict]]:
        """
        Fetch daily stock prices for a given symbol.
        Returns list of price data or None if error occurs.
        """
        try:
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': symbol,
                'outputsize': 'full',  # gets up to 20 years of data
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()  # Raises exception for 4XX/5XX status codes
            
            data = response.json()
            
            # Check for API error messages
            if "Error Message" in data:
                raise ValueError(f"API Error: {data['Error Message']}")
                
            time_series = data.get('Time Series (Daily)', {})
            
            processed_data = []
            for date, values in time_series.items():
                processed_data.append({
                    'symbol': symbol,
                    'date': datetime.strptime(date, '%Y-%m-%d').date(),
                    'open_price': Decimal(values['1. open']),
                    'high_price': Decimal(values['2. high']),
                    'low_price': Decimal(values['3. low']),
                    'close_price': Decimal(values['4. close']),
                    'volume': int(values['5. volume'])
                })
            
            return processed_data
            
        except requests.RequestException as e:
            print(f"Network error occurred: {e}")
            return None
        except ValueError as e:
            print(f"Data processing error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
        
class StockDataService:
    @staticmethod
    def get_stock_history(symbol, start_date=None, end_date=None):
        """Raw database fetching"""
        query = StockPrice.objects.filter(symbol=symbol)
        
        if start_date:
            query = query.filter(date__gte=start_date)
        if end_date:
            query = query.filter(date__lte=end_date)
            
        return query.order_by('-date')
