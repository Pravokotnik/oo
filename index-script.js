// Non-module JavaScript implementation
document.addEventListener('DOMContentLoaded', function() {
    // Track scroll position
    const curtainsContainer = document.querySelector('.curtains-container');
    const curtainLeft = document.querySelector('.curtain-left');
    const curtainRight = document.querySelector('.curtain-right');
    const scrollIndicator = document.querySelector('.scroll-indicator');
    
    // Threshold for when curtains should be fully open (in percentage of viewport height)
    const SCROLL_THRESHOLD = 0.3;
    
    function handleScroll() {
        const scrollPosition = window.scrollY;
        const windowHeight = window.innerHeight;
        
        // Calculate how much to open the curtains based on scroll position
        const scrollPercentage = Math.min(scrollPosition / (windowHeight * SCROLL_THRESHOLD), 1);
        
        if (scrollPercentage > 0) {
            // Start opening curtains
            curtainLeft.style.transform = `translateX(${-scrollPercentage * 100}%)`;
            curtainRight.style.transform = `translateX(${scrollPercentage * 100}%)`;
            
            // Fade out scroll indicator
            scrollIndicator.style.opacity = 1 - scrollPercentage;
        } else {
            // Reset curtains position
            curtainLeft.style.transform = 'translateX(0)';
            curtainRight.style.transform = 'translateX(0)';
            scrollIndicator.style.opacity = 1;
        }
        
        // Add open class when fully open
        if (scrollPercentage >= 1) {
            curtainsContainer.classList.add('curtain-open');
        } else {
            curtainsContainer.classList.remove('curtain-open');
        }
    }
    
    // Add extra content to make the page scrollable
    function addScrollableContent() {
        const root = document.getElementById('root');
        const extraContent = document.createElement('div');
        extraContent.style.height = '150vh';
        extraContent.style.padding = '20px';
        extraContent.style.backgroundColor = '#f5f5f5';
        extraContent.innerHTML = `
            <h1 style="margin-top: 20px; text-align: center;">About Pixellect</h1>
            <p style="max-width: 800px; margin: 20px auto; line-height: 1.6;">
                Pixellect is an interactive art experience that reveals beautiful artwork 
                through an engaging curtain reveal effect. Scroll down to experience the 
                full effect and discover more about the artwork.
            </p>
        `;
        root.appendChild(extraContent);
    }
    
    // Initialize
    addScrollableContent();
    
    // Set up event listeners
    window.addEventListener('scroll', handleScroll);
    window.addEventListener('resize', handleScroll);
    
    // Initial call to set positions
    handleScroll();
});