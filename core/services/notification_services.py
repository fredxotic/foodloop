"""
Optimized Notification Service - Efficient and scalable
"""
from django.utils import timezone
from django.urls import reverse
from django.db import transaction
from typing import Optional, List
from datetime import timedelta
import random
import logging

from core.models import Notification, UserProfile, Donation
from core.services.base import BaseService, ServiceResponse
from core.cache import CacheManager
from core.utils import send_realtime_notification

logger = logging.getLogger(__name__)


class NotificationService(BaseService):
    """
    High-performance notification management with caching
    """
    
    MAX_NOTIFICATIONS_PER_USER = 50
    CLEANUP_THRESHOLD_DAYS = 30

    @classmethod
    def create_notification(
        cls, 
        user, 
        notification_type: str, 
        title: str, 
        message: str,
        related_donation: Optional[Donation] = None,
        related_url: Optional[str] = None
    ) -> Optional[Notification]:
        """
        Create notification with automatic cleanup and cache invalidation
        """
        try:
            # Use utility function for unified notification creation
            notification = send_realtime_notification(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                related_url=related_url,
                related_donation=related_donation
            )
            
            # Probabilistic cleanup (5% chance) to prevent performance hit
            if random.random() < 0.05:
                cls._schedule_cleanup(user)
            
            # Invalidate notification count cache
            CacheManager.invalidate_notification_count(user.id)
            
            return notification
            
        except Exception as e:
            logger.error(f"Notification creation error: {e}")
            return None

    @classmethod
    def notify_donation_claimed(cls, donation: Donation, recipient) -> bool:
        """Send notifications when a donation is claimed"""
        try:
            # Notify donor
            cls.create_notification(
                user=donation.donor,
                notification_type=Notification.DONATION_CLAIMED,
                title="Donation Claimed! 🎉",
                message=f"{recipient.get_full_name()} has claimed your '{donation.title}' donation.",
                related_donation=donation,
                related_url=reverse('core:donation_detail', args=[donation.id])
            )
            
            # Notify recipient
            cls.create_notification(
                user=recipient,
                notification_type=Notification.DONATION_CLAIMED,
                title="Donation Claimed Successfully",
                message=f"You've claimed '{donation.title}'. Pickup by {donation.pickup_end.strftime('%b %d, %I:%M %p')}.",
                related_donation=donation,
                related_url=reverse('core:donation_detail', args=[donation.id])
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Claim notification error: {e}")
            return False

    @classmethod
    def notify_donation_completed(cls, donation: Donation) -> bool:
        """Send notifications when a donation is completed"""
        try:
            # Notify donor
            cls.create_notification(
                user=donation.donor,
                notification_type=Notification.DONATION_COMPLETED,
                title="Donation Completed! ✅",
                message=f"Your '{donation.title}' donation was successfully picked up by {donation.recipient.get_full_name()}.",
                related_donation=donation,
                related_url=reverse('core:rate_user', args=[donation.id])
            )
            
            # Notify recipient
            cls.create_notification(
                user=donation.recipient,
                notification_type=Notification.DONATION_COMPLETED,
                title="Thank You!",
                message=f"Thank you for picking up '{donation.title}'. Please rate your experience.",
                related_donation=donation,
                related_url=reverse('core:rate_user', args=[donation.id])
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Completion notification error: {e}")
            return False

    @classmethod
    def notify_donation_cancelled(cls, donation: Donation, recipient) -> bool:
        """Send notifications when a donation is cancelled"""
        try:
            # Notify recipient
            cls.create_notification(
                user=recipient,
                notification_type=Notification.SYSTEM,
                title="Donation Cancelled",
                message=f"The donation '{donation.title}' has been cancelled by the donor.",
                related_donation=donation,
                related_url=reverse('core:donation_detail', args=[donation.id])
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Cancellation notification error: {e}")
            return False

    @classmethod
    def notify_new_donation(cls, donation: Donation) -> int:
        """
        Notify relevant recipients about new donation
        Returns count of notifications sent
        """
        try:
            # Find compatible recipients near the donation
            recipients = cls._find_compatible_recipients(donation)
            
            notification_count = 0
            for recipient in recipients[:10]:  # Limit to 10 most relevant
                try:
                    cls.create_notification(
                        user=recipient.user,
                        notification_type=Notification.NEW_DONATION,
                        title="New Donation Available! 🍽️",
                        message=f"New {donation.food_category} donation: '{donation.title}' near you.",
                        related_donation=donation,
                        related_url=reverse('core:donation_detail', args=[donation.id])
                    )
                    notification_count += 1
                except Exception as e:
                    logger.warning(f"Failed to notify recipient {recipient.user.id}: {e}")
                    continue
            
            logger.info(f"Sent {notification_count} new donation notifications")
            return notification_count
            
        except Exception as e:
            logger.error(f"New donation notification error: {e}")
            return 0

    @classmethod
    def _find_compatible_recipients(cls, donation: Donation, max_results: int = 10) -> List[UserProfile]:
        """Find recipients compatible with donation (Iterates efficiently)"""
        try:
            # Base query for verified recipients
            # Use iterator to avoid loading all users into memory
            recipient_qs = UserProfile.objects.filter(
                user_type=UserProfile.RECIPIENT,
                email_verified=True
            ).select_related('user').order_by('-user__last_login')
            
            compatible = []
            # Iterate through DB cursor in chunks
            for recipient in recipient_qs.iterator(chunk_size=100):
                if recipient.is_dietary_compatible(donation):
                    compatible.append(recipient)
                    if len(compatible) >= max_results:
                        break
            
            return compatible
            
        except Exception as e:
            logger.error(f"Recipient search error: {e}")
            return []

    @classmethod
    def notify_rating_received(cls, rating) -> bool:
        """Send notification when user receives a rating"""
        try:
            rated_user = rating.rated_user
            rating_user = rating.rating_user
            
            # Determine message based on rating score
            if rating.rating >= 4:
                emoji = "⭐"
                tone = "Great"
            elif rating.rating >= 3:
                emoji = "👍"
                tone = "Good"
            else:
                emoji = "📝"
                tone = "Feedback"
            
            cls.create_notification(
                user=rated_user,
                notification_type=Notification.RATING_RECEIVED,
                title=f"New {tone} Rating {emoji}",
                message=f"{rating_user.get_full_name()} rated you {rating.rating}/5 stars.",
                related_url=reverse('core:profile')
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Rating notification error: {e}")
            return False

    @classmethod
    def get_user_notifications(
        cls, 
        user, 
        limit: int = 20, 
        unread_only: bool = False
    ) -> List[Notification]:
        """
        Get notifications with efficient query
        """
        try:
            queryset = Notification.objects.filter(
                user=user
            ).select_related(
                'related_donation',
                'related_donation__donor'
            ).order_by('-created_at')
            
            if unread_only:
                queryset = queryset.filter(is_read=False)
            
            return list(queryset[:limit])
            
        except Exception as e:
            logger.error(f"Get notifications error: {e}")
            return []

    @classmethod
    def get_unread_count(cls, user) -> int:
        """Get count of unread notifications with caching"""
        try:
            # Try cache first
            cached_count = CacheManager.get_notification_count(user.id)
            if cached_count is not None:
                return cached_count
            
            # Query database
            count = Notification.objects.filter(
                user=user, 
                is_read=False
            ).count()
            
            # Cache the result
            CacheManager.set_notification_count(user.id, count)
            
            return count
            
        except Exception as e:
            logger.error(f"Unread count error: {e}")
            return 0

    @classmethod
    def mark_notification_read(cls, notification_id: int, user) -> ServiceResponse:
        """Mark a specific notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            
            if not notification.is_read:
                notification.is_read = True
                notification.read_at = timezone.now()
                notification.save(update_fields=['is_read', 'read_at'])
                
                # Invalidate cache
                CacheManager.invalidate_notification_count(user.id)
            
            return cls.success(message="Notification marked as read")
            
        except Notification.DoesNotExist:
            return cls.error("Notification not found")
        except Exception as e:
            return cls.handle_exception(e, "mark notification read")

    @classmethod
    def mark_all_read(cls, user) -> ServiceResponse:
        """Mark all notifications as read for user"""
        try:
            count = Notification.objects.filter(
                user=user, 
                is_read=False
            ).update(
                is_read=True, 
                read_at=timezone.now()
            )
            
            # Invalidate cache
            CacheManager.invalidate_notification_count(user.id)
            
            return cls.success(
                data={'count': count},
                message=f"Marked {count} notifications as read"
            )
            
        except Exception as e:
            return cls.handle_exception(e, "mark all read")

    @classmethod
    def _schedule_cleanup(cls, user):
        """Schedule cleanup of old notifications"""
        try:
            count = Notification.objects.filter(user=user).count()
            
            if count > cls.MAX_NOTIFICATIONS_PER_USER:
                # Keep most recent, delete oldest
                notifications = Notification.objects.filter(
                    user=user
                ).order_by('-created_at')
                
                keep_ids = list(notifications[:cls.MAX_NOTIFICATIONS_PER_USER].values_list('id', flat=True))
                
                Notification.objects.filter(
                    user=user
                ).exclude(
                    id__in=keep_ids
                ).delete()
                
                logger.info(f"Cleaned up old notifications for user {user.id}")
                
        except Exception as e:
            logger.error(f"Notification cleanup error: {e}")

    @classmethod
    def cleanup_old_notifications(cls, days: int = None) -> int:
        """
        Cleanup read notifications older than specified days
        Can be called as a scheduled task
        """
        try:
            days = days or cls.CLEANUP_THRESHOLD_DAYS
            cutoff_date = timezone.now() - timedelta(days=days)
            
            deleted_count, _ = Notification.objects.filter(
                is_read=True,
                created_at__lt=cutoff_date
            ).delete()
            
            logger.info(f"Cleaned up {deleted_count} old notifications")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Bulk cleanup error: {e}")
            return 0