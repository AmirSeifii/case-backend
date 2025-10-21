from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerViewSet, RestaurantViewSet, OrderViewSet,
    OrderItemViewSet, OrderEventViewSet, KyteWebhookView
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'restaurants', RestaurantViewSet, basename='restaurant')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-items', OrderItemViewSet, basename='orderitem')
router.register(r'order-events', OrderEventViewSet, basename='orderevent')

urlpatterns = [
    path('', include(router.urls)),
    path('kyte/events/', KyteWebhookView.as_view(), name='kyte-webhook'),
]

