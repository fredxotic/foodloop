// static/js/notifications.js - Simplified version without WebSockets
class NotificationManager {
    constructor() {
        this.userId = null;
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
        this.startPolling(); // Use polling instead of WebSockets
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
                }
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }
    
    updateNotificationBadge(count) {
        const badge = document.getElementById('notificationBadge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'block';
            } else {
                badge.style.display = 'none';
            }
        }
    }
    
    renderNotifications(notifications) {
        const container = document.getElementById('notificationList');
        if (!container) return;
        
        if (notifications.length === 0) {
            container.innerHTML = `
                <div class="text-center p-4 text-muted">
                    <i class="fas fa-bell-slash fa-2x mb-2"></i>
                    <p>No new notifications</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = notifications.map(notification => `
            <div class="notification-item ${notification.is_read ? '' : 'unread'} p-3 border-bottom">
                <div class="d-flex align-items-start">
                    <div class="notification-icon bg-${this.getNotificationColor(notification.type)} text-white rounded-circle d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;">
                        <i class="fas fa-${this.getNotificationIcon(notification.type)}"></i>
                    </div>
                    <div class="flex-grow-1 ms-3">
                        <div class="d-flex justify-content-between align-items-start mb-1">
                            <strong class="me-2">${notification.title}</strong>
                            <small class="text-muted">${notification.time_ago}</small>
                        </div>
                        <p class="mb-1 small">${notification.message}</p>
                        ${notification.related_url ? `
                            <a href="${notification.related_url}" class="btn btn-sm btn-outline-primary mt-1">
                                View Details
                            </a>
                        ` : ''}
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    getNotificationColor(type) {
        const colors = {
            'donation_claimed': 'warning',
            'donation_completed': 'success',
            'new_donation': 'info',
            'rating_received': 'primary',
            'message_received': 'secondary',
            'system': 'dark'
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
            'system': 'info-circle'
        };
        return icons[type] || 'bell';
    }
    
    setupEventListeners() {
        // Mark all as read
        const markAllReadBtn = document.getElementById('markAllRead');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', async () => {
                try {
                    const response = await fetch('/notifications/read-all/', {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': this.getCSRFToken(),
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    if (response.ok) {
                        this.loadNotificationCount();
                        this.loadNotifications();
                    }
                } catch (error) {
                    console.error('Error marking all as read:', error);
                }
            });
        }
        
        // Request notification permission
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
        setInterval(() => {
            this.loadNotificationCount();
        }, 30000);
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.notificationManager = new NotificationManager();
});