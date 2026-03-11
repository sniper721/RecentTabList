// Background Level Loader- Loads levels after page renders for instant site load
(function() {
   console.log('🔄 Starting background level loading...');
    
    // Check if we're on the index page with empty levels
   const container = document.querySelector('.card-body.p-0');
    
   if (container && container.innerHTML.trim() === '') {
       console.log('📭 No levels found, showing loading indicator...');
        
        // Show loading indicator
       container.innerHTML = `
            <div class="text-center p-5" id="loading-indicator">
                <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-3">Loading levels from database...</p>
            </div>
        `;
        
        // Fetch levels in background
        fetch('/api/levels/main')
            .then(response => response.json())
            .then(data => {
               console.log('✅ Levels loaded:', data.levels?.length || 0, 'levels');
                
               if (data.success && data.levels && data.levels.length > 0) {
                    // Reload the page to render levels server-side
                   console.log('🔄 Reloading page with levels...');
                    window.location.reload();
                } else {
                    // Show error
                   const loadingIndicator = document.getElementById('loading-indicator');
                   if (loadingIndicator) {
                        loadingIndicator.innerHTML = `
                            <div class="alert alert-warning">
                                <i class="fas fa-exclamation-triangle"></i>
                                No levels found. Check MongoDB connection.
                            </div>
                        `;
                    }
                }
            })
            .catch(error => {
               console.error('❌ Error loading levels:', error);
               const loadingIndicator = document.getElementById('loading-indicator');
               if (loadingIndicator) {
                    loadingIndicator.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-circle"></i>
                            Failed to load levels. Please refresh the page.
                        </div>
                    `;
                }
            });
    } else {
       console.log('✅ Levels already loaded, skipping background loader');
    }
})();
