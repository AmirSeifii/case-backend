from django.db import models


class Customer(models.Model):
    """Customer model for storing customer information"""
    first_name = models.CharField(max_length=255)
    second_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=50)
    address = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'customer'
    
    def __str__(self):
        return f"{self.first_name} {self.second_name}"


class Restaurant(models.Model):
    """Restaurant model for storing restaurant information"""
    name = models.CharField(max_length=255)
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        db_table = 'restaurants'
    
    def __str__(self):
        return self.name


class Order(models.Model):
    """Order model for managing restaurant orders"""
    
    # Status choices for order lifecycle
    class OrderStatus(models.TextChoices):
        CREATED = 'created', 'Created'
        ACCEPTED = 'accepted', 'Accepted'
        PREPARING = 'preparing', 'Preparing'
        READY = 'ready', 'Ready'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'
    
    # Preparation status choices
    class PreparationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        DELAYED = 'delayed', 'Delayed'
        CANCELLED = 'cancelled', 'Cancelled'
        DONE = 'done', 'Done'
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.CREATED
    )
    preparation_status = models.CharField(
        max_length=20,
        choices=PreparationStatus.choices,
        null=True,
        blank=True
    )
    rejection_reason = models.TextField(null=True, blank=True)
    delay_minutes = models.IntegerField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Timestamps
    placed_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'orders'
        ordering = ['-placed_at']
        indexes = [
            models.Index(fields=['restaurant']),
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['placed_at']),
        ]
    
    def __str__(self):
        return f"Order #{self.id} - {self.restaurant.name} - {self.status}"


class OrderItem(models.Model):
    """Order items for storing individual menu items in an order"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'order_items'
    
    def __str__(self):
        return f"{self.quantity}x {self.menu_item}"
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price


class OrderEvent(models.Model):
    """Order events for tracking order status changes (audit trail)"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='events'
    )
    event_type = models.CharField(max_length=100)
    event_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['event_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - Order #{self.order.id}"
