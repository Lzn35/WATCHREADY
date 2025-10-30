// Simple 10-minute idle timeout - no warnings, just logout
class SimpleIdleTimeout {
    constructor() {
        this.idleTimeout = 10 * 60 * 1000; // 10 minutes in milliseconds
        this.lastActivity = Date.now();
        this.timeoutId = null;
        
        this.init();
    }
    
    init() {
        // Set up activity listeners
        this.setupActivityListeners();
        
        // Start the idle check
        this.startIdleCheck();
    }
    
    setupActivityListeners() {
        // Listen for user activity
        const events = ['mousedown', 'keypress', 'click'];
        
        events.forEach(event => {
            document.addEventListener(event, () => {
                this.lastActivity = Date.now();
            }, true);
        });
    }
    
    startIdleCheck() {
        // Check every minute if user is idle
        this.timeoutId = setInterval(() => {
            const timeSinceActivity = Date.now() - this.lastActivity;
            
            if (timeSinceActivity >= this.idleTimeout) {
                // User has been idle for 10 minutes - logout
                this.logout();
            }
        }, 60000); // Check every minute
    }
    
    logout() {
        // Clear the interval
        if (this.timeoutId) {
            clearInterval(this.timeoutId);
        }
        
        // Redirect to logout
        window.location.href = '/logout';
    }
}

// Initialize simple idle timeout
const idleTimeout = new SimpleIdleTimeout();