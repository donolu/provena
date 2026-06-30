from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

    def ready(self):
        from apps.inventory.signals import low_stock_alert

        from .handlers import handle_low_stock_alert

        low_stock_alert.connect(
            handle_low_stock_alert, dispatch_uid="notifications.low_stock_alert"
        )
