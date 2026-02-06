from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from pathlib import Path
import os

from core.models import UserProfile, Donation
from core.services import EmailService, AnalyticsService


class Command(BaseCommand):
    help = 'Set up FoodLoop application with initial configuration and sample data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='Create a superuser account',
        )
        parser.add_argument(
            '--create-sample-data',
            action='store_true',
            help='Create sample users and donations for testing',
        )
        parser.add_argument(
            '--setup-directories',
            action='store_true',
            help='Create necessary directories (media, logs, etc.)',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Setting up FoodLoop application...')
        )
        
        # Setup directories
        if options['setup_directories']:
            self.setup_directories()
        
        # Create superuser
        if options['create_superuser']:
            self.create_superuser()
        
        # Create sample data
        if options['create_sample_data']:
            self.create_sample_data()
        
        # Final status
        self.stdout.write(
            self.style.SUCCESS('\n✅ FoodLoop setup completed successfully!')
        )
        self.stdout.write('📖 Next steps:')
        self.stdout.write('   1. Run: python manage.py runserver')
        self.stdout.write('   2. Visit: http://127.0.0.1:8000/')
        self.stdout.write('   3. API docs: http://127.0.0.1:8000/api/docs/')
    
    def setup_directories(self):
        """Create necessary directories"""
        from django.conf import settings
        
        directories = [
            settings.MEDIA_ROOT,
            settings.STATIC_ROOT,
            settings.BASE_DIR / 'logs',
            settings.MEDIA_ROOT / 'donations',
            settings.MEDIA_ROOT / 'profiles',
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.stdout.write(f' Created directory: {directory}')
    
    def create_superuser(self):
        """Create superuser if none exists"""
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING(' Superuser already exists, skipping...')
            )
            return
        
        username = input('Enter superuser username: ') or 'admin'
        email = input('Enter superuser email: ') or 'admin@foodloop.com'
        password = input('Enter superuser password: ') or 'admin123'
        
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'👤 Created superuser: {username}')
        )
    

    def create_sample_data(self):
        """Create sample users and donations for testing"""
        self.stdout.write(' Creating sample data...')
        
        # Sample donors
        sample_donors = [
            {
                'username': 'donor1',
                'email': 'donor1@example.com',
                'first_name': 'Jane',
                'last_name': 'Baker',
                'phone': '+254701234567',
                'address': 'Westlands, Nairobi'
            },
            {
                'username': 'donor2', 
                'email': 'donor2@example.com',
                'first_name': 'John',
                'last_name': 'Restaurant',
                'phone': '+254701234568',
                'address': 'CBD, Nairobi'
            }
        ]
        
        # Sample recipients
        sample_recipients = [
            {
                'username': 'recipient1',
                'email': 'recipient1@example.com',
                'first_name': 'Mary',
                'last_name': 'Community',
                'phone': '+254701234569',
                'address': 'Kibera, Nairobi',
                'dietary_restrictions': ['vegetarian'],
                'health_conditions': ['diabetes']
            },
            {
                'username': 'recipient2',
                'email': 'recipient2@example.com',
                'first_name': 'Peter',
                'last_name': 'Family',
                'phone': '+254701234570',
                'address': 'Mathare, Nairobi',
                'dietary_restrictions': [],
                'nutrition_goals': ['high_protein', 'low_sodium']
            }
        ]
        
        # Create donors
        for donor_data in sample_donors:
            user, created = User.objects.get_or_create(
                username=donor_data['username'],
                defaults={
                    'email': donor_data['email'],
                    'first_name': donor_data['first_name'],
                    'last_name': donor_data['last_name'],
                }
            )
            
            if created:
                user.set_password('test')  # Set password properly
                user.save()
                
                # FIXED: Removed latitude/longitude
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'user_type': UserProfile.DONOR,
                        'phone_number': donor_data['phone'],
                        'location': donor_data['address'],
                        'email_verified': True,
                    }
                )
                self.stdout.write(f' Created donor: {user.username}')
        
        # Create recipients
        for recipient_data in sample_recipients:
            user, created = User.objects.get_or_create(
                username=recipient_data['username'],
                defaults={
                    'email': recipient_data['email'],
                    'first_name': recipient_data['first_name'],
                    'last_name': recipient_data['last_name'],
                }
            )
            
            if created:
                user.set_password('test')  # Set password properly
                user.save()
                
                # FIXED: Removed latitude/longitude
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'user_type': UserProfile.RECIPIENT,
                        'phone_number': recipient_data['phone'],
                        'location': recipient_data['address'],
                        'dietary_restrictions': recipient_data.get('dietary_restrictions', []),
                        'email_verified': True,
                    }
                )
                self.stdout.write(f' Created recipient: {user.username}')
        
        # Create sample donations
        donors = User.objects.filter(profile__user_type=UserProfile.DONOR)
        if donors.exists():
            sample_donations = [
                {
                    'title': 'Fresh Vegetables Mix',
                    'description': 'Mixed vegetables including tomatoes, onions, and greens from our restaurant. Approximately 5 kg.',
                    'food_category': 'vegetables',
                    'quantity': '5 kg',
                    'estimated_calories': 800,
                    'dietary_tags': ['vegetarian', 'vegan'],
                    'pickup_location': 'Westlands Restaurant, Nairobi',
                },
                {
                    'title': 'Bread and Pastries',
                    'description': 'Day-old bread and pastries, still fresh and delicious. 20 loaves total.',
                    'food_category': 'grains',
                    'quantity': '20 loaves',
                    'estimated_calories': 1500,
                    'dietary_tags': ['vegetarian'],
                    'pickup_location': 'City Bakery, CBD Nairobi',
                }
            ]
            
            for i, donation_data in enumerate(sample_donations):
                donor = donors[i % donors.count()]
                
                # FIXED: Removed latitude/longitude from defaults
                donation, created = Donation.objects.get_or_create(
                    title=donation_data['title'],
                    donor=donor,
                    defaults={
                        'description': donation_data['description'],
                        'food_category': donation_data['food_category'],
                        'quantity': donation_data['quantity'],
                        'estimated_calories': donation_data['estimated_calories'],
                        'dietary_tags': donation_data['dietary_tags'],
                        'pickup_location': donation_data['pickup_location'],
                        'expiry_datetime': timezone.now() + timezone.timedelta(days=2),
                        'pickup_start': timezone.now() + timezone.timedelta(hours=2),
                        'pickup_end': timezone.now() + timezone.timedelta(days=1),
                        'status': Donation.AVAILABLE
                    }
                )
                
                if created:
                    # nutrition_score is now a dynamic property - no need to calculate
                    self.stdout.write(f' Created donation: {donation.title}')
        
        self.stdout.write(
            self.style.SUCCESS(' Sample data created successfully!')
        )
        self.stdout.write(
            ' Test login credentials:'
        )
        self.stdout.write('   Donor: donor1 / password: test')
        self.stdout.write('   Recipient: recipient1 / password: test')