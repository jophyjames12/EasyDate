document.addEventListener('DOMContentLoaded', function() {
    const authContainer = document.querySelector('.auth-container');
    // Add a small timeout for a fade-in effect
    setTimeout(() => {
        authContainer.classList.add('show');
    }, 100);
});