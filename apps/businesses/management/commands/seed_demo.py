from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.licensing.models import License
from apps.menu.models import Category, MenuItem
from apps.tables.models import Table


class Command(BaseCommand):
    help = 'Create or reset local development POS demo data.'

    def handle(self, *args, **options):
        now = timezone.now()
        business, _ = Business.objects.update_or_create(
            slug='demo-dhaba',
            defaults={
                'name': 'Demo Dhaba',
                'phone': '+91 99999 99999',
                'email': 'demo@posdhaba.local',
                'address': 'Local Development',
                'is_active': True,
            },
        )

        License.objects.update_or_create(
            business=business,
            defaults={
                'key': 'DEV-DEMO-DHABA-2026',
                'starts_at': now - timedelta(days=1),
                'expires_at': now + timedelta(days=365),
                'is_active': True,
            },
        )

        admin, _ = User.objects.get_or_create(username='admin')
        admin.first_name = 'POS Admin'
        admin.email = 'admin@posdhaba.local'
        admin.role = User.Role.ADMIN
        admin.business = business
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        admin.set_password('admin123')
        admin.save()

        waiter, _ = User.objects.get_or_create(username='waiter')
        waiter.first_name = 'Demo Waiter'
        waiter.email = 'waiter@posdhaba.local'
        waiter.role = User.Role.WAITER
        waiter.business = business
        waiter.is_staff = False
        waiter.is_superuser = False
        waiter.is_active = True
        waiter.set_password('waiter123')
        waiter.save()

        menu = {
            'Starters': [
                ('Paneer Tikka', 'Grilled paneer with spices', 220),
                ('Chicken Tikka', 'Charcoal grilled chicken', 280),
            ],
            'Main Course': [
                ('Butter Chicken', 'Creamy tomato chicken curry', 320),
                ('Dal Tadka', 'Yellow lentils tempered with spices', 180),
                ('Shahi Paneer', 'Paneer in rich tomato gravy', 240),
            ],
            'Rice & Breads': [
                ('Veg Biryani', 'Aromatic basmati rice with vegetables', 220),
                ('Chicken Biryani', 'Basmati rice with chicken and spices', 280),
                ('Butter Roti', 'Tandoor roti with butter', 35),
                ('Garlic Naan', 'Soft naan with garlic and butter', 70),
            ],
            'Beverages': [
                ('Masala Chaas', 'Chilled spiced buttermilk', 60),
                ('Cold Drink', 'Assorted soft drink', 50),
                ('Mineral Water', 'Packaged drinking water', 30),
            ],
        }

        for category_name, items in menu.items():
            category, _ = Category.objects.update_or_create(
                business=business,
                name=category_name,
                defaults={'is_active': True},
            )
            for name, description, price in items:
                MenuItem.objects.update_or_create(
                    business=business,
                    name=name,
                    defaults={
                        'category': category,
                        'description': description,
                        'price': price,
                        'is_available': True,
                    },
                )

        for number in range(1, 11):
            Table.objects.update_or_create(
                business=business,
                number=number,
                defaults={
                    'name': f'Table {number}',
                    'capacity': 4 if number <= 8 else 6,
                    'is_active': True,
                },
            )

        self.stdout.write(self.style.SUCCESS('Demo POS data is ready.'))
        self.stdout.write('Admin : admin / admin123')
        self.stdout.write('Waiter: waiter / waiter123')
