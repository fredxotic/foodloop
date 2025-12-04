/**
 * FoodLoop Core Scripts
 * Modernized Entry Point for UI/UX Interactions
 */

const FoodLoop = {
    // =========================================
    // 1. Initialization
    // =========================================
    init() {
        this.setupCSRF();
        this.setupMobileMenu();
        this.setupDateTimeInputs();
        this.setupFormValidation();
        console.log('FoodLoop UI Initialized');
    },

    // =========================================
    // 2. Security & Networking
    // =========================================
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
    },

    setupCSRF() {
        // Ensure all fetch requests have the CSRF token automatically
        const csrftoken = this.getCookie('csrftoken');
        if (csrftoken) {
            const originalFetch = window.fetch;
            window.fetch = function(url, options = {}) {
                if (!options.headers) options.headers = {};
                if (!options.headers['X-CSRFToken']) {
                    options.headers['X-CSRFToken'] = csrftoken;
                }
                // Add AJAX identifier
                options.headers['X-Requested-With'] = 'XMLHttpRequest';
                return originalFetch(url, options);
            };
        }
    },

    // =========================================
    // 3. UI Components
    // =========================================
    
    // Toggle Sidebar/Navbar on Mobile
    setupMobileMenu() {
        // This is handled via Alpine.js in the new base.html, 
        // but we keep this as a fallback or for specific JS triggers.
        const menuBtn = document.querySelector('[data-toggle="mobile-menu"]');
        if(menuBtn) {
            menuBtn.addEventListener('click', () => {
                document.body.classList.toggle('mobile-menu-open');
            });
        }
    },

    // Standardize DateTime inputs to not allow past dates
    setupDateTimeInputs() {
        const inputs = document.querySelectorAll('input[type="datetime-local"]');
        if (inputs.length > 0) {
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            
            // Format: YYYY-MM-DDTHH:MM
            const minDateTime = `${year}-${month}-${day}T${hours}:${minutes}`;
            
            inputs.forEach(input => {
                if (!input.min) input.min = minDateTime;
            });
        }
    },

    // Setup form validation helpers
    setupFormValidation() {
        // Add real-time validation feedback
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
            
            inputs.forEach(input => {
                input.addEventListener('blur', () => {
                    this.validateInput(input);
                });
                
                input.addEventListener('input', () => {
                    // Clear error on input
                    if (input.classList.contains('border-red-500')) {
                        input.classList.remove('border-red-500', 'bg-red-50');
                        input.classList.add('border-slate-200');
                    }
                });
            });
        });
    },

    validateInput(input) {
        if (!input.checkValidity()) {
            input.classList.add('border-red-500', 'bg-red-50');
            input.classList.remove('border-slate-200');
        } else {
            input.classList.remove('border-red-500', 'bg-red-50');
            input.classList.add('border-slate-200');
        }
    },

    // =========================================
    // 4. Global Toast Notification System
    // =========================================
    showToast(message, type = 'info') {
        // Check if our container exists, if not create it
        let container = document.querySelector('.fixed-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'fixed-toast-container';
            container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 100; max-width: 90vw;';
            document.body.appendChild(container);
        }

        // Create the toast element
        const toast = document.createElement('div');
        
        // Map types to Tailwind classes
        const typeClasses = {
            'success': 'bg-green-500',
            'error': 'bg-red-500',
            'warning': 'bg-yellow-500',
            'info': 'bg-blue-500'
        };

        const iconMap = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };

        toast.className = `${typeClasses[type] || typeClasses['info']} text-white px-5 py-3 rounded-xl shadow-xl mb-3 flex items-center gap-3 min-w-[300px] max-w-[400px] opacity-0 transform translate-x-4 transition-all duration-300`;
        toast.innerHTML = `
            <i class="fas fa-${iconMap[type] || iconMap['info']} text-lg"></i>
            <span class="flex-1 font-medium text-sm">${message}</span>
            <button onclick="this.parentElement.remove()" class="hover:bg-white/20 rounded-full p-1 transition-colors">
                <i class="fas fa-times text-sm"></i>
            </button>
        `;

        container.appendChild(toast);

        // Animate In
        requestAnimationFrame(() => {
            toast.classList.remove('opacity-0', 'translate-x-4');
            toast.classList.add('opacity-100', 'translate-x-0');
        });

        // Auto Remove after 4 seconds
        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-x-4');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    // =========================================
    // 5. Donation Action Helpers
    // =========================================
    async claimDonation(donationId) {
        try {
            const response = await fetch(`/donations/${donationId}/claim/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showToast('Donation claimed successfully!', 'success');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                this.showToast(data.message || 'Failed to claim donation', 'error');
            }
        } catch (error) {
            console.error('Claim error:', error);
            this.showToast('Network error. Please try again.', 'error');
        }
    },

    async completeDonation(donationId) {
        if (!confirm('Mark this donation as completed?')) return;

        try {
            const response = await fetch(`/donations/${donationId}/complete/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showToast('Donation completed! Please rate your experience.', 'success');
                setTimeout(() => window.location.href = `/donations/${donationId}/rate/`, 1500);
            } else {
                this.showToast(data.message || 'Failed to complete donation', 'error');
            }
        } catch (error) {
            console.error('Complete error:', error);
            this.showToast('Network error. Please try again.', 'error');
        }
    },

    // =========================================
    // 6. Image Preview Helper
    // =========================================
    previewImage(input, previewId) {
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const preview = document.getElementById(previewId);
                if (preview) {
                    if (preview.tagName === 'IMG') {
                        preview.src = e.target.result;
                    } else {
                        preview.style.backgroundImage = `url(${e.target.result})`;
                    }
                }
            };
            reader.readAsDataURL(input.files[0]);
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    FoodLoop.init();
    // Expose to window for inline scripts if necessary
    window.FoodLoop = FoodLoop;
});

// Make functions available globally
window.claimDonation = (id) => FoodLoop.claimDonation(id);
window.completeDonation = (id) => FoodLoop.completeDonation(id);