from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
import random
from django.utils import timezone
from django.db.models import Q
from django.core.management import call_command
import io

from .models import Customer, Restaurant, Order, OrderItem, OrderEvent
from .serializers import (
    CustomerSerializer, RestaurantSerializer, OrderSerializer,
    OrderItemSerializer, OrderEventSerializer, OrderListSerializer
)
from .kyte_client import kyte_client

class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for Customer model"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class RestaurantViewSet(viewsets.ModelViewSet):
    """ViewSet for Restaurant model"""
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order model with custom actions for order management.
    Includes actions for accepting, rejecting, and updating order status.
    """
    queryset = Order.objects.all().select_related('customer', 'restaurant').prefetch_related('items', 'events')

    def get_serializer_class(self):
        if self.action == 'list':
            return OrderListSerializer
        return OrderSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        restaurant_id = self.request.query_params.get('restaurant_id')
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)

        order_status = self.request.query_params.get('status')
        if order_status:
            queryset = queryset.filter(status=order_status)

        prep_status = self.request.query_params.get('preparation_status')
        if prep_status:
            queryset = queryset.filter(preparation_status=prep_status)
        return queryset

    def _create_order_event(self, order, event_type, event_data=None):
        OrderEvent.objects.create(order=order, event_type=event_type, event_data=event_data or {})

    # ---------- Simulation helpers exposed as actions ----------
    @action(detail=False, methods=['post'])
    def simulate_create(self, request):
        restaurant_id = int(request.data.get('restaurant_id') or 1)

        customers = list(Customer.objects.all())
        if not customers:
            return Response({'error': 'No customers available'}, status=status.HTTP_400_BAD_REQUEST)

        customer = random.choice(customers)
        placed_at = timezone.now().isoformat()

        sample_items = [
            {"menu_item": "Random Pizza", "quantity": 1, "unit_price": 12.5},
            {"menu_item": "Garlic Bread", "quantity": 1, "unit_price": 5.0},
            {"menu_item": "Soft Drink", "quantity": 1, "unit_price": 2.5},
        ]
        items = random.sample(sample_items, k=random.randint(1, len(sample_items)))
        total_amount = round(sum(i['unit_price'] * i['quantity'] for i in items), 2)

        payload = {
            'restaurant_id': restaurant_id,
            'customer_id': customer.id,
            'placed_at': placed_at,
            'total_amount': total_amount,
            'items': items,
        }
        response = handle_order_created_event(payload)
        return Response(response, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def simulate_cancel(self, request):
        restaurant_id = int(request.data.get('restaurant_id') or 1)

        # Prefer READY orders, then in-progress (accepted/delayed), then pending
        ready_qs = Order.objects.filter(
            restaurant_id=restaurant_id,
            status=Order.OrderStatus.READY
        ).exclude(status=Order.OrderStatus.CANCELLED)

        inprog_qs = Order.objects.filter(
            restaurant_id=restaurant_id,
            preparation_status__in=[
                Order.PreparationStatus.ACCEPTED,
                Order.PreparationStatus.DELAYED,
            ]
        ).exclude(status__in=[Order.OrderStatus.DELIVERED, Order.OrderStatus.CANCELLED])

        pending_qs = Order.objects.filter(
            restaurant_id=restaurant_id
        ).filter(
            Q(preparation_status__isnull=True) | Q(preparation_status=Order.PreparationStatus.PENDING)
        ).exclude(status__in=[Order.OrderStatus.DELIVERED, Order.OrderStatus.CANCELLED])

        order = None
        for qs in (ready_qs, inprog_qs, pending_qs):
            o = qs.order_by('?').first()
            if o:
                order = o
                break

        if not order:
            return Response({'error': 'No cancellable orders found'}, status=status.HTTP_400_BAD_REQUEST)

        payload = {'order_id': order.id, 'reason': 'Simulated cancellation'}
        response = handle_order_cancelled_event(payload)
        return Response(response)

    # ---------- Core actions ----------
    @action(detail=True, methods=['post'])
    def accept_preparation(self, request, pk=None):
        order = self.get_object()
        if order.preparation_status == Order.PreparationStatus.ACCEPTED:
            return Response({'error': 'Order has already been accepted'}, status=status.HTTP_400_BAD_REQUEST)
        order.preparation_status = Order.PreparationStatus.ACCEPTED
        order.accepted_at = timezone.now()
        order.save()
        self._create_order_event(order, 'preparation_accepted', {'accepted_at': order.accepted_at.isoformat()})
        kyte_client.notify_preparation_accepted(order.id)
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject_preparation(self, request, pk=None):
        order = self.get_object()
        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': 'Rejection reason is required'}, status=status.HTTP_400_BAD_REQUEST)
        order.preparation_status = Order.PreparationStatus.REJECTED
        order.rejection_reason = reason
        order.status = Order.OrderStatus.CANCELLED
        order.cancelled_at = timezone.now()
        order.save()
        self._create_order_event(order, 'preparation_rejected', {'reason': reason, 'rejected_at': timezone.now().isoformat()})
        kyte_client.notify_preparation_rejected(order.id, reason)
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_delayed(self, request, pk=None):
        order = self.get_object()
        delay_minutes = request.data.get('delay_minutes')
        reason = request.data.get('reason', '')
        if not delay_minutes:
            return Response({'error': 'Delay minutes is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            delay_minutes = int(delay_minutes)
            if delay_minutes <= 0:
                raise ValueError('Delay minutes must be positive')
        except (ValueError, TypeError):
            return Response({'error': 'Invalid delay minutes value'}, status=status.HTTP_400_BAD_REQUEST)
        order.preparation_status = Order.PreparationStatus.DELAYED
        order.delay_minutes = (order.delay_minutes or 0) + delay_minutes
        order.save()
        self._create_order_event(order, 'preparation_delayed', {
            'delay_minutes': delay_minutes,
            'reason': reason,
            'delayed_at': timezone.now().isoformat(),
        })
        kyte_client.notify_preparation_delayed(order.id, delay_minutes, reason)
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_cancelled(self, request, pk=None):
        order = self.get_object()
        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': 'Cancellation reason is required'}, status=status.HTTP_400_BAD_REQUEST)
        order.preparation_status = Order.PreparationStatus.CANCELLED
        order.status = Order.OrderStatus.CANCELLED
        order.cancelled_at = timezone.now()
        order.rejection_reason = reason
        order.save()
        self._create_order_event(order, 'preparation_cancelled', {'reason': reason, 'cancelled_at': timezone.now().isoformat()})
        kyte_client.notify_preparation_cancelled(order.id, reason)
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_done(self, request, pk=None):
        order = self.get_object()
        if order.preparation_status not in (Order.PreparationStatus.ACCEPTED, Order.PreparationStatus.DELAYED):
            return Response({'error': 'Order must be accepted before marking as done'}, status=status.HTTP_400_BAD_REQUEST)
        order.preparation_status = Order.PreparationStatus.DONE
        order.status = Order.OrderStatus.READY
        order.save()
        self._create_order_event(order, 'preparation_done', {'completed_at': timezone.now().isoformat()})
        kyte_client.notify_preparation_done(order.id)
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        order = self.get_object()
        if order.status != Order.OrderStatus.READY:
            return Response({'error': 'Order must be ready before marking as delivered'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = Order.OrderStatus.DELIVERED
        order.save()
        self._create_order_event(order, 'order_delivered', {'delivered_at': timezone.now().isoformat()})
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        restaurant_id = request.query_params.get('restaurant_id')
        queryset = self.get_queryset().filter(
            Q(preparation_status__isnull=True) | Q(preparation_status=Order.PreparationStatus.PENDING)
        )
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        serializer = OrderListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        restaurant_id = request.query_params.get('restaurant_id')
        queryset = self.get_queryset().filter(
            preparation_status__in=[Order.PreparationStatus.ACCEPTED, Order.PreparationStatus.DELAYED]
        )
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        serializer = OrderListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def cancelled(self, request):
        """Return cancelled orders for a restaurant, newest first.

        These are used by the UI to surface recently-cancelled items prominently
        until acknowledged by the user.
        """
        restaurant_id = request.query_params.get('restaurant_id')
        stage = request.query_params.get('stage')  # 'preparation' | 'ready'
        source = request.query_params.get('source')  # 'kyte' | 'staff'
        queryset = self.get_queryset().filter(status=Order.OrderStatus.CANCELLED)
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)

        # Stage filtering: treat orders that have a 'preparation_done' event as
        # ready-level cancellations. Others are preparation-level.
        if stage == 'ready':
            queryset = queryset.filter(events__event_type='preparation_done').distinct()
        elif stage == 'preparation':
            queryset = queryset.exclude(events__event_type='preparation_done').distinct()

        # Source filtering: Kyte cancellations create 'order_cancelled' events.
        # Staff cancellations use 'preparation_cancelled' (or 'preparation_rejected').
        if source == 'kyte':
            queryset = queryset.filter(events__event_type='order_cancelled').distinct()
        elif source == 'staff':
            queryset = queryset.exclude(events__event_type='order_cancelled').distinct()
        serializer = OrderListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def simulate(self, request):
        count = request.data.get('count', 5)
        try:
            out = io.StringIO()
            call_command('generate_orders', count=count, restaurant_id=1, stdout=out)
            return Response({'message': f'Successfully generated {count} random orders', 'count': count}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class KyteWebhookView(APIView):
    """Inbound webhook to handle events from Kyte (mock).

    Supported events:
    - order_created
    - order_cancelled
    """

    def post(self, request):
        event_type = request.data.get('type')
        data = request.data.get('data', {})

        if not event_type:
            return Response({'error': 'Missing event type'}, status=status.HTTP_400_BAD_REQUEST)

        if event_type == 'order_created':
            try:
                response = handle_order_created_event(data)
                return Response(response, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if event_type == 'order_cancelled':
            try:
                response = handle_order_cancelled_event(data)
                return Response(response)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'error': 'Unsupported event'}, status=status.HTTP_400_BAD_REQUEST)


def handle_order_created_event(data):
    """Create local order from an order_created event payload.

    Expected data keys: restaurant_id, customer_id, placed_at; optional: total_amount, items
    """
    try:
        restaurant_id = data['restaurant_id']
        customer_id = data['customer_id']
        placed_at = data['placed_at']
    except KeyError as e:
        raise ValueError(f"Missing field: {e.args[0]}")

    try:
        restaurant = Restaurant.objects.get(id=restaurant_id)
        customer = Customer.objects.get(id=customer_id)
    except (Restaurant.DoesNotExist, Customer.DoesNotExist):
        raise ValueError('Invalid restaurant_id or customer_id')

    order = Order.objects.create(
        restaurant=restaurant,
        customer=customer,
        status=Order.OrderStatus.CREATED,
        preparation_status=Order.PreparationStatus.PENDING,
        total_amount=data.get('total_amount'),
        placed_at=placed_at,
    )

    # Optional items
    items = data.get('items', [])
    for item in items:
        OrderItem.objects.create(
            order=order,
            menu_item=item.get('menu_item', 'Item'),
            quantity=item.get('quantity', 1),
            unit_price=item.get('unit_price', 0),
        )

    OrderEvent.objects.create(order=order, event_type='order_created', event_data=data)
    return {'message': 'order_created processed', 'order_id': order.id}


def handle_order_cancelled_event(data):
    """Cancel local order from an order_cancelled event payload.

    Expected data keys: order_id; optional: reason
    """
    order_id = data.get('order_id')
    reason = data.get('reason', '')
    if not order_id:
        raise ValueError('order_id is required')

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise ValueError('Order not found')

    order.status = Order.OrderStatus.CANCELLED
    order.preparation_status = Order.PreparationStatus.CANCELLED
    order.rejection_reason = reason
    order.cancelled_at = timezone.now()
    order.save()

    OrderEvent.objects.create(order=order, event_type='order_cancelled', event_data=data)
    return {'message': 'order_cancelled processed', 'order_id': order.id}


# Convenience endpoints to simulate Kyte events from the UI
@action(detail=False, methods=['post'])
def simulate_create(self, request):
    """Simulate a Kyte order_created for a given restaurant (default id=1)."""
    restaurant_id = int(request.data.get('restaurant_id') or 1)

    customers = list(Customer.objects.all())
    if not customers:
        return Response({'error': 'No customers available'}, status=status.HTTP_400_BAD_REQUEST)

    customer = random.choice(customers)
    placed_at = timezone.now().isoformat()

    # Simple random items
    sample_items = [
        {"menu_item": "Random Pizza", "quantity": 1, "unit_price": 12.5},
        {"menu_item": "Garlic Bread", "quantity": 1, "unit_price": 5.0},
        {"menu_item": "Soft Drink", "quantity": 1, "unit_price": 2.5},
    ]
    items = random.sample(sample_items, k=random.randint(1, len(sample_items)))
    total_amount = round(sum(i['unit_price'] * i['quantity'] for i in items), 2)

    payload = {
        'restaurant_id': restaurant_id,
        'customer_id': customer.id,
        'placed_at': placed_at,
        'total_amount': total_amount,
        'items': items,
    }

    response = handle_order_created_event(payload)
    return Response(response, status=status.HTTP_201_CREATED)


@action(detail=False, methods=['post'])
def simulate_cancel(self, request):
    """Simulate a Kyte order_cancelled for a random not-delivered order for restaurant id=1."""
    restaurant_id = int(request.data.get('restaurant_id') or 1)

    # Choose random order that is not delivered
    candidates = Order.objects.filter(
        restaurant_id=restaurant_id
    ).exclude(status=Order.OrderStatus.DELIVERED).order_by('?')

    order = candidates.first()
    if not order:
        return Response({'error': 'No cancellable orders found'}, status=status.HTTP_400_BAD_REQUEST)

    payload = {
        'order_id': order.id,
        'reason': 'Simulated cancellation',
    }

    response = handle_order_cancelled_event(payload)
    return Response(response)
    
    @action(detail=True, methods=['post'])
    def reject_preparation(self, request, pk=None):
        """
        Reject the order preparation.
        This is called when the restaurant cannot prepare the order.
        """
        order = self.get_object()
        
        # Get rejection reason
        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update order
        order.preparation_status = Order.PreparationStatus.REJECTED
        order.rejection_reason = reason
        order.status = Order.OrderStatus.CANCELLED
        order.cancelled_at = timezone.now()
        order.save()
        
        # Create event
        self._create_order_event(
            order,
            'preparation_rejected',
            {'reason': reason, 'rejected_at': timezone.now().isoformat()}
        )
        

        # Notify Kyte (mock)
        kyte_client.notify_preparation_rejected(order.id, reason)

        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_delayed(self, request, pk=None):
        """
        Mark the order as delayed.
        This is called when the restaurant needs more time to prepare the order.
        """
        order = self.get_object()
        
        # Get delay information
        delay_minutes = request.data.get('delay_minutes')
        reason = request.data.get('reason', '')
        
        if not delay_minutes:
            return Response(
                {'error': 'Delay minutes is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            delay_minutes = int(delay_minutes)
            if delay_minutes <= 0:
                raise ValueError("Delay minutes must be positive")
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid delay minutes value'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update order
        order.preparation_status = Order.PreparationStatus.DELAYED
        # Accumulate delay rather than overwrite
        order.delay_minutes = (order.delay_minutes or 0) + delay_minutes
        order.save()
        
        # Create event
        self._create_order_event(
            order,
            'preparation_delayed',
            {
                'delay_minutes': delay_minutes,
                'reason': reason,
                'delayed_at': timezone.now().isoformat()
            }
        )
        

        # Notify Kyte (mock)
        kyte_client.notify_preparation_delayed(order.id, delay_minutes, reason)

        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_cancelled(self, request, pk=None):
        """
        Mark the order preparation as cancelled.
        This is called when the restaurant needs to cancel an already accepted order.
        """
        order = self.get_object()
        
        # Get cancellation reason
        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'Cancellation reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update order
        order.preparation_status = Order.PreparationStatus.CANCELLED
        order.status = Order.OrderStatus.CANCELLED
        order.cancelled_at = timezone.now()
        order.rejection_reason = reason
        order.save()
        
        # Create event
        self._create_order_event(
            order,
            'preparation_cancelled',
            {'reason': reason, 'cancelled_at': timezone.now().isoformat()}
        )
        

        # Notify Kyte (mock)
        kyte_client.notify_preparation_cancelled(order.id, reason)

        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_done(self, request, pk=None):
        """
        Mark the order preparation as done.
        This is called when the restaurant has finished preparing the order.
        """
        order = self.get_object()
        
        # Validate that order was accepted
        if order.preparation_status != Order.PreparationStatus.ACCEPTED and \
           order.preparation_status != Order.PreparationStatus.DELAYED:
            return Response(
                {'error': 'Order must be accepted before marking as done'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update order
        order.preparation_status = Order.PreparationStatus.DONE
        order.status = Order.OrderStatus.READY
        order.save()
        
        # Create event
        self._create_order_event(
            order,
            'preparation_done',
            {'completed_at': timezone.now().isoformat()}
        )
        

        # Notify Kyte (mock)
        kyte_client.notify_preparation_done(order.id)

        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        """
        Mark the order as delivered.
        This is called when the order has been picked up by the drone/delivery service.
        """
        order = self.get_object()
        
        # Validate that order is ready
        if order.status != Order.OrderStatus.READY:
            return Response(
                {'error': 'Order must be ready before marking as delivered'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update order
        order.status = Order.OrderStatus.DELIVERED
        order.save()
        
        # Create event
        self._create_order_event(
            order,
            'order_delivered',
            {'delivered_at': timezone.now().isoformat()}
        )
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending orders (created but not yet accepted or rejected)"""
        restaurant_id = request.query_params.get('restaurant_id')
        
        queryset = self.get_queryset().filter(
            Q(preparation_status__isnull=True) | 
            Q(preparation_status=Order.PreparationStatus.PENDING)
        )
        
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        
        serializer = OrderListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active orders (accepted or delayed)"""
        restaurant_id = request.query_params.get('restaurant_id')
        
        queryset = self.get_queryset().filter(
            preparation_status__in=[
                Order.PreparationStatus.ACCEPTED,
                Order.PreparationStatus.DELAYED
            ]
        )
        
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        
        serializer = OrderListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def simulate(self, request):
        """Generate random orders for testing"""
        count = request.data.get('count', 5)
        
        try:
            # Capture command output
            out = io.StringIO()
            call_command('generate_orders', count=count, restaurant_id=1, stdout=out)

            return Response({
                'message': f'Successfully generated {count} random orders',
                'count': count
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderItemViewSet(viewsets.ModelViewSet):
    """ViewSet for OrderItem model"""
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer


class OrderEventViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for OrderEvent model (read-only)"""
    queryset = OrderEvent.objects.all()
    serializer_class = OrderEventSerializer
    
    def get_queryset(self):
        """Filter events by order if order_id is provided"""
        queryset = super().get_queryset()
        order_id = self.request.query_params.get('order_id', None)
        
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        
        return queryset
