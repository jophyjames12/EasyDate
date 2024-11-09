document.addEventListener('DOMContentLoaded', function () {
    // Show the auth container with a slight delay
    const authContainer = document.querySelector('.auth-container');
    setTimeout(() => {
        authContainer.classList.add('show');
    }, 100);

    // --- Slider Control Section ---
    let currentIndex = 0; // Track the current index of the slider
    const eventSlider = document.querySelector('.event-slider');
    const eventItems = document.querySelectorAll('.event-item');
    const totalItems = eventItems.length;

    // Function to move the slider left or right with cyclic behavior
    function moveSlide(direction) {
        if (direction === 'left') {
            currentIndex = (currentIndex === 0) ? totalItems - 1 : currentIndex - 1;
        } else if (direction === 'right') {
            currentIndex = (currentIndex === totalItems - 1) ? 0 : currentIndex + 1;
        }

        // Calculate the new transform value for the slider
        const slideWidth = eventItems[0].clientWidth;
        const newTransformValue = -currentIndex * slideWidth;
        eventSlider.style.transition = "transform 0.5s ease";
        eventSlider.style.transform = `translateX(${newTransformValue}px)`;
    }

    // Event listeners for left and right arrows
    const leftArrow = document.querySelector('.left-arrow');
    const rightArrow = document.querySelector('.right-arrow');

    if (leftArrow && rightArrow) {
        leftArrow.addEventListener('click', () => moveSlide('left'));
        rightArrow.addEventListener('click', () => moveSlide('right'));
    }

    // Function to close the modal
    function closeModal() {
        const modal = document.getElementById("successModal");
        if (modal) {
            modal.style.display = "none"; // Hide the modal
        }
    }

    // Add event listener to the modal close button
    const closeButton = document.querySelector(".close-btn");
    if (closeButton) {
        closeButton.addEventListener("click", closeModal);
    }

  

});

const form = document.getElementById('dateRequestForm');
form.addEventListener('submit', function(event) {
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(function(position) {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;
            console.log(`Latitude: ${latitude}, Longitude: ${longitude}`);
            // You can save these coordinates in your database or store them
        }, function(error) {
            console.error("Error occurred: " + error.message);
        });
    } else {
        console.log("Geolocation is not supported by this browser.");
    }    
});