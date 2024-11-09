document.addEventListener('DOMContentLoaded', function () {
    // Show the auth container with a slight delay
    const authContainer = document.querySelector('.auth-container');
    if (authContainer) {
        setTimeout(() => {
            authContainer.classList.add('show');
        }, 100);
    }

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

    // Add event listener to the modal close button
    const closeButton = document.querySelector(".close-btn");
    if (closeButton) {
        closeButton.addEventListener("click", function() {
            closeModal('preferencesModal');
        });  // Close the preferences modal when clicked

    }

  

});

// Get all forms with the class 'dating-form'
const forms = document.querySelectorAll('.mr-1');

forms.forEach(form => {
    form.addEventListener('submit', function(event) {
        // Prevent the form from submitting immediately
        event.preventDefault();

        // Check if geolocation is supported by the browser
        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition(function(position) {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;

                // Assign the latitude and longitude to the respective hidden input fields
                form.querySelector('#latitude').value = latitude;
                form.querySelector('#longitude').value = longitude;

                // Log the latitude and longitude for verification
                console.log(`Latitude: ${latitude}, Longitude: ${longitude}`);

                // Now submit the form with the geolocation data
                form.submit();
            }, function(error) {
                console.error("Error occurred: " + error.message);
                // If there's an error getting geolocation, submit the form without location data
                form.submit();
            });
        } else {
            console.log("Geolocation is not supported by this browser.");
            // If geolocation is not supported, submit the form without the geolocation data
            form.submit();
        }
    });
});

const searchForm = document.getElementById('search-form');
searchForm.addEventListener('submit', function (event) {
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(function(position) {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;

            // Assign the latitude and longitude to the respective hidden input fields
            searchForm.querySelector('#latitude').value = latitude;
            searchForm.querySelector('#longitude').value = longitude;

            // Log the latitude and longitude for verification
            console.log(`Latitude: ${latitude}, Longitude: ${longitude}`);

            // Now submit the form with the geolocation data
            searchForm.submit();
        }, function(error) {
            console.error("Error occurred: " + error.message);
            // If there's an error getting geolocation, submit the form without location data
            searchForm.submit();
        });
    } else {
        console.log("Geolocation is not supported by this browser.");
        // If geolocation is not supported, submit the form without the geolocation data
        searchForm.submit();
    }
});