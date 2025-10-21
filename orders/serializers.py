from rest_framework import serializers
from .models import Customer, Restaurant, Order, OrderItem, OrderEvent


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model"""
    
    class Meta:
        model = Customer
        fields = ['id', 'first_name', 'second_name', 'phone_number', 'address']


class RestaurantSerializer(serializers.ModelSerializer):
    """Serializer for Restaurant model"""
    
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'address', 'phone_number']


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model"""
    total_price = serializers.ReadOnlyField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'menu_item', 'quantity', 'unit_price', 'total_price']


class OrderEventSerializer(serializers.ModelSerializer):
    """Serializer for OrderEvent model"""
    
    class Meta:
        model = OrderEvent
        fields = ['id', 'event_type', 'event_data', 'created_at']
        read_only_fields = ['created_at']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model with nested items"""
    items = OrderItemSerializer(many=True, read_only=True)
    customer = CustomerSerializer(read_only=True)
    restaurant = RestaurantSerializer(read_only=True)
    events = OrderEventSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'restaurant', 'customer', 'status', 'preparation_status',
            'rejection_reason', 'delay_minutes', 'total_amount',
            'placed_at', 'accepted_at', 'delivered_at', 'cancelled_at',
            'created_at', 'updated_at', 'items', 'events'
        ]
        read_only_fields = ['created_at', 'updated_at']


class OrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for order list view"""
    customer_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'restaurant_name', 'customer_name', 'status', 
            'preparation_status', 'total_amount', 'placed_at', 
            'items_count', 'delay_minutes'
        ]
    
    def get_customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.second_name}"
    
    def get_restaurant_name(self, obj):
        return obj.restaurant.name
    
    def get_items_count(self, obj):
        return obj.items.count()
