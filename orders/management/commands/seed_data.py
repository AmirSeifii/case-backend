from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from orders.models import Customer, Restaurant, Order, OrderItem


class Command(BaseCommand):
    help = 'Seeds the database with demo data for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database with demo data...')
        
        # Clear existing data
        self.stdout.write('Clearing existing data...')
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        Customer.objects.all().delete()
        Restaurant.objects.all().delete()
        
        # Create restaurants
        self.stdout.write('Creating restaurants...')
        restaurant1 = Restaurant.objects.create(
            name="Pizza Paradise",
            address="123 Main St, Downtown",
            phone_number="+1-555-0101"
        )
        restaurant2 = Restaurant.objects.create(
            name="Burger Barn",
            address="456 Oak Ave, Midtown",
            phone_number="+1-555-0102"
        )
        restaurant3 = Restaurant.objects.create(
            name="Sushi Station",
            address="789 Pine Rd, Uptown",
            phone_number="+1-555-0103"
        )
        
        # Create customers
        self.stdout.write('Creating customers...')
        customer1 = Customer.objects.create(
            first_name="John",
            second_name="Doe",
            phone_number="+1-555-1001",
            address="100 Customer Lane, Apt 1"
        )
        customer2 = Customer.objects.create(
            first_name="Jane",
            second_name="Smith",
            phone_number="+1-555-1002",
            address="200 Buyer Blvd, Suite 5"
        )
        customer3 = Customer.objects.create(
            first_name="Bob",
            second_name="Johnson",
            phone_number="+1-555-1003",
            address="300 Client Court, Unit 10"
        )
        customer4 = Customer.objects.create(
            first_name="Alice",
            second_name="Williams",
            phone_number="+1-555-1004",
            address="400 Patron Place, Apt 3"
        )
        
        # Create orders
        self.stdout.write('Creating orders...')
        now = timezone.now()
        
        # Order 1 - New order waiting for response (Pizza Paradise)
        order1 = Order.objects.create(
            restaurant=restaurant1,
            customer=customer1,
            status=Order.OrderStatus.CREATED,
            preparation_status=None,
            total_amount=45.99,
            placed_at=now - timedelta(minutes=5)
        )
        OrderItem.objects.create(
            order=order1,
            menu_item="Large Pepperoni Pizza",
            quantity=2,
            unit_price=15.99
        )
        OrderItem.objects.create(
            order=order1,
            menu_item="Garlic Bread",
            quantity=1,
            unit_price=6.99
        )
        OrderItem.objects.create(
            order=order1,
            menu_item="Caesar Salad",
            quantity=1,
            unit_price=7.99
        )
        
        # Order 2 - Another new order (Pizza Paradise)
        order2 = Order.objects.create(
            restaurant=restaurant1,
            customer=customer2,
            status=Order.OrderStatus.CREATED,
            preparation_status=None,
            total_amount=28.50,
            placed_at=now - timedelta(minutes=2)
        )
        OrderItem.objects.create(
            order=order2,
            menu_item="Medium Margherita Pizza",
            quantity=1,
            unit_price=12.99
        )
        OrderItem.objects.create(
            order=order2,
            menu_item="Buffalo Wings",
            quantity=1,
            unit_price=10.99
        )
        OrderItem.objects.create(
            order=order2,
            menu_item="Soft Drink",
            quantity=2,
            unit_price=2.50
        )
        
        # Order 3 - Accepted and being prepared (Burger Barn)
        order3 = Order.objects.create(
            restaurant=restaurant2,
            customer=customer3,
            status=Order.OrderStatus.ACCEPTED,
            preparation_status=Order.PreparationStatus.ACCEPTED,
            total_amount=32.75,
            placed_at=now - timedelta(minutes=15),
            accepted_at=now - timedelta(minutes=12)
        )
        OrderItem.objects.create(
            order=order3,
            menu_item="Classic Cheeseburger",
            quantity=2,
            unit_price=12.99
        )
        OrderItem.objects.create(
            order=order3,
            menu_item="French Fries",
            quantity=2,
            unit_price=3.99
        )
        
        # Order 4 - Delayed order (Burger Barn)
        order4 = Order.objects.create(
            restaurant=restaurant2,
            customer=customer4,
            status=Order.OrderStatus.ACCEPTED,
            preparation_status=Order.PreparationStatus.DELAYED,
            delay_minutes=15,
            total_amount=55.80,
            placed_at=now - timedelta(minutes=20),
            accepted_at=now - timedelta(minutes=18)
        )
        OrderItem.objects.create(
            order=order4,
            menu_item="BBQ Bacon Burger",
            quantity=3,
            unit_price=15.99
        )
        OrderItem.objects.create(
            order=order4,
            menu_item="Onion Rings",
            quantity=2,
            unit_price=4.99
        )
        
        # Order 5 - New order (Sushi Station)
        order5 = Order.objects.create(
            restaurant=restaurant3,
            customer=customer1,
            status=Order.OrderStatus.CREATED,
            preparation_status=None,
            total_amount=78.90,
            placed_at=now - timedelta(minutes=3)
        )
        OrderItem.objects.create(
            order=order5,
            menu_item="Dragon Roll",
            quantity=2,
            unit_price=16.99
        )
        OrderItem.objects.create(
            order=order5,
            menu_item="California Roll",
            quantity=2,
            unit_price=12.99
        )
        OrderItem.objects.create(
            order=order5,
            menu_item="Miso Soup",
            quantity=2,
            unit_price=4.50
        )
        OrderItem.objects.create(
            order=order5,
            menu_item="Green Tea",
            quantity=2,
            unit_price=2.99
        )
        
        # Order 6 - Completed order (Sushi Station)
        order6 = Order.objects.create(
            restaurant=restaurant3,
            customer=customer2,
            status=Order.OrderStatus.READY,
            preparation_status=Order.PreparationStatus.DONE,
            total_amount=45.50,
            placed_at=now - timedelta(minutes=35),
            accepted_at=now - timedelta(minutes=32)
        )
        OrderItem.objects.create(
            order=order6,
            menu_item="Salmon Sashimi",
            quantity=1,
            unit_price=18.99
        )
        OrderItem.objects.create(
            order=order6,
            menu_item="Tuna Roll",
            quantity=2,
            unit_price=13.99
        )
        
        self.stdout.write(self.style.SUCCESS('✅ Successfully seeded database!'))
        self.stdout.write(f'Created:')
        self.stdout.write(f'  - {Restaurant.objects.count()} restaurants')
        self.stdout.write(f'  - {Customer.objects.count()} customers')
        self.stdout.write(f'  - {Order.objects.count()} orders')
        self.stdout.write(f'  - {OrderItem.objects.count()} order items')
        self.stdout.write('')
        self.stdout.write('Restaurant IDs:')
        for restaurant in Restaurant.objects.all():
            self.stdout.write(f'  - {restaurant.name} (ID: {restaurant.id})')

