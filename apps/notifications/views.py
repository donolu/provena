from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: NotificationSerializer(many=True)},
        tags=["Notifications"],
        summary="List notifications",
        description="Returns the authenticated user's notifications. Pass `?unread=true` to filter unread only.",
    )
    def get(self, request):
        qs = Notification.objects.filter(recipient=request.user)
        if request.query_params.get("unread", "").lower() == "true":
            qs = qs.filter(is_read=False)
        return Response(NotificationSerializer(qs, many=True).data)


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: NotificationSerializer},
        tags=["Notifications"],
        summary="Mark notification as read",
    )
    def post(self, request, pk):
        notification = services.mark_as_read(request.user, pk)
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: None},
        tags=["Notifications"],
        summary="Mark all notifications as read",
    )
    def post(self, request):
        count = services.mark_all_as_read(request.user)
        return Response({"marked_read": count})


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={204: None},
        tags=["Notifications"],
        summary="Delete a notification",
    )
    def delete(self, request, pk):
        services.delete_notification(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
