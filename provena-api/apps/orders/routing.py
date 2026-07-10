from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/orders/(?P<reference>[A-Z0-9-]+)/$",
        consumers.OrderStatusConsumer.as_asgi(),
    ),
]
