from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache

from .views import WS_TICKET_PREFIX, WS_TICKET_TTL


@database_sync_to_async
def _get_user(user_id: str):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        qs = parse_qs(scope.get("query_string", b"").decode())
        ticket_list = qs.get("ticket", [])
        scope["user"] = AnonymousUser()
        if ticket_list:
            key = f"{WS_TICKET_PREFIX}{ticket_list[0]}"
            user_id = cache.get(key)
            if user_id:
                claimed = cache.add(f"{key}:claimed", "1", timeout=WS_TICKET_TTL)
                if claimed:
                    cache.delete(key)
                    scope["user"] = await _get_user(user_id)
        return await super().__call__(scope, receive, send)
