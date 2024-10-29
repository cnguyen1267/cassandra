from django.urls import path
from . import views

urlpatterns = [
    path('stocks/import/', views.fetch_multiple_stocks, name='import_stocks'),
    path('stocks/history/', views.get_stock_data_view, name='stock_history'),
]