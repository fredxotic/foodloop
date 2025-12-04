/**
 * FoodLoop Notification Manager
 * Handles real-time notification polling and display using Alpine.js & Tailwind
 */

class NotificationManager {
    constructor() {
        this.userId = null;
        this.pollingInterval = null;
        this.pollingRate = 30000; // 30 seconds
        this.isPolling = false;
        this.initialize();
    }
    
    initialize() {
        // Get user ID from meta tag
        this.userId = document.querySelector('meta[name="user-id"]')?.content;
        
        if (!this.userId) {
            console.log('NotificationManager: No user logged in');
            return;
        }
        
        console.log('NotificationManager initialized for user:', this.userId);
        
        // Initial load
        this.loadNotificationCount();
        
        // Start polling
        this.startPolling();
        
        // Setup dropdown listener
        this.setupDropdownListener();
        
        // Request browser notification permission
        this.requestNotificationPermission();
    }
    
    /**
     * Load unread notification count (lightweight)
     */
    async loadNotificationCount() {
        try {
            const response = await fetch('/notifications/count/', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) throw new Error('Failed to load count');
            
            const data = await response.json();
            this.updateNotificationBadge(data.count || 0);
            
        } catch (error) {
            console.error('Notification count error:', error);
        }
    }
    
    /**
     * Load full notification list (heavy - only when dropdown opens)
     */
    async loadNotifications() {
        const container = document.getElementById('notificationList');
        if (!container) return;
        
        // Show loading state
        container.innerHTML = `
            <div class="px-5 py-12 text-center text-slate-400">
                <i class="fas fa-circle-notch fa-spin text-2xl mb-3 text-brand-500"></i>
                <p class="text-xs font-bold uppercase tracking-wide">Loading notifications...</p>
            </div>
        `;
        
        try {
            const response = await fetch('/notifications/', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) throw new Error('Failed to load notifications');
            
            const data = await response.json();
            
            if (data.notifications && data.notifications.length > 0) {
                this.renderNotifications(data.notifications);
            } else {
                this.renderEmptyState();
            }
            
        } catch (error) {
            console.error('Load notifications error:', error);
            this.renderErrorState();
        }
    }
    
    /**
     * Update notification badge count
     */
    updateNotificationBadge(count) {
        const badge = document.getElementById('notificationBadge');
        if (!badge) return;
        
        if (count > 0) {
            badge.style.display = 'block';
            badge.classList.add('animate-pulse');
            
            // Remove pulse after 2 seconds
            setTimeout(() => {
                badge.classList.remove('animate-pulse');
            }, 2000);
        } else {
            badge.style.display = 'none';
        }
    }
    
    /**
     * Render notifications in dropdown
     */
    renderNotifications(notifications) {
        const container = document.getElementById('notificationList');
        if (!container) return;
        
        container.innerHTML = notifications.map(notification => `
            <div class="notification-item ${notification.is_read ? 'bg-white' : 'bg-blue-50 border-l-4 border-blue-500'} 
                 p-4 border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer"
                 data-notification-id="${notification.id}"
                 onclick="window.notificationManager.handleNotificationClick(${notification.id}, '${notification.related_url || ''}')">
                
                <!-- Icon -->
                <div class="flex gap-3 items-start">
                    <div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${this.getNotificationBgColor(notification.type)}">
                        <i class="fas fa-${this.getNotificationIcon(notification.type)} text-sm ${this.getNotificationIconColor(notification.type)}"></i>
                    </div>
                    
                    <!-- Content -->
                    <div class="flex-1 min-w-0">
                        <div class="flex justify-between items-start gap-2 mb-1">
                            <h4 class="font-bold text-sm text-slate-900 line-clamp-1">${this.escapeHtml(notification.title)}</h4>
                            <span class="text-xs text-slate-400 whitespace-nowrap">${notification.time_ago}</span>
                        </div>
                        <p class="text-xs text-slate-600 line-clamp-2 mb-2">${this.escapeHtml(notification.message)}</p>
                        
                        <!-- Actions -->
                        <div class="flex gap-2">
                            ${notification.related_url ? `
                                <button onclick="event.stopPropagation(); window.notificationManager.handleNotificationClick(${notification.id}, '${notification.related_url}')" 
                                        class="text-xs font-semibold text-brand-600 hover:text-brand-700">
                                    View Details →
                                </button>
                            ` : ''}
                            ${!notification.is_read ? `
                                <button onclick="event.stopPropagation(); window.notificationManager.markAsRead(${notification.id})" 
                                        class="text-xs font-semibold text-slate-500 hover:text-slate-700">
                                    Mark Read
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    /**
     * Render empty state
     */
    renderEmptyState() {
        const container = document.getElementById('notificationList');
        if (!container) return;
        
        container.innerHTML = `
            <div class="px-5 py-16 text-center">
                <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <i class="fas fa-bell-slash text-2xl text-slate-300"></i>
                </div>
                <h4 class="text-sm font-bold text-slate-900 mb-1">No notifications</h4>
                <p class="text-xs text-slate-500">You're all caught up!</p>
            </div>
        `;
    }
    
    /**
     * Render error state
     */
    renderErrorState() {
        const container = document.getElementById('notificationList');
        if (!container) return;
        
        container.innerHTML = `
            <div class="px-5 py-16 text-center">
                <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <i class="fas fa-exclamation-triangle text-2xl text-red-500"></i>
                </div>
                <h4 class="text-sm font-bold text-slate-900 mb-1">Oops!</h4>
                <p class="text-xs text-slate-500 mb-4">Unable to load notifications</p>
                <button onclick="window.notificationManager.loadNotifications()" 
                        class="text-xs font-bold text-brand-600 hover:text-brand-700 underline">
                    Try Again
                </button>
            </div>
        `;
    }
    
    /**
     * Handle notification click
     */
    async handleNotificationClick(notificationId, url) {
        // Mark as read
        await this.markAsRead(notificationId);
        
        // Navigate if URL provided
        if (url) {
            window.location.href = url;
        }
    }
    
    /**
     * Mark single notification as read
     */
    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/notifications/${notificationId}/read/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) throw new Error('Failed to mark as read');
            
            // Update UI immediately
            const notificationItem = document.querySelector(`[data-notification-id="${notificationId}"]`);
            if (notificationItem) {
                notificationItem.classList.remove('bg-blue-50', 'border-l-4', 'border-blue-500');
                notificationItem.classList.add('bg-white');
            }
            
            // Reload count
            this.loadNotificationCount();
            
        } catch (error) {
            console.error('Mark as read error:', error);
        }
    }
    
    /**
     * Mark all notifications as read
     */
    async markAllAsRead() {
        try {
            const response = await fetch('/notifications/read-all/', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) throw new Error('Failed to mark all as read');
            
            // Update UI
            document.querySelectorAll('.notification-item').forEach(item => {
                item.classList.remove('bg-blue-50', 'border-l-4', 'border-blue-500');
                item.classList.add('bg-white');
            });
            
            // Update badge
            this.updateNotificationBadge(0);
            
            // Show success toast
            if (window.FoodLoop && window.FoodLoop.showToast) {
                window.FoodLoop.showToast('All notifications marked as read', 'success');
            }
            
        } catch (error) {
            console.error('Mark all as read error:', error);
            if (window.FoodLoop && window.FoodLoop.showToast) {
                window.FoodLoop.showToast('Error marking notifications as read', 'error');
            }
        }
    }
    
    /**
     * Setup dropdown open listener
     */
    setupDropdownListener() {
        const trigger = document.getElementById('notificationTrigger');
        if (!trigger) return;
        
        // Load notifications when dropdown opens (using Alpine's @click event)
        trigger.addEventListener('click', () => {
            setTimeout(() => {
                this.loadNotifications();
            }, 100);
        });
    }
    
    /**
     * Start polling for new notifications
     */
    startPolling() {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.pollingInterval = setInterval(() => {
            this.loadNotificationCount();
        }, this.pollingRate);
        
        console.log(`Notification polling started (every ${this.pollingRate/1000}s)`);
    }
    
    /**
     * Stop polling
     */
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.isPolling = false;
            console.log('Notification polling stopped');
        }
    }
    
    /**
     * Request browser notification permission
     */
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    console.log('✅ Browser notifications enabled');
                }
            });
        }
    }
    
    /**
     * Get notification icon
     */
    getNotificationIcon(type) {
        const icons = {
            'donation_claimed': 'hand-holding-heart',
            'donation_completed': 'check-circle',
            'new_donation': 'utensils',
            'rating_received': 'star',
            'system': 'info-circle'
        };
        return icons[type] || 'bell';
    }
    
    /**
     * Get notification background color
     */
    getNotificationBgColor(type) {
        const colors = {
            'donation_claimed': 'bg-yellow-100',
            'donation_completed': 'bg-green-100',
            'new_donation': 'bg-blue-100',
            'rating_received': 'bg-purple-100',
            'system': 'bg-slate-100'
        };
        return colors[type] || 'bg-slate-100';
    }
    
    /**
     * Get notification icon color
     */
    getNotificationIconColor(type) {
        const colors = {
            'donation_claimed': 'text-yellow-600',
            'donation_completed': 'text-green-600',
            'new_donation': 'text-blue-600',
            'rating_received': 'text-purple-600',
            'system': 'text-slate-600'
        };
        return colors[type] || 'text-slate-600';
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Get CSRF token
     */
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.content || 
               document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               this.getCookie('csrftoken') || '';
    }
    
    /**
     * Get cookie value
     */
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.notificationManager = new NotificationManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.notificationManager) {
        window.notificationManager.stopPolling();
    }
});