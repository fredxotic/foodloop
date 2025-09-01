# core/management/commands/seed_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile, Donation
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Seeds the database with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding data...')
        
        # Create sample users if they don't exist
        donor1, created = User.objects.get_or_create(
            username='donor1',
            defaults={
                'email': 'donor1@example.com',
                'first_name': 'John',
                'last_name': 'Smith'
            }
        )
        if created:
            donor1.set_password('password123')
            donor1.save()
            self.stdout.write(f'Created user: {donor1.username}')
        else:
            self.stdout.write(f'User already exists: {donor1.username}')
        
        # Get or create user profile for donor1
        donor1_profile, profile_created = UserProfile.objects.get_or_create(
            user=donor1,
            defaults={
                'user_type': 'donor',
                'phone_number': '555-0101'
            }
        )
        if profile_created:
            self.stdout.write(f'Created profile for: {donor1.username}')
        else:
            # Update existing profile if needed
            if donor1_profile.user_type != 'donor':
                donor1_profile.user_type = 'donor'
                donor1_profile.save()
                self.stdout.write(f'Updated profile for: {donor1.username}')
        
        donor2, created = User.objects.get_or_create(
            username='donor2',
            defaults={
                'email': 'donor2@example.com',
                'first_name': 'Sarah',
                'last_name': 'Johnson'
            }
        )
        if created:
            donor2.set_password('password123')
            donor2.save()
            self.stdout.write(f'Created user: {donor2.username}')
        else:
            self.stdout.write(f'User already exists: {donor2.username}')
        
        # Get or create user profile for donor2
        donor2_profile, profile_created = UserProfile.objects.get_or_create(
            user=donor2,
            defaults={
                'user_type': 'donor',
                'phone_number': '555-0102'
            }
        )
        if profile_created:
            self.stdout.write(f'Created profile for: {donor2.username}')
        
        recipient1, created = User.objects.get_or_create(
            username='recipient1',
            defaults={
                'email': 'recipient1@example.com',
                'first_name': 'Community',
                'last_name': 'Kitchen'
            }
        )
        if created:
            recipient1.set_password('password123')
            recipient1.save()
            self.stdout.write(f'Created user: {recipient1.username}')
        else:
            self.stdout.write(f'User already exists: {recipient1.username}')
        
        # Get or create user profile for recipient1
        recipient1_profile, profile_created = UserProfile.objects.get_or_create(
            user=recipient1,
            defaults={
                'user_type': 'recipient',
                'phone_number': '555-0201'
            }
        )
        if profile_created:
            self.stdout.write(f'Created profile for: {recipient1.username}')
        
        recipient2, created = User.objects.get_or_create(
            username='recipient2',
            defaults={
                'email': 'recipient2@example.com',
                'first_name': 'Food',
                'last_name': 'Pantry'
            }
        )
        if created:
            recipient2.set_password('password123')
            recipient2.save()
            self.stdout.write(f'Created user: {recipient2.username}')
        else:
            self.stdout.write(f'User already exists: {recipient2.username}')
        
        # Get or create user profile for recipient2
        recipient2_profile, profile_created = UserProfile.objects.get_or_create(
            user=recipient2,
            defaults={
                'user_type': 'recipient',
                'phone_number': '555-0202'
            }
        )
        if profile_created:
            self.stdout.write(f'Created profile for: {recipient2.username}')
        
        # Delete existing donations to avoid duplicates
        Donation.objects.all().delete()
        self.stdout.write('Cleared existing donations')
        
        # Create sample donations
        donations_data = [
            {
                'donor': donor1,
                'food_type': 'vegetables',
                'quantity': '5 kg',
                'description': 'Fresh organic vegetables from local farm - tomatoes, cucumbers, bell peppers',
                'pickup_time': datetime.now() + timedelta(hours=2),
                'location': '123 Main St, City Center',
                'status': 'available'
            },
            {
                'donor': donor1,
                'food_type': 'bakery',
                'quantity': '10 loaves',
                'description': 'Day-old bread from bakery - assorted types',
                'pickup_time': datetime.now() + timedelta(hours=5),
                'location': '456 Oak Ave, Downtown',
                'status': 'available'
            },
            {
                'donor': donor2,
                'food_type': 'fruits',
                'quantity': '8 kg',
                'description': 'Assorted fruits - apples, oranges, bananas',
                'pickup_time': datetime.now() + timedelta(days=1),
                'location': '789 Pine Rd, Westside',
                'status': 'available'
            },
            {
                'donor': donor2,
                'food_type': 'dairy',
                'quantity': '3 boxes',
                'description': 'Milk, cheese, and yogurt - all within expiration date',
                'pickup_time': datetime.now() + timedelta(hours=3),
                'location': '321 Elm St, Eastside',
                'status': 'claimed',
                'recipient': recipient1
            },
            {
                'donor': donor1,
                'food_type': 'cooked',
                'quantity': '15 meals',
                'description': 'Prepared meals from restaurant - vegetarian options available',
                'pickup_time': datetime.now() + timedelta(hours=4),
                'location': '555 Restaurant Row, Food District',
                'status': 'available'
            },
            {
                'donor': donor2,
                'food_type': 'other',
                'quantity': 'Various',
                'description': 'Non-perishable food items - canned goods, pasta, rice',
                'pickup_time': datetime.now() + timedelta(days=2),
                'location': '888 Market St, Shopping Area',
                'status': 'available'
            }
        ]
        
        for donation_data in donations_data:
            donation = Donation.objects.create(
                donor=donation_data['donor'],
                food_type=donation_data['food_type'],
                quantity=donation_data['quantity'],
                description=donation_data['description'],
                pickup_time=donation_data['pickup_time'],
                location=donation_data['location'],
                status=donation_data['status'],
                recipient=donation_data.get('recipient', None)
            )
            self.stdout.write(f'Created donation: {donation.food_type} from {donation.donor.username}')
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded data!'))