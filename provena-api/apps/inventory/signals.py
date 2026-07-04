from django.dispatch import Signal

# Fired when a StockLevel's quantity_available drops to or below low_stock_threshold.
# Providing: variant (ProductVariant), stock_level (StockLevel), quantity_available (int)
low_stock_alert = Signal()
