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

    // --- Map Initialization Section ---
    const map = L.map('map').setView([51.505, -0.09], 13); // Default coordinates
    let userMarker; // Marker to represent the user’s location
    let placeMarkers = []; // Array to store markers for the found places

    // Load map tiles from OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Geolocation to center map on user’s location if available
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition((position) => {
            const { latitude, longitude } = position.coords;
            userMarker = L.marker([latitude, longitude]).addTo(map);
            map.setView([latitude, longitude], 14); // Center map on user's location
        }, () => alert("Geolocation is not enabled."));
    } else {
        alert("Geolocation is not supported by this browser.");
    }

    // --- Search Function Section ---
    function searchPlaces() {
        const tag = document.getElementById('tag').value;
        const ambiance = document.getElementById('ambiance').value;
        const sortBy = document.getElementById('sort').value;

        // Ensure user location is available before making API calls
        if (!userMarker) {
            alert("Please allow location access.");
            return;
        }

        const userLat = userMarker.getLatLng().lat;
        const userLon = userMarker.getLatLng().lng;

        // Overpass API query for places with specific tag and ambiance
        const overpassUrl = `https://overpass-api.de/api/interpreter?data=[out:json];
            node["amenity"="${tag}"](around:3000,${userLat},${userLon});
            node["atmosphere"="${ambiance}"](around:3000,${userLat},${userLon});
            out qt;`;

        // Fetch places from Overpass API
        fetch(overpassUrl)
            .then(response => response.json())
            .then(data => {
                let places = data.elements;

                // Fallbacks if no places match both tag and ambiance
                if (places.length === 0) {
                    console.log("No places found with selected criteria, trying with tag only.");
                    const fallbackUrl = `https://overpass-api.de/api/interpreter?data=[out:json];
                        node["amenity"="${tag}"](around:3000,${userLat},${userLon});
                        out qt;`;

                    fetch(fallbackUrl)
                        .then(response => response.json())
                        .then(data => {
                            places = data.elements;
                            if (places.length === 0) {
                                console.log("No places found with selected tag, trying ambiance only.");
                                const ambianceFallbackUrl = `https://overpass-api.de/api/interpreter?data=[out:json];
                                    node["atmosphere"="${ambiance}"](around:3000,${userLat},${userLon});
                                    out qt;`;

                                fetch(ambianceFallbackUrl)
                                    .then(response => response.json())
                                    .then(data => {
                                        places = data.elements;
                                        displayPlaces(places, sortBy, userLat, userLon);
                                    })
                                    .catch(error => console.error("Error fetching ambiance-only places:", error));
                            } else {
                                displayPlaces(places, sortBy, userLat, userLon);
                            }
                        })
                        .catch(error => console.error("Error fetching tag-only places:", error));
                } else {
                    displayPlaces(places, sortBy, userLat, userLon);
                }
            })
            .catch(error => console.error("Error fetching places:", error));
    }

    // --- Function to Display Places ---
    function displayPlaces(places, sortBy, userLat, userLon) {
        // Clear previous markers
        placeMarkers.forEach(marker => map.removeLayer(marker));
        placeMarkers = [];

        const placeDetailsDiv = document.getElementById('place-details');
        placeDetailsDiv.innerHTML = "<h2>Places:</h2>";

        if (places.length === 0) {
            placeDetailsDiv.innerHTML = "<h2>No places found matching the criteria</h2>";
            return;
        }

        // Sort places by distance or reviews based on selection
        if (sortBy === 'distance') {
            places.sort((a, b) => {
                const distanceA = getDistance(userLat, userLon, a.lat, a.lon);
                const distanceB = getDistance(userLat, userLon, b.lat, b.lon);
                return distanceA - distanceB;
            });
        } else if (sortBy === 'reviews') {
            places.sort((a, b) => (b.tags?.rating || 0) - (a.tags?.rating || 0));
        }

        // Add each place as a marker on the map and list in the sidebar
        places.forEach((place, index) => {
            const lat = place.lat;
            const lon = place.lon;
            const name = place.tags?.name || `Place ${index + 1}`;
            const rating = place.tags?.rating || "No reviews";

            const marker = L.marker([lat, lon]).addTo(map);
            marker.bindPopup(`<strong>${name}</strong><br>Rating: ${rating}`);
            placeMarkers.push(marker);

            const placeItem = document.createElement('div');
            placeItem.className = 'place-item';
            placeItem.innerHTML = `<strong>${name}</strong> - ${rating} - Click for directions`;
            placeItem.onclick = () => showRouteToPlace(lat, lon);
            placeDetailsDiv.appendChild(placeItem);
        });
    }

    // --- Helper Functions ---

    // Calculate distance between two points
    function getDistance(lat1, lon1, lat2, lon2) {
        const R = 6371e3; // Earth radius in meters
        const φ1 = lat1 * Math.PI / 180;
        const φ2 = lat2 * Math.PI / 180;
        const Δφ = (lat2 - lat1) * Math.PI / 180;
        const Δλ = (lon2 - lon1) * Math.PI / 180;

        const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
            Math.cos(φ1) * Math.cos(φ2) *
            Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        return R * c; // Distance in meters
    }

    // Show route to the selected place on the map
    function showRouteToPlace(lat, lon) {
        L.Routing.control({
            waypoints: [
                L.latLng(userMarker.getLatLng().lat, userMarker.getLatLng().lng),
                L.latLng(lat, lon)
            ],
            routeWhileDragging: true
        }).addTo(map);
    }
});
