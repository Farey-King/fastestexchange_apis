from django.apps import AppConfig


class FastestExchangeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fastest_exchange'

    def ready(self) -> None:
        import fastest_exchange.signals
        return super().ready()
