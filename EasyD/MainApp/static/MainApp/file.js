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

    // Modal close function
    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = "none";
        }
        
    }

    // Show the preferences modal after the "Next" button is clicked
    const nextButton = document.querySelector(".next-btn"); // Change to the correct class
    if (nextButton) {
        nextButton.addEventListener("click", function() {
            const accountCreatedModal = document.getElementById("successModal");
            const preferencesModal = document.getElementById("preferencesModal");

            if (accountCreatedModal && preferencesModal) {
                accountCreatedModal.style.display = "none";  // Hide account created modal
                preferencesModal.style.display = "block";  // Show preferences modal
            }
        });
    }

    // Handle preferences form submission
    const saveButton = document.querySelector(".save-btn");
    if (saveButton) {
        saveButton.addEventListener("submit", function(e) {
            e.preventDefault(); // Prevent form from submitting traditionally

            const selectedPreferences = Array.from(document.querySelectorAll('input[name="preferences"]:checked')).map(input => input.value);

            // Send the selected preferences to the backend (using AJAX)
            // Example using fetch (AJAX)
            fetch('/save_preferences/', {  // Update the URL as needed to match your backend endpoint
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')  // Make sure to handle CSRF token if using Django
                },
                body: JSON.stringify({ preferences: selectedPreferences })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Preferences saved:', data);
                
                // After saving preferences, show success message or close the modal
                const saveButton = document.getElementById(".save-btn");
                if (saveButton) {
                    saveButton.style.display = "none";  // Close the preferences modal
                }
                // Optionally, show a confirmation modal or message here
                alert("Preferences saved successfully!");
            })
            .catch(error => {
                console.error('Error saving preferences:', error);
                alert("There was an error saving your preferences.");
            });
        });
    }

    // Function to get CSRF token (for Django)
    function getCookie(name) {
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
    }

    // Add event listener to the close button (inside the modal)
    const closeButton = document.querySelector(".close-btn");
    if (closeButton) {
        closeButton.addEventListener("click", function() {
            closeModal('preferencesModal');
        });  // Close the preferences modal when clicked
    }

});





