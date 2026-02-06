"""
Management command to cleanup stale claimed donations
Usage: python manage.py cleanup_stale_claims
"""
from django.core.management.base import BaseCommand
from core.services.donation_services import DonationService


class Command(BaseCommand):
    help = 'Cleanup stale claimed donations where pickup window has passed'

    def handle(self, *args, **options):
        self.stdout.write('Starting stale claim cleanup...')
        
        result = DonationService.cleanup_stale_claims()
        
        if result.success:
            count = result.data.get('count', 0)
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Successfully cleaned up {count} stale claim(s)'
                )
            )
            
            if count > 0:
                self.stdout.write('\nReverted donations:')
                for donation in result.data.get('donations', []):
                    self.stdout.write(
                        f'  - {donation.title} (ID: {donation.id})'
                    )
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ Cleanup failed: {result.message}')
            )
