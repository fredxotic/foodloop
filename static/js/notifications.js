// static/js/notifications.js - Fully functional version
class NotificationManager {
    constructor() {
        this.userId = null;
        this.pollingInterval = null;
        this.initialize();
    }
    
    initialize() {
        this.userId = document.querySelector('meta[name="user-id"]')?.content;
        
        if (!this.userId) {
            console.log('No user ID found for notifications');
            return;
        }
        
        this.loadNotificationCount();
        this.setupEventListeners();
        this.startPolling();
        
        // Load notifications when dropdown is opened
        this.setupDropdownListener();
    }
    
    async loadNotificationCount() {
        try {
            const response = await fetch('/notifications/count/');
            if (response.ok) {
                const data = await response.json();
                this.updateNotificationBadge(data.count);
            }
        } catch (error) {
            console.error('Error loading notification count:', error);
        }
    }
    
    async loadNotifications() {
        try {
            const response = await fetch('/notifications/');
            if (response.ok) {
                const data = await response.json();
                if (data.notifications) {
                    this.renderNotifications(data.notifications);
                } else {
                    this.renderEmptyNotifications();
                }
            } else {
                this.renderError();
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
            this.renderError();
        }
    }
    
    updateNotificationBadge(count) {
        const badge = document.getElementById('notificationBadge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'block';
                
                // Add pulse animation for new notifications
                badge.classList.add('pulse');
                setTimeout(() => badge.classList.remove('pulse'), 2000);
            } else {
                badge.style.display = 'none';
            }
        }
    }
    
    renderNotifications(notifications) {
        const container = document.getElementById('notificationList');
        if (!container) return;
        
        if (notifications.length === 0) {
            this.renderEmptyNotifications();
            return;
        }
        
        container.innerHTML = notifications.map(notification => `
            <div class="notification-item ${notification.is_read ? '' : 'unread'} p-3 border-bottom" 
                 data-notification-id="${notification.id}">
                <div class="d-flex align-items-start">
                    <div class="notification-icon bg-${this.getNotificationColor(notification.type)} text-white rounded-circle d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;">
                        <i class="fas fa-${this.getNotificationIcon(notification.type)}"></i>
                    </div>
                    <div class="flex-grow-1 ms-3">
                        <div class="d-flex justify-content-between align-items-start mb-1">
                            <strong class="me-2">${this.escapeHtml(notification.title)}</strong>
                            <small class="text-muted">${notification.time_ago}</small>
                        </div>
                        <p class="mb-1 small">${this.escapeHtml(notification.message)}</p>
                        ${notification.related_url ? `
                            <a href="${notification.related_url}" class="btn btn-sm btn-outline-primary mt-1" onclick="window.notificationManager.markAsRead(${notification.id})">
                                View Details
                            </a>
                        ` : ''}
                        <div class="mt-2">
                            <small>
                                <a href="#" class="text-muted me-3" onclick="window.notificationManager.markAsRead(${notification.id}); return false;">
                                    <i class="fas fa-check me-1"></i>Mark as read
                                </a>
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        // Add click handlers for notification items
        this.setupNotificationClickHandlers();
    }
    
    renderEmptyNotifications() {
        const container = document.getElementById('notificationList');
        if (container) {
            container.innerHTML = `
                <div class="text-center p-4 text-muted">
                    <i class="fas fa-bell-slash fa-2x mb-2"></i>
                    <p class="mb-0">No new notifications</p>
                    <small class="text-muted">We'll notify you when something happens</small>
                </div>
            `;
        }
    }
    
    renderError() {
        const container = document.getElementById('notificationList');
        if (container) {
            container.innerHTML = `
                <div class="text-center p-4 text-muted">
                    <i class="fas fa-exclamation-triangle fa-2x mb-2 text-warning"></i>
                    <p class="mb-0">Unable to load notifications</p>
                    <small class="text-muted">Please try again later</small>
                </div>
            `;
        }
    }
    
    setupNotificationClickHandlers() {
        const notificationItems = document.querySelectorAll('.notification-item');
        notificationItems.forEach(item => {
            item.addEventListener('click', (e) => {
                // Don't trigger if clicking on links or buttons
                if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON') {
                    return;
                }
                
                const notificationId = item.getAttribute('data-notification-id');
                const link = item.querySelector('a.btn');
                
                if (link) {
                    this.markAsRead(notificationId);
                    window.location.href = link.href;
                }
            });
        });
    }
    
    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/notifications/${notificationId}/read/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                // Update UI
                const notificationItem = document.querySelector(`[data-notification-id="${notificationId}"]`);
                if (notificationItem) {
                    notificationItem.classList.remove('unread');
                }
                
                // Update badge count
                this.loadNotificationCount();
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }
    
    async markAllAsRead() {
        try {
            const response = await fetch('/notifications/read-all/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                // Update all notifications to read state
                document.querySelectorAll('.notification-item.unread').forEach(item => {
                    item.classList.remove('unread');
                });
                
                // Update badge
                this.updateNotificationBadge(0);
                
                // Show success message
                this.showToast('All notifications marked as read', 'success');
            }
        } catch (error) {
            console.error('Error marking all as read:', error);
            this.showToast('Error marking notifications as read', 'error');
        }
    }
    
    getNotificationColor(type) {
        const colors = {
            'donation_claimed': 'warning',
            'donation_completed': 'success',
            'new_donation': 'info',
            'rating_received': 'primary',
            'message_received': 'secondary',
            'system': 'dark',
            'dietary_match': 'success'
        };
        return colors[type] || 'primary';
    }
    
    getNotificationIcon(type) {
        const icons = {
            'donation_claimed': 'hand-holding-heart',
            'donation_completed': 'check-circle',
            'new_donation': 'utensils',
            'rating_received': 'star',
            'message_received': 'envelope',
            'system': 'info-circle',
            'dietary_match': 'apple-alt'
        };
        return icons[type] || 'bell';
    }
    
    setupEventListeners() {
        // Mark all as read
        const markAllReadBtn = document.getElementById('markAllRead');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.markAllAsRead();
            });
        }
        
        // Request notification permission for browser notifications
        this.requestNotificationPermission();
    }
    
    setupDropdownListener() {
        const dropdown = document.getElementById('notificationDropdown');
        if (dropdown) {
            dropdown.addEventListener('show.bs.dropdown', () => {
                this.loadNotifications();
            });
        }
    }
    
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    console.log('Notification permission granted');
                }
            });
        }
    }
    
    startPolling() {
        // Poll for new notifications every 30 seconds
        this.pollingInterval = setInterval(() => {
            this.loadNotificationCount();
        }, 30000);
    }
    
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
    }
    
    showToast(message, type = 'info') {
        // Use the foodLoopUI toast system if available
        if (window.foodLoopUI && window.foodLoopUI.showToast) {
            window.foodLoopUI.showToast(message, type);
        } else {
            // Fallback toast
            const toast = document.createElement('div');
            toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
            toast.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
            toast.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 3000);
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.notificationManager = new NotificationManager();
});

// Add CSS for pulse animation
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    .pulse {
        animation: pulse 0.6s ease-in-out;
    }
    .notification-item {
        cursor: pointer;
        transition: background-color 0.2s ease;
    }
    .notification-item:hover {
        background-color: rgba(0,0,0,0.02);
    }
    .notification-item.unread {
        background-color: rgba(0,123,255,0.05);
        border-left: 3px solid #007bff;
    }
`;
document.head.appendChild(style);