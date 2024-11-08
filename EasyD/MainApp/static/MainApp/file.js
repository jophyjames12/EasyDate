document.addEventListener('DOMContentLoaded', function() {
    const authContainer = document.querySelector('.auth-container');
    setTimeout(() => {
        authContainer.classList.add('show');
    }, 100);

    // Slider control for events (left and right arrows)
    let currentIndex = 0; // Track the current slide index
    const eventSlider = document.querySelector('.event-slider');
    const eventItems = document.querySelectorAll('.event-item');
    const totalItems = eventItems.length;

    // Function to handle the slide movement (cyclic behavior)
    function moveSlide(direction) {
        if (direction === 'left') {
            currentIndex = (currentIndex === 0) ? totalItems - 1 : currentIndex - 1; // Loop back to last slide
        } else if (direction === 'right') {
            currentIndex = (currentIndex === totalItems - 1) ? 0 : currentIndex + 1; // Loop back to first slide
        }

        // Calculate the new transform value to slide the items
        const slideWidth = eventItems[0].clientWidth; // Width of one event item
        const newTransformValue = -currentIndex * slideWidth; // Calculate the translation
        eventSlider.style.transition = "transform 0.5s ease"; // Add smooth transition
        eventSlider.style.transform = `translateX(${newTransformValue}px)`;
    }

    // Add event listeners to the left and right arrows
    const leftArrow = document.querySelector('.left-arrow');
    const rightArrow = document.querySelector('.right-arrow');

    if (leftArrow && rightArrow) {
        leftArrow.addEventListener('click', function() {
            moveSlide('left');
        });
        rightArrow.addEventListener('click', function() {
            moveSlide('right');
        });
    }
});


