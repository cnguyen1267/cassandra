from django.urls import path
from . import views

urlpatterns = [
    path('<str:symbol>/', views.backtest_view, name='backtest'),
]