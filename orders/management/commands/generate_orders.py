import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from orders.models import Customer, Restaurant, Order, OrderItem


class Command(BaseCommand):
    help = 'Generates random orders for testing'

    MENU_ITEMS = {
        1: [  # Pizza Paradise
            ('Large Pepperoni Pizza', 15.99),
            ('Medium Margherita Pizza', 12.99),
            ('Garlic Bread', 6.99),
            ('Caesar Salad', 7.99),
            ('Buffalo Wings', 10.99),
            ('Soft Drink', 2.50),
        ],
        2: [  # Burger Barn
            ('Classic Cheeseburger', 12.99),
            ('BBQ Bacon Burger', 15.99),
            ('French Fries', 3.99),
            ('Onion Rings', 4.99),
            ('Milkshake', 5.99),
        ],
        3: [  # Sushi Station
            ('Dragon Roll', 16.99),
            ('California Roll', 12.99),
            ('Salmon Sashimi', 18.99),
            ('Tuna Roll', 13.99),
            ('Miso Soup', 4.50),
            ('Green Tea', 2.99),
        ],
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of orders to generate'
        )
        parser.add_argument(
            '--restaurant-id',
            type=int,
            default=None,
            help='Restrict generation to a specific restaurant id'
        )

    def handle(self, *args, **options):
        count = options['count']
        target_restaurant_id = options.get('restaurant_id')

        if target_restaurant_id is not None:
            restaurants = list(Restaurant.objects.filter(id=target_restaurant_id))
            if not restaurants:
                self.stdout.write(self.style.ERROR(f'Restaurant with id {target_restaurant_id} not found.'))
                return
        else:
            restaurants = list(Restaurant.objects.all())
        customers = list(Customer.objects.all())
        
        if not restaurants or not customers:
            self.stdout.write(self.style.ERROR('No restaurants or customers found. Run seed_data first.'))
            return
        
        now = timezone.now()
        orders_created = 0
        
        for _ in range(count):
            restaurant = random.choice(restaurants)
            customer = random.choice(customers)
            
            # Random time in the last 1-15 minutes
            minutes_ago = random.randint(1, 15)
            placed_at = now - timedelta(minutes=minutes_ago)
            
            # Create order
            order = Order.objects.create(
                restaurant=restaurant,
                customer=customer,
                status=Order.OrderStatus.CREATED,
                preparation_status=None,
                placed_at=placed_at,
                total_amount=0  # Will calculate after items
            )
            
            # Add random items (2-4 items per order)
            menu_items = self.MENU_ITEMS.get(restaurant.id, self.MENU_ITEMS[1])
            num_items = random.randint(2, 4)
            selected_items = random.sample(menu_items, min(num_items, len(menu_items)))
            
            total = 0
            for item_name, price in selected_items:
                quantity = random.randint(1, 3)
                OrderItem.objects.create(
                    order=order,
                    menu_item=item_name,
                    quantity=quantity,
                    unit_price=price
                )
                total += price * quantity
            
            # Update total
            order.total_amount = round(total, 2)
            order.save()
            
            orders_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Successfully generated {orders_created} random orders!')
        )

