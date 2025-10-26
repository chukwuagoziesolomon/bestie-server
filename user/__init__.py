"""
Compatibility shim for legacy imports like `from user...`.
It re-exports modules from `bestyy.core_features.user` to avoid widespread refactors.
"""
from importlib import import_module
import sys

def _alias(submodule: str) -> None:
    source = f"bestyy.core_features.user.{submodule}"
    target = f"user.{submodule}"
    try:
        module = import_module(source)
        # Register as a real module for direct imports
        sys.modules[target] = module
        # Also expose as attribute on the `user` package (so code like `user.models` works)
        attr_name = submodule.split(".")[0]
        setattr(sys.modules[__name__], attr_name, import_module(f"bestyy.core_features.user.{attr_name}"))
    except Exception:
        # Silently ignore missing optional modules
        pass

# Common submodules referenced across the codebase
_SUBMODULES = [
    # Core modules
    "models",
    "urls",
    "routing",
    "permissions",
    "tasks",
    "utils",
    # Serializers
    "serializers",
    "serializers.user_serializers",
    "serializers.address_serializers",
    "serializers.order_serializers",
    "serializers.favorite_serializers",
    # Services
    "services",
    "services.paystack_service",
    "services.google_maps_service",
    "services.auto_favorite_service",
    "services.menu_update_notification_service",
    "services.personalized_recommendation_service",
    "services.notification_service",
    # API
    "api",
    "api.serializers",
    "api.user_views",
    "api.admin_views",
    "api.admin_order_views",
    "api.admin_user_management",
    "api.admin_revenue_views",
    "api.courier_dashboard_views",
    "api.courier_deliveries",
    "api.courier_company_analytics",
    "api.courier_delivery_activity",
    "api.paystack_webhooks",
    "api.unified_recommendation_view",
    "api.vendor_search_views",
    "api.vendor_orders",
    "api.whatsapp_test_views",
    "api.vendor_profile_views",
    "api.courier_verification_views",
    "api.food_customization_views",
]

for _sub in _SUBMODULES:
    _alias(_sub)


