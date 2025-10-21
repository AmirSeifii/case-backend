from django.contrib import admin
from .models import Customer, Restaurant, Order, OrderItem, OrderEvent


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'second_name', 'phone_number']
    search_fields = ['first_name', 'second_name', 'phone_number']


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'phone_number', 'address']
    search_fields = ['name', 'phone_number']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    readonly_fields = ['event_type', 'event_data', 'created_at']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'restaurant', 'customer', 'status', 
        'preparation_status', 'total_amount', 'placed_at'
    ]
    list_filter = ['status', 'preparation_status', 'placed_at']
    search_fields = ['customer__first_name', 'customer__second_name', 'restaurant__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [OrderItemInline, OrderEventInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('restaurant', 'customer', 'total_amount')
        }),
        ('Status', {
            'fields': ('status', 'preparation_status', 'rejection_reason', 'delay_minutes')
        }),
        ('Timestamps', {
            'fields': ('placed_at', 'accepted_at', 'delivered_at', 'cancelled_at', 'created_at', 'updated_at')
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'menu_item', 'quantity', 'unit_price', 'total_price']
    list_filter = ['order__restaurant']
    search_fields = ['menu_item', 'order__id']


@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'event_type', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['order__id', 'event_type']
    readonly_fields = ['order', 'event_type', 'event_data', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
