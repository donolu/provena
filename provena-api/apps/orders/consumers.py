import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Order

logger = logging.getLogger(__name__)


def _order_group(reference: str) -> str:
    return f"order_{reference}"


class OrderStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.reference = self.scope["url_route"]["kwargs"]["reference"]
        owns = await self._buyer_owns_order(user, self.reference)
        if not owns:
            await self.close(code=4003)
            return

        self.group_name = _order_group(self.reference)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass  # server-push only; client messages are ignored

    async def order_status(self, event):
        await self.send(text_data=json.dumps({"type": "order_status", "status": event["status"]}))

    @database_sync_to_async
    def _buyer_owns_order(self, user, reference: str) -> bool:
        return Order.objects.filter(reference=reference, buyer=user).exists()
