// static/js/scripts.js
// JavaScript for FoodLoop application

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all functionality
    initDateTimeInputs();
    initAjaxForms();
    initStatusUpdates();
    initNotifications();
});

// Initialize datetime inputs with proper constraints
function initDateTimeInputs() {
    const datetimeInputs = document.querySelectorAll('input[type="datetime-local"]');
    datetimeInputs.forEach(input => {
        // Set minimum to current datetime
        const now = new Date();
        const localDatetime = now.toISOString().slice(0, 16);
        input.min = localDatetime;
        
        // Add change event listener
        input.addEventListener('change', function() {
            validateDateTimeInput(this);
        });
    });
}

// Validate datetime input
function validateDateTimeInput(input) {
    const selectedDate = new Date(input.value);
    const now = new Date();
    
    if (selectedDate < now) {
        alert('Please select a future date and time');
        input.value = '';
        input.focus();
        return false;
    }
    return true;
}

// Initialize AJAX form submissions
function initAjaxForms() {
    const ajaxForms = document.querySelectorAll('form.ajax-form');
    ajaxForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            submitFormViaAjax(this);
        });
    });
}

// Submit form via AJAX
function submitFormViaAjax(form) {
    const formData = new FormData(form);
    const url = form.getAttribute('action');
    const method = form.getAttribute('method') || 'POST';
    
    // Show loading state
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.textContent = 'Processing...';
    submitButton.disabled = true;
    
    fetch(url, {
        method: method,
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Operation completed successfully!', 'success');
            if (data.redirect) {
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1000);
            }
        } else {
            showNotification(data.error || 'An error occurred', 'error');
        }
    })
    .catch(error => {
        showNotification('Network error. Please try again.', 'error');
        console.error('Error:', error);
    })
    .finally(() => {
        // Restore button state
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    });
}

// Initialize status update buttons
function initStatusUpdates() {
    const statusButtons = document.querySelectorAll('.status-update-btn');
    statusButtons.forEach(button => {
        button.addEventListener('click', function() {
            const donationId = this.getAttribute('data-donation-id');
            const newStatus = this.getAttribute('data-new-status');
            updateDonationStatus(donationId, newStatus);
        });
    });
}

// Update donation status via AJAX
function updateDonationStatus(donationId, newStatus) {
    fetch('/donation/update-status/', {
        method: 'POST',
        body: JSON.stringify({
            donation_id: donationId,
            new_status: newStatus
        }),
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Status updated successfully!', 'success');
            // Reload page after a short delay
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showNotification(data.error || 'Failed to update status', 'error');
        }
    })
    .catch(error => {
        showNotification('Network error. Please try again.', 'error');
        console.error('Error:', error);
    });
}

// Initialize notification system
function initNotifications() {
    // Create notification container if it doesn't exist
    if (!document.getElementById('notification-container')) {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'fixed top-4 right-4 z-50 space-y-2';
        document.body.appendChild(container);
    }
}

// Show notification
function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    const notification = document.createElement('div');
    
    let bgColor = 'bg-blue-500';
    if (type === 'success') bgColor = 'bg-green-500';
    if (type === 'error') bgColor = 'bg-red-500';
    if (type === 'warning') bgColor = 'bg-yellow-500';
    
    notification.className = `${bgColor} text-white px-4 py-2 rounded shadow-lg alert`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.5s';
        setTimeout(() => {
            container.removeChild(notification);
        }, 500);
    }, 5000);
}

// Get CSRF token from cookies
function getCookie(name) {
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

// Search/filter functionality for donations
function filterDonations(searchTerm) {
    const donations = document.querySelectorAll('.donation-card');
    donations.forEach(card => {
        const text = card.textContent.toLowerCase();
        if (text.includes(searchTerm.toLowerCase())) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

// Initialize search if search input exists
const searchInput = document.getElementById('search-donations');
if (searchInput) {
    searchInput.addEventListener('input', function() {
        filterDonations(this.value);
    });
}

// Map integration (placeholder for future functionality)
function initMap() {
    // This would be implemented with a mapping library like Leaflet or Google Maps
    console.log('Map functionality would be initialized here');
}

// Export functions for potential use in other modules
window.FoodLoop = {
    showNotification,
    filterDonations,
    initMap
};