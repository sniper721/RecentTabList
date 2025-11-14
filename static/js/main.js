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
    
    // YouTube video preview with proper tooltip system - Fixed spasm issue
    let globalTooltip = null;
    let tooltipTimeout = null;
    
    // Create global tooltip container
    function createGlobalTooltip() {
        if (globalTooltip) return globalTooltip;
        
        globalTooltip = document.createElement('div');
        globalTooltip.id = 'youtube-tooltip';
        globalTooltip.style.cssText = `
            position: fixed;
            z-index: 10000;
            background: white;
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s ease;
            max-width: 200px;
        `;
        document.body.appendChild(globalTooltip);
        return globalTooltip;
    }
    
    // Show tooltip
    function showTooltip(element, videoId) {
        const tooltip = createGlobalTooltip();
        const rect = element.getBoundingClientRect();
        
        tooltip.innerHTML = `
            <img src="https://img.youtube.com/vi/${videoId}/mqdefault.jpg" 
                 alt="Video Preview" 
                 style="width: 160px; height: 90px; border-radius: 4px; display: block;">
            <div style="text-align: center; margin-top: 8px; color: #666; font-size: 12px;">
                <i class="fab fa-youtube" style="color: #ff0000;"></i> YouTube Preview
            </div>
        `;
        
        // Position tooltip
        const tooltipRect = tooltip.getBoundingClientRect();
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        let top = rect.bottom + 10;
        
        // Keep tooltip on screen
        if (left < 10) left = 10;
        if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }
        if (top + tooltipRect.height > window.innerHeight - 10) {
            top = rect.top - tooltipRect.height - 10;
        }
        
        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
        tooltip.style.opacity = '1';
    }
    
    // Hide tooltip
    function hideTooltip() {
        if (globalTooltip) {
            globalTooltip.style.opacity = '0';
        }
    }
    
    // Apply to YouTube links
    const videoLinks = document.querySelectorAll('a[href*="youtube.com"], a[href*="youtu.be"]');
    videoLinks.forEach(link => {
        link.addEventListener('mouseenter', function(e) {
            clearTimeout(tooltipTimeout);
            
            const url = this.getAttribute('href');
            let videoId = '';
            
            if (url.includes('youtube.com')) {
                const match = url.match(/[?&]v=([^&]+)/);
                videoId = match ? match[1] : '';
            } else if (url.includes('youtu.be')) {
                videoId = url.split('/').pop().split('?')[0];
            }
            
            if (videoId) {
                tooltipTimeout = setTimeout(() => {
                    showTooltip(this, videoId);
                }, 500); // 500ms delay to prevent accidental triggers
            }
        });
        
        link.addEventListener('mouseleave', function() {
            clearTimeout(tooltipTimeout);
            hideTooltip();
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
                
                if (!videoUrl.includes('youtube.com') && !videoUrl.includes('youtu.be') && 
                    !videoUrl.includes('streamable.com') && !videoUrl.includes('vimeo.com') && 
                    !videoUrl.includes('tiktok.com') && !videoUrl.includes('twitch.tv')) {
                    e.preventDefault();
                    alert('Please provide a valid video URL (YouTube, Streamable, Vimeo, TikTok, or Twitch)');
                    return;
                }
            }
        });
    }
    
    // Theme handling
    initializeTheme();
    
    // Force GD background if already in dark mode
    const currentTheme = document.body.getAttribute('data-bs-theme') || 'light';
    if (currentTheme === 'dark') {
        setTimeout(() => {
            initializeGDBackground();
        }, 1000);
    }
    
    // Handle theme dropdown clicks
    const themeOptions = document.querySelectorAll('.theme-option');
    themeOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.preventDefault();
            const theme = this.getAttribute('data-theme');
            changeTheme(theme);
        });
    });
    
    // Keep old toggle functionality for backwards compatibility
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
    
    // Initialize GD background for dark mode
    if (currentTheme === 'dark') {
        initializeGDBackground();
    }
}

/**
 * Change to a specific theme
 */
function changeTheme(theme) {
    // Update the theme
    document.body.setAttribute('data-bs-theme', theme);
    updateThemeIcon(theme);
    
    // Handle GD background animation
    if (theme === 'dark') {
        initializeGDBackground();
    } else {
        removeGDBackground();
    }
    
    // Send request to server to save theme preference
    fetch(`/toggle_theme?theme=${theme}`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    }).catch(error => {
        console.error('Error saving theme preference:', error);
    });
}

/**
 * Toggle between light and dark themes (for backwards compatibility)
 */
function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-bs-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    changeTheme(newTheme);
}

/**
 * Update the theme toggle icon
 */
function updateThemeIcon(theme) {
    const themeIcon = document.querySelector('#themeDropdown i');
    if (themeIcon) {
        // Update icon based on theme
        switch(theme) {
            case 'dark':
                themeIcon.className = 'fas fa-moon';
                break;
            case 'light':
                themeIcon.className = 'fas fa-sun';
                break;
            case 'auto':
                themeIcon.className = 'fas fa-adjust';
                break;
            default:
                themeIcon.className = 'fas fa-palette';
        }
    }
    
    // Update active state in dropdown
    const themeOptions = document.querySelectorAll('.theme-option');
    themeOptions.forEach(option => {
        option.classList.remove('active');
        if (option.getAttribute('data-theme') === theme) {
            option.classList.add('active');
        }
    });
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

/**
 * GD-Style Background Animation with Smart Counter System
 */
let gdElementCounter = 0;
let gdBackgroundActive = false;

function initializeGDBackground() {
    // Remove any existing GD elements first
    removeGDBackground();
    gdBackgroundActive = true;
    
    console.log('🎮 Initializing GD-style background with smart counter system');
    
    // Create the GD icon with 3 background spikes
    createGDIcon();
    
    // Create initial batch
    createGDBatch();
    
    // Check counter every 2 seconds and create new batch if needed
    window.gdBackgroundInterval = setInterval(() => {
        if (document.body.getAttribute('data-bs-theme') === 'dark' && gdBackgroundActive) {
            // Only create new batch when 2-4 elements remain
            if (gdElementCounter <= 4) {
                console.log(`🔄 Low element count (${gdElementCounter}), creating new batch`);
                createGDBatch();
            }
        }
    }, 2000);
}

function createGDBatch() {
    // Random number between 4-10
    const batchSize = Math.floor(Math.random() * 7) + 4;
    console.log(`📦 Creating batch of ${batchSize} elements`);
    
    for (let i = 0; i < batchSize; i++) {
        // Random delay for each element (0-2 seconds)
        const delay = Math.random() * 2000;
        
        setTimeout(() => {
            // Random element type: 60% cubes, 30% spikes, 10% orbs
            const rand = Math.random();
            if (rand < 0.6) {
                createGDCube();
            } else if (rand < 0.9) {
                createGDSpike();
            } else {
                createGDOrb();
            }
        }, delay);
    }
}

function createGDCube(isPulsing = false) {
    const cube = document.createElement('div');
    cube.className = 'gd-cube';
    
    if (isPulsing) {
        cube.classList.add('pulse');
    }
    
    // Random size for cubes (20-40px)
    const size = Math.random() * 20 + 20;
    cube.style.width = size + 'px';
    cube.style.height = size + 'px';
    
    // Choose random animation direction
    const animations = ['gdCubeFloatUp', 'gdCubeFloatDown', 'gdCubeFloatLeft', 'gdCubeFloatRight'];
    const selectedAnimation = animations[Math.floor(Math.random() * animations.length)];
    cube.style.animationName = selectedAnimation;
    
    // Position based on animation direction
    positionElement(cube, selectedAnimation);
    
    // Random animation duration
    const duration = Math.random() * 6 + 12; // 12-18 seconds
    cube.style.animationDuration = duration + 's';
    
    // Random delay
    const delay = Math.random() * 3;
    cube.style.animationDelay = delay + 's';
    
    // Add click event
    cube.addEventListener('click', () => popGDElement(cube, 'cube'));
    
    document.body.appendChild(cube);
    gdElementCounter++;
    
    console.log(`🟫 Created gray GD cube (${gdElementCounter} total)`);
    
    // Remove after animation
    setTimeout(() => {
        removeGDElement(cube);
    }, (duration + delay + 2) * 1000);
}

function createGDSpike() {
    const spike = document.createElement('div');
    spike.className = 'gd-spike';
    
    // Random spike type (1, 2, or 3)
    const spikeType = Math.floor(Math.random() * 3) + 1;
    spike.classList.add(`type-${spikeType}`);
    
    // Choose random animation direction
    const animations = ['gdSpikeFloatUp', 'gdSpikeFloatSide', 'gdSpikeFloatDiagonal'];
    const selectedAnimation = animations[Math.floor(Math.random() * animations.length)];
    spike.style.animationName = selectedAnimation;
    
    // Position based on animation direction
    positionElement(spike, selectedAnimation);
    
    // Random animation duration
    const duration = Math.random() * 6 + 14; // 14-20 seconds
    spike.style.animationDuration = duration + 's';
    
    // Random delay
    const delay = Math.random() * 4;
    spike.style.animationDelay = delay + 's';
    
    // Add click event
    spike.addEventListener('click', () => popGDElement(spike, 'spike'));
    
    document.body.appendChild(spike);
    gdElementCounter++;
    
    console.log(`⚡ Created gray GD spike (${gdElementCounter} total)`);
    
    // Remove after animation
    setTimeout(() => {
        removeGDElement(spike);
    }, (duration + delay + 2) * 1000);
}

function createGDOrb() {
    const orb = document.createElement('div');
    orb.className = 'gd-orb';
    
    // Random size for orbs (25-45px)
    const size = Math.random() * 20 + 25;
    orb.style.width = size + 'px';
    orb.style.height = size + 'px';
    
    // Choose random animation direction
    const animations = ['gdOrbFloatUp', 'gdOrbFloatCross', 'gdOrbFloatCircle'];
    const selectedAnimation = animations[Math.floor(Math.random() * animations.length)];
    orb.style.animationName = selectedAnimation;
    
    // Position based on animation direction
    positionElement(orb, selectedAnimation);
    
    // Random animation duration
    const duration = Math.random() * 8 + 16; // 16-24 seconds
    orb.style.animationDuration = duration + 's';
    
    // Random delay
    const delay = Math.random() * 5;
    orb.style.animationDelay = delay + 's';
    
    // Add click event
    orb.addEventListener('click', () => popGDElement(orb, 'orb'));
    
    document.body.appendChild(orb);
    gdElementCounter++;
    
    console.log(`🔘 Created gray GD orb (${gdElementCounter} total)`);
    
    // Remove after animation
    setTimeout(() => {
        removeGDElement(orb);
    }, (duration + delay + 2) * 1000);
}

function positionElement(element, animation) {
    switch(animation) {
        case 'gdCubeFloatUp':
        case 'gdSpikeFloatUp':
        case 'gdOrbFloatUp':
            element.style.left = Math.random() * 90 + 5 + '%';
            element.style.bottom = '-60px';
            break;
        case 'gdCubeFloatDown':
            element.style.left = Math.random() * 90 + 5 + '%';
            element.style.top = '-60px';
            break;
        case 'gdCubeFloatLeft':
        case 'gdSpikeFloatSide':
        case 'gdOrbFloatCross':
            element.style.left = '-60px';
            element.style.top = Math.random() * 90 + 5 + '%';
            break;
        case 'gdCubeFloatRight':
            element.style.right = '-60px';
            element.style.top = Math.random() * 90 + 5 + '%';
            break;
        case 'gdSpikeFloatDiagonal':
            element.style.right = '-50px';
            element.style.bottom = '-50px';
            break;
        case 'gdOrbFloatCircle':
            element.style.left = '50%';
            element.style.top = '-60px';
            break;
    }
}

function popGDElement(element, type) {
    // Pop animation
    element.style.transition = 'all 0.3s ease';
    element.style.transform = 'scale(1.5)';
    element.style.opacity = '0';
    
    console.log(`💥 Popped ${type}! (${gdElementCounter - 1} remaining)`);
    
    setTimeout(() => {
        removeGDElement(element);
    }, 300);
}

function removeGDElement(element) {
    if (element && element.parentNode) {
        element.parentNode.removeChild(element);
        gdElementCounter = Math.max(0, gdElementCounter - 1);
    }
}

function createGDIcon() {
    // Remove existing icon
    const existingIcon = document.querySelector('.gd-icon');
    if (existingIcon) {
        existingIcon.remove();
    }
    
    // Create RobTop's face icon
    const icon = document.createElement('div');
    icon.className = 'gd-icon';
    document.body.appendChild(icon);
    
    console.log('😎 Created RobTop face icon');
}

function removeGDBackground() {
    gdBackgroundActive = false;
    
    // Clear interval
    if (window.gdBackgroundInterval) {
        clearInterval(window.gdBackgroundInterval);
        window.gdBackgroundInterval = null;
        console.log('⏹️ Stopped GD background interval');
    }
    
    // Remove existing GD elements
    const cubes = document.querySelectorAll('.gd-cube');
    const spikes = document.querySelectorAll('.gd-spike');
    const orbs = document.querySelectorAll('.gd-orb');
    const icon = document.querySelector('.gd-icon');
    
    cubes.forEach(cube => cube.remove());
    spikes.forEach(spike => spike.remove());
    orbs.forEach(orb => orb.remove());
    if (icon) icon.remove();
    
    gdElementCounter = 0;
    
    console.log(`🗑️ Removed all GD background elements`);
}

