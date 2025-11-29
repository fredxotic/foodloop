"""
Celery Tasks for FoodLoop

Background tasks for improved performance and user experience.
Includes email sending, notifications, analytics, and maintenance tasks.
All tasks use the service layer and proper error handling.
"""

from celery import shared_task
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg
from datetime import timedelta, datetime
from typing import List, Dict, Any
import logging

from .models import Donation, UserProfile, Notification, NutritionImpact
from .services import EmailService, NotificationService, AIService, DonationService
from .cache import CacheManager, CacheWarmupManager

logger = logging.getLogger(__name__)


# ============================================================================
# EMAIL TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3)
def send_email_task(self, recipient_email: str, subject: str, template_name: str, context: Dict):
    """
    Async email sending task with retry logic
    """
    try:
        from .utils import send_email_with_template
        
        success = send_email_with_template(
            recipient_email=recipient_email,
            subject=subject,
            template_name=template_name,
            context=context
        )
        
        if not success:
            raise Exception("Email sending failed")
        
        logger.info(f"Email sent successfully to {recipient_email}")
        return {'success': True, 'recipient': recipient_email}
        
    except Exception as e:
        logger.error(f"Email task error: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def send_bulk_notification_emails(notification_ids: List[int]):
    """
    Send bulk notification emails
    """
    try:
        notifications = Notification.objects.filter(
            id__in=notification_ids,
            is_read=False
        ).select_related('user')
        
        sent_count = 0
        for notification in notifications:
            try:
                send_email_task.delay(
                    recipient_email=notification.user.email,
                    subject=notification.title,
                    template_name='notification_email',
                    context={
                        'user': notification.user,
                        'notification': notification
                    }
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to queue email for notification {notification.id}: {e}")
        
        logger.info(f"Queued {sent_count} notification emails")
        return {'sent_count': sent_count}
        
    except Exception as e:
        logger.error(f"Bulk email task error: {e}")
        return {'error': str(e)}


# ============================================================================
# DONATION EXPIRY TASKS
# ============================================================================

@shared_task
def check_expiring_donations():
    """
    Check for expiring donations and send reminders
    Runs every hour
    """
    try:
        now = timezone.now()
        reminder_windows = [1, 6, 24]  # hours before expiry
        
        sent_count = 0
        
        for hours in reminder_windows:
            window_start = now + timedelta(hours=hours - 0.5)
            window_end = now + timedelta(hours=hours + 0.5)
            
            expiring_donations = Donation.objects.filter(
                status=Donation.AVAILABLE,
                expiry_datetime__gte=window_start,
                expiry_datetime__lte=window_end
            ).select_related('donor')
            
            for donation in expiring_donations:
                try:
                    EmailService.send_expiry_reminder_email(donation, hours)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send expiry reminder for donation {donation.id}: {e}")
        
        logger.info(f"Sent {sent_count} expiry reminder emails")
        return {'sent_count': sent_count}
        
    except Exception as e:
        logger.error(f"Check expiring donations error: {e}")
        return {'error': str(e)}


@shared_task
def mark_expired_donations():
    """
    Mark donations as expired
    Runs every 30 minutes
    """
    try:
        now = timezone.now()
        
        expired = Donation.objects.filter(
            status=Donation.AVAILABLE,
            expiry_datetime__lt=now
        ).update(status=Donation.EXPIRED)
        
        logger.info(f"Marked {expired} donations as expired")
        
        # Invalidate relevant caches
        if expired > 0:
            CacheWarmupManager.warmup_popular_donations()
        
        return {'expired_count': expired}
        
    except Exception as e:
        logger.error(f"Mark expired donations error: {e}")
        return {'error': str(e)}


# ============================================================================
# NOTIFICATION CLEANUP TASKS
# ============================================================================

@shared_task
def cleanup_old_notifications():
    """
    Clean up old read notifications
    Runs daily
    """
    try:
        cleaned = NotificationService.cleanup_old_notifications(days=30)
        logger.info(f"Cleaned up {cleaned} old notifications")
        return {'cleaned_count': cleaned}
        
    except Exception as e:
        logger.error(f"Notification cleanup error: {e}")
        return {'error': str(e)}


# ============================================================================
# CACHE WARMUP TASKS
# ============================================================================

@shared_task
def warmup_popular_caches():
    """
    Warmup caches for popular data
    Runs every 30 minutes during peak hours
    """
    try:
        # Warmup popular donations
        CacheWarmupManager.warmup_popular_donations(limit=30)
        
        # Warmup platform overview
        from .services import AnalyticsService
        AnalyticsService.get_platform_overview()
        
        logger.info("Cache warmup completed successfully")
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Cache warmup error: {e}")
        return {'error': str(e)}


@shared_task
def warmup_user_cache(user_id: int):
    """
    Warmup cache for specific user
    Called when user logs in
    """
    try:
        success = CacheWarmupManager.warmup_user_data(user_id)
        return {'success': success, 'user_id': user_id}
        
    except Exception as e:
        logger.error(f"User cache warmup error: {e}")
        return {'error': str(e)}


# ============================================================================
# ANALYTICS TASKS
# ============================================================================

@shared_task
def update_daily_analytics():
    """
    Update daily analytics and nutrition impact
    Runs at midnight
    """
    try:
        yesterday = timezone.now().date() - timedelta(days=1)
        
        # Get all users with completed donations yesterday
        users_with_activity = set()
        
        # Donors
        donors = Donation.objects.filter(
            completed_at__date=yesterday
        ).values_list('donor_id', flat=True).distinct()
        users_with_activity.update(donors)
        
        # Recipients
        recipients = Donation.objects.filter(
            completed_at__date=yesterday
        ).values_list('recipient_id', flat=True).distinct()
        users_with_activity.update(recipients)
        
        # Update nutrition impact for each user
        for user_id in users_with_activity:
            try:
                user = User.objects.get(id=user_id)
                
                # Calculate stats for yesterday
                donor_stats = Donation.objects.filter(
                    donor=user,
                    completed_at__date=yesterday
                ).aggregate(
                    count=Count('id'),
                    calories=Avg('estimated_calories'),
                    nutrition=Avg('nutrition_score')
                )
                
                recipient_stats = Donation.objects.filter(
                    recipient=user,
                    completed_at__date=yesterday
                ).aggregate(
                    count=Count('id'),
                    calories=Avg('estimated_calories'),
                    nutrition=Avg('nutrition_score')
                )
                
                # Update or create impact record
                NutritionImpact.objects.update_or_create(
                    user=user,
                    date=yesterday,
                    defaults={
                        'donations_made': donor_stats['count'] or 0,
                        'donations_received': recipient_stats['count'] or 0,
                        'total_calories': (donor_stats['calories'] or 0) + (recipient_stats['calories'] or 0),
                        'avg_nutrition_score': (
                            (donor_stats['nutrition'] or 0) + (recipient_stats['nutrition'] or 0)
                        ) / 2 if donor_stats['nutrition'] or recipient_stats['nutrition'] else 0
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to update analytics for user {user_id}: {e}")
        
        logger.info(f"Updated daily analytics for {len(users_with_activity)} users")
        return {'users_updated': len(users_with_activity)}
        
    except Exception as e:
        logger.error(f"Daily analytics update error: {e}")
        return {'error': str(e)}


# ============================================================================
# RECOMMENDATION UPDATE TASKS
# ============================================================================

@shared_task
def refresh_user_recommendations(user_id: int):
    """
    Refresh recommendations for a specific user
    Called after profile updates or new donations
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Invalidate old recommendations
        CacheManager.invalidate_recommendations(user_id)
        
        # Generate new recommendations
        AIService.get_personalized_recommendations(user, limit=10)
        
        logger.info(f"Refreshed recommendations for user {user_id}")
        return {'success': True, 'user_id': user_id}
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'error': 'User not found'}
    except Exception as e:
        logger.error(f"Refresh recommendations error: {e}")
        return {'error': str(e)}


@shared_task
def batch_refresh_recommendations():
    """
    Refresh recommendations for all active recipients
    Runs every 6 hours
    """
    try:
        # Get active recipients
        recipients = UserProfile.objects.filter(
            user_type=UserProfile.RECIPIENT,
            email_verified=True,
            last_active__gte=timezone.now() - timedelta(days=7)
        ).values_list('user_id', flat=True)[:100]  # Limit to prevent overload
        
        refreshed = 0
        for user_id in recipients:
            try:
                refresh_user_recommendations.delay(user_id)
                refreshed += 1
            except Exception as e:
                logger.error(f"Failed to queue recommendation refresh for user {user_id}: {e}")
        
        logger.info(f"Queued recommendation refresh for {refreshed} users")
        return {'queued_count': refreshed}
        
    except Exception as e:
        logger.error(f"Batch refresh recommendations error: {e}")
        return {'error': str(e)}


# ============================================================================
# SYSTEM MAINTENANCE TASKS
# ============================================================================

@shared_task
def cleanup_old_verifications():
    """
    Clean up old email verifications
    Runs daily
    """
    try:
        from .models import EmailVerification
        
        cutoff = timezone.now() - timedelta(days=7)
        deleted, _ = EmailVerification.objects.filter(
            created_at__lt=cutoff,
            is_verified=False
        ).delete()
        
        logger.info(f"Deleted {deleted} old verification tokens")
        return {'deleted_count': deleted}
        
    except Exception as e:
        logger.error(f"Cleanup verifications error: {e}")
        return {'error': str(e)}


@shared_task
def generate_system_health_report():
    """
    Generate and log system health report
    Runs every hour
    """
    try:
        from .services import AnalyticsService
        
        health_report = AnalyticsService.generate_system_health_report()
        
        logger.info(f"System Health: {health_report['status']} (Score: {health_report.get('overall_health_score', 'N/A')})")
        
        # Alert if unhealthy
        if health_report.get('status') == 'unhealthy':
            logger.critical(f"SYSTEM UNHEALTHY: {health_report}")
        
        return health_report
        
    except Exception as e:
        logger.error(f"Health report error: {e}")
        return {'error': str(e)}