from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import StockPrice

@admin.register(StockPrice)
class StockPriceAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'date', 'open_price', 'close_price', 'volume']
    list_filter = ['symbol', 'date']
    search_fields = ['symbol']
    ordering = ['-date']