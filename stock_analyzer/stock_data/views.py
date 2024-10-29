# stock_data/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .tasks import fetch_stock_data, get_stock_data_task
import time

@api_view(['POST'])
def fetch_multiple_stocks(request):
    # Get symbols from request body
    symbols = request.data.get('symbols', [])
    
    if not symbols:
        return Response({
            'error': 'No symbols provided'
        }, status=400)
    
    results = []
    for symbol in symbols:
        # Fetch data for each symbol
        result = fetch_stock_data(symbol.upper())
        results.append(result)
        
        # Respect API rate limits (5 calls per minute for free tier)
        time.sleep(12)  # Wait 12 seconds between calls
    
    return Response({
        'results': results
    })

@api_view(['POST'])
def get_stock_data_view(request):
    stock_requests = request.data
    
    if not stock_requests or not isinstance(stock_requests, list):
        return Response(
            {'error': 'Please provide an array of stock requests'}, 
            status=400
        )

    results = {}
    for stock_req in stock_requests:
        symbol = stock_req.get('symbol')
        start_date = stock_req.get('start_date')
        end_date = stock_req.get('end_date')
        
        if not symbol:
            continue
            
        stock_data = get_stock_data_task(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get the prices list from stock_data['data']
        prices = stock_data['data']
        
        # Restructure into parallel arrays
        results[symbol] = {
            'symbol': symbol,
            'timeframe': 'daily',
            'dates': [str(price['date']) for price in prices],
            'opens': [float(price['open']) for price in prices],
            'closes': [float(price['close']) for price in prices],
            'volumes': [int(price['volume']) for price in prices]
        }

    return Response({
        'data': results,
        'metadata': {
            'requested_count': len(stock_requests),
            'returned_count': len(results)
        }
    })