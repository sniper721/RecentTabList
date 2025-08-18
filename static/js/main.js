/**
 * Geometry Dash Demon List - Main JavaScript
 * Contains common functionality for the website
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Add fade-in animation to main content
    const mainContent = document.querySelector('.container.mt-4');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }
    
    // Add active class to current nav item
    const currentPath = window.location.pathname;
    document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
    
    // Handle flash messages auto-dismiss
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(message => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(message);
            bsAlert.close();
        }, 5000); // Auto-dismiss after 5 seconds
    });
    
    // Add click event to level rows and cards if they exist
    const levelRows = document.querySelectorAll('.level-row');
    if (levelRows.length > 0) {
        levelRows.forEach(row => {
            row.addEventListener('click', function() {
                const levelId = this.getAttribute('data-level-id');
                if (levelId) {
                    window.location.href = `/level/${levelId}`;
                }
            });
        });
    }
    
    // Handle level cards for the new grid layout
    const levelCards = document.querySelectorAll('.level-card');
    if (levelCards.length > 0) {
        levelCards.forEach(card => {
            card.addEventListener('click', function() {
                const levelId = this.getAttribute('data-level-id');
                if (levelId) {
                    window.location.href = `/level/${levelId}`;
                }
            });
        });
    }
    
    // Add confirmation for delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Add YouTube video preview on hover if available
    const videoLinks = document.querySelectorAll('a[href*="youtube.com"], a[href*="youtu.be"]');
    videoLinks.forEach(link => {
        link.addEventListener('mouseenter', function() {
            const url = this.getAttribute('href');
            let videoId = '';
            
            if (url.includes('youtube.com')) {
                videoId = url.split('v=')[1].split('&')[0];
            } else if (url.includes('youtu.be')) {
                videoId = url.split('/').pop();
            }
            
            if (videoId) {
                const preview = document.createElement('div');
                preview.classList.add('video-preview');
                preview.innerHTML = `
                    <img src="https://img.youtube.com/vi/${videoId}/mqdefault.jpg" alt="Video Preview">
                    <div class="play-button"><i class="fas fa-play"></i></div>
                `;
                
                this.appendChild(preview);
            }
        });
        
        link.addEventListener('mouseleave', function() {
            const preview = this.querySelector('.video-preview');
            if (preview) {
                preview.remove();
            }
        });
    });
    
    // Form validation for record submission
    const recordForm = document.querySelector('form[action*="submit_record"]');
    if (recordForm) {
        recordForm.addEventListener('submit', function(e) {
            const progressInput = document.getElementById('progress');
            const videoInput = document.getElementById('video_url');
            
            if (progressInput && videoInput) {
                const progress = parseInt(progressInput.value);
                const videoUrl = videoInput.value;
                
                if (progress < 50) {
                    e.preventDefault();
                    alert('Progress must be at least 50%');
                    return;
                }
                
                if (!videoUrl.includes('youtube.com') && !videoUrl.includes('youtu.be')) {
                    e.preventDefault();
                    alert('Please provide a valid YouTube URL');
                    return;
                }
            }
        });
    }
    
    // Theme handling
    initializeTheme();
    
    // Handle theme toggle clicks
    const themeToggle = document.querySelector('a[href*="toggle_theme"]');
    if (themeToggle) {
        themeToggle.addEventListener('click', function(e) {
            e.preventDefault();
            toggleTheme();
        });
    }
});

/**
 * Initialize theme on page load
 */
function initializeTheme() {
    const currentTheme = document.body.getAttribute('data-bs-theme') || 'light';
    updateThemeIcon(currentTheme);
    
    // Add smooth transitions
    document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    
    // Apply transitions to all theme-sensitive elements
    const elements = document.querySelectorAll('.card, .navbar, .btn, .form-control, .form-select, .dropdown-menu, .alert');
    elements.forEach(el => {
        el.style.transition = 'background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease';
    });
}

/**
 * Toggle between light and dark themes
 */
function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-bs-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    // Update the theme
    document.body.setAttribute('data-bs-theme', newTheme);
    updateThemeIcon(newTheme);
    
    // Send request to server to save theme preference
    fetch('/toggle_theme', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    }).catch(error => {
        console.error('Error saving theme preference:', error);
    });
}

/**
 * Update the theme toggle icon
 */
function updateThemeIcon(theme) {
    const themeIcon = document.querySelector('a[href*="toggle_theme"] i');
    if (themeIcon) {
        if (theme === 'dark') {
            themeIcon.className = 'fas fa-sun';
            themeIcon.parentElement.title = 'Switch to Light Mode';
        } else {
            themeIcon.className = 'fas fa-moon';
            themeIcon.parentElement.title = 'Switch to Dark Mode';
        }
    }
}

/**
 * Back to top functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    const backToTopButton = document.getElementById('backToTop');
    
    if (backToTopButton) {
        // Show/hide button based on scroll position
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                backToTopButton.style.display = 'block';
                backToTopButton.style.opacity = '1';
            } else {
                backToTopButton.style.opacity = '0';
                setTimeout(() => {
                    if (window.pageYOffset <= 300) {
                        backToTopButton.style.display = 'none';
                    }
                }, 300);
            }
        });
        
        // Smooth scroll to top
        backToTopButton.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
        
        // Add transition
        backToTopButton.style.transition = 'opacity 0.3s ease, transform 0.2s ease';
        
        // Add hover effect
        backToTopButton.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1)';
        });
        
        backToTopButton.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    }
});