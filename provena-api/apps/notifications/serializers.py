from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "notification_type", "title", "body", "data", "is_read", "created_at"]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "email_order_placed",
            "email_order_dispatched",
            "email_new_order",
            "email_payout_received",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
