// Image fallback system for level thumbnails
document.addEventListener('DOMContentLoaded', function() {
    // Handle image loading errors
    const images = document.querySelectorAll('img[src*="youtube"], img[src*="streamable"], img[loading="lazy"]');
    
    images.forEach(img => {
        img.addEventListener('error', function() {
            // Create a colorful placeholder based on level name
            const levelName = this.alt || 'Level';
            const placeholder = createPlaceholder(levelName, this.width || 206, this.height || 116);
            
            // Replace image with placeholder
            const placeholderDiv = document.createElement('div');
            placeholderDiv.innerHTML = placeholder;
            placeholderDiv.className = this.className;
            placeholderDiv.style.width = (this.width || 206) + 'px';
            placeholderDiv.style.height = (this.height || 116) + 'px';
            placeholderDiv.style.borderRadius = '8px';
            placeholderDiv.style.display = 'flex';
            placeholderDiv.style.alignItems = 'center';
            placeholderDiv.style.justifyContent = 'center';
            placeholderDiv.style.fontSize = '12px';
            placeholderDiv.style.fontWeight = 'bold';
            placeholderDiv.style.color = 'white';
            placeholderDiv.style.textAlign = 'center';
            placeholderDiv.style.textShadow = '1px 1px 2px rgba(0,0,0,0.5)';
            
            this.parentNode.replaceChild(placeholderDiv, this);
        });
        
        // Add loading animation
        img.style.transition = 'opacity 0.3s ease';
        img.style.opacity = '0';
        
        img.addEventListener('load', function() {
            this.style.opacity = '1';
        });
    });
});

function createPlaceholder(levelName, width, height) {
    // Generate color based on level name
    const colors = [
        'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
        'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
        'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
        'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)',
        'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
        'linear-gradient(135deg, #ff8a80 0%, #ea4c89 100%)',
        'linear-gradient(135deg, #8fd3f4 0%, #84fab0 100%)'
    ];
    
    let hash = 0;
    for (let i = 0; i < levelName.length; i++) {
        const char = levelName.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
    }
    
    const colorIndex = Math.abs(hash) % colors.length;
    const gradient = colors[colorIndex];
    
    // Get first letter or emoji
    const firstChar = levelName.charAt(0).toUpperCase();
    const isEmoji = /[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]/u.test(firstChar);
    
    return `
        <div style="
            background: ${gradient};
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            border-radius: 8px;
            position: relative;
            overflow: hidden;
        ">
            <div style="font-size: ${width > 150 ? '24px' : '18px'}; margin-bottom: 4px;">
                ${isEmoji ? firstChar : '🎮'}
            </div>
            <div style="font-size: ${width > 150 ? '10px' : '8px'}; opacity: 0.9; max-width: 90%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                ${levelName.length > 15 ? levelName.substring(0, 15) + '...' : levelName}
            </div>
            <div style="
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.2) 0%, transparent 50%);
                pointer-events: none;
            "></div>
        </div>
    `;
}

// Lazy loading optimization
function initializeLazyLoading() {
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initializeLazyLoading);