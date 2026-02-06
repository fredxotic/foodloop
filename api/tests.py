"""
API Security Tests
==================

Test suite for API permissions and viewset security enhancements.
Run with: python manage.py test api.tests -v 2
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Donation, UserProfile
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class DonationPermissionTests(TestCase):
    """Test donation permissions and ownership validation"""
    
    def setUp(self):
        """Create test users and donations"""
        # Create donor 1
        self.donor1 = User.objects.create_user(
            username='donor1',
            email='donor1@test.com',
            password='testpass123'
        )
        self.donor1_profile = UserProfile.objects.create(
            user=self.donor1,
            user_type=UserProfile.DONOR,
            email_verified=True
        )
        
        # Create donor 2
        self.donor2 = User.objects.create_user(
            username='donor2',
            email='donor2@test.com',
            password='testpass123'
        )
        self.donor2_profile = UserProfile.objects.create(
            user=self.donor2,
            user_type=UserProfile.DONOR,
            email_verified=True
        )
        
        # Create recipient
        self.recipient = User.objects.create_user(
            username='recipient1',
            email='recipient@test.com',
            password='testpass123'
        )
        self.recipient_profile = UserProfile.objects.create(
            user=self.recipient,
            user_type=UserProfile.RECIPIENT,
            email_verified=True
        )
        
        # Create donation by donor1
        self.donation = Donation.objects.create(
            donor=self.donor1,
            title='Test Donation',
            food_category='fruits',
            description='Fresh apples',
            quantity='5kg',
            expiry_datetime=timezone.now() + timedelta(days=2),
            pickup_start=timezone.now(),
            pickup_end=timezone.now() + timedelta(hours=4),
            pickup_location='Test Location',
            status=Donation.AVAILABLE
        )
        
        self.client = APIClient()
    
    def test_owner_can_update_donation(self):
        """Test that donation owner can update their donation"""
        self.client.force_authenticate(user=self.donor1)
        
        update_data = {
            'title': 'Updated Donation',
            'food_category': 'fruits',
            'description': 'Updated description',
            'quantity': '10kg',
            'expiry_datetime': (timezone.now() + timedelta(days=2)).isoformat(),
            'pickup_start': timezone.now().isoformat(),
            'pickup_end': (timezone.now() + timedelta(hours=4)).isoformat(),
            'pickup_location': 'Updated Location'
        }
        
        response = self.client.put(
            f'/api/v1/donations/{self.donation.id}/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Donation')
    
    def test_non_owner_cannot_update_donation(self):
        """Test that non-owner cannot update someone else's donation"""
        self.client.force_authenticate(user=self.donor2)
        
        update_data = {
            'title': 'Malicious Update',
            'description': 'Hacked'
        }
        
        response = self.client.patch(
            f'/api/v1/donations/{self.donation.id}/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # DRF returns 'detail' key on permission errors
        self.assertIn('detail', response.data)
    
    def test_recipient_cannot_update_donation(self):
        """Test that recipients cannot update donations"""
        self.client.force_authenticate(user=self.recipient)
        
        update_data = {
            'title': 'Recipient Update Attempt'
        }
        
        response = self.client.patch(
            f'/api/v1/donations/{self.donation.id}/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_owner_can_delete_donation(self):
        """Test that donation owner can delete (cancel) their donation"""
        self.client.force_authenticate(user=self.donor1)
        
        response = self.client.delete(f'/api/v1/donations/{self.donation.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify donation was cancelled, not deleted
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.status, Donation.CANCELLED)
    
    def test_non_owner_cannot_delete_donation(self):
        """Test that non-owner cannot delete someone else's donation"""
        self.client.force_authenticate(user=self.donor2)
        
        response = self.client.delete(f'/api/v1/donations/{self.donation.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # DRF returns 'detail' key on permission errors
        self.assertIn('detail', response.data)
        
        # Verify donation still exists
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.status, Donation.AVAILABLE)
    
    def test_cannot_update_completed_donation(self):
        """Test that completed donations cannot be updated"""
        # Mark as completed
        self.donation.status = Donation.COMPLETED
        self.donation.save()
        
        self.client.force_authenticate(user=self.donor1)
        
        update_data = {'title': 'Update After Completion'}
        
        response = self.client.patch(
            f'/api/v1/donations/{self.donation.id}/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot update', response.data['error'])
    
    def test_unauthenticated_cannot_update(self):
        """Test that unauthenticated users cannot update donations"""
        update_data = {'title': 'Anonymous Update'}
        
        response = self.client.patch(
            f'/api/v1/donations/{self.donation.id}/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserPermissionTests(TestCase):
    """Test user permissions and ownership validation"""
    
    def setUp(self):
        """Create test users"""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        UserProfile.objects.create(
            user=self.user1,
            user_type=UserProfile.DONOR,
            email_verified=True
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
        UserProfile.objects.create(
            user=self.user2,
            user_type=UserProfile.RECIPIENT,
            email_verified=True
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='testpass123',
            is_staff=True
        )
        
        self.client = APIClient()
    
    def test_user_can_update_own_profile(self):
        """Test that users can update their own profile"""
        self.client.force_authenticate(user=self.user1)
        
        update_data = {
            'email': 'newemail@test.com',
            'first_name': 'Updated'
        }
        
        response = self.client.patch(
            f'/api/v1/users/{self.user1.id}/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_user_cannot_update_other_user(self):
        """Test that users cannot update other users' profiles"""
        self.client.force_authenticate(user=self.user1)
        
        update_data = {
            'email': 'hacked@test.com'
        }
        
        response = self.client.patch(
            f'/api/v1/users/{self.user2.id}/',
            update_data,
            format='json'
        )
        
        # Should get 404 because user can't even see other users
        # or 403 if they somehow bypass queryset filtering
        self.assertIn(
            response.status_code, 
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        )
    
    def test_staff_can_update_any_user(self):
        """Test that staff can update any user"""
        self.client.force_authenticate(user=self.staff_user)
        
        update_data = {
            'first_name': 'Admin Updated'
        }
        
        response = self.client.patch(
            f'/api/v1/users/{self.user1.id}/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_user_cannot_delete_themselves(self):
        """Test that users cannot delete their own account"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.delete(f'/api/v1/users/{self.user1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cannot delete your own account', response.data['error'])
    
    def test_staff_can_delete_users(self):
        """Test that staff can delete users"""
        self.client.force_authenticate(user=self.staff_user)
        
        response = self.client.delete(f'/api/v1/users/{self.user2.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify user was deleted
        self.assertFalse(User.objects.filter(id=self.user2.id).exists())


class PermissionClassTests(TestCase):
    """Test custom permission classes directly"""
    
    def setUp(self):
        """Create test data"""
        from django.test import RequestFactory
        from api.permissions import IsDonorOrReadOnly, IsOwnerOrReadOnly
        
        self.factory = RequestFactory()
        self.donor_permission = IsDonorOrReadOnly()
        self.owner_permission = IsOwnerOrReadOnly()
        
        # Create users
        self.donor = User.objects.create_user('donor', 'donor@test.com', 'pass')
        self.donor_profile = UserProfile.objects.create(
            user=self.donor,
            user_type=UserProfile.DONOR
        )
        
        self.recipient = User.objects.create_user('recipient', 'recipient@test.com', 'pass')
        self.recipient_profile = UserProfile.objects.create(
            user=self.recipient,
            user_type=UserProfile.RECIPIENT
        )
    
    def test_is_donor_or_readonly_allows_donor_write(self):
        """Test IsDonorOrReadOnly allows donors to write"""
        request = self.factory.post('/api/donations/')
        request.user = self.donor
        
        has_permission = self.donor_permission.has_permission(request, None)
        self.assertTrue(has_permission)
    
    def test_is_donor_or_readonly_denies_recipient_write(self):
        """Test IsDonorOrReadOnly denies recipients write access"""
        request = self.factory.post('/api/donations/')
        request.user = self.recipient
        
        has_permission = self.donor_permission.has_permission(request, None)
        self.assertFalse(has_permission)
    
    def test_object_permission_allows_owner_put(self):
        """Test object permission allows owner to PUT"""
        donation = Donation(donor=self.donor)
        
        request = self.factory.put(f'/api/donations/1/')
        request.user = self.donor
        
        has_permission = self.donor_permission.has_object_permission(
            request, None, donation
        )
        self.assertTrue(has_permission)
    
    def test_object_permission_denies_non_owner_put(self):
        """Test object permission denies non-owner PUT"""
        other_donor = User.objects.create_user('other', 'other@test.com', 'pass')
        donation = Donation(donor=self.donor)
        
        request = self.factory.put(f'/api/donations/1/')
        request.user = other_donor
        
        has_permission = self.donor_permission.has_object_permission(
            request, None, donation
        )
        self.assertFalse(has_permission)
