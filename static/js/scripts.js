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
        console.log('✅ FoodLoop UI Initialized');
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

    // =========================================
    // 4. Global Toast Notification System
    // =========================================
    showToast(message, type = 'info') {
        // Check if our container exists, if not create it
        let container = document.querySelector('.fixed-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'fixed-toast-container';
            container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 100;';
            document.body.appendChild(container);
        }

        // Create the toast element
        const toast = document.createElement('div');
        
        // Map types to CSS variables or classes
        const bgColors = {
            'success': 'var(--color-success)',
            'error': 'var(--color-danger)',
            'warning': 'var(--color-warning)',
            'info': 'var(--color-text-main)'
        };

        toast.style.cssText = `
            background-color: ${bgColors[type] || bgColors['info']};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: var(--radius-md);
            margin-bottom: 0.75rem;
            box-shadow: var(--shadow-lg);
            font-weight: 500;
            opacity: 0;
            transform: translateX(20px);
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        `;

        // Add icon based on type
        const icon = type === 'success' ? 'check-circle' : 
                     type === 'error' ? 'exclamation-circle' : 'info-circle';
        
        toast.innerHTML = `<i class="fas fa-${icon}"></i> <span>${message}</span>`;

        container.appendChild(toast);

        // Animate In
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        });

        // Auto Remove
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(20px)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    FoodLoop.init();
    // Expose to window for inline scripts if necessary
    window.FoodLoop = FoodLoop;
});