// Initialize the Leaflet map and set the default view (over India)
const map = L.map('map').setView([20.5937, 78.9629], 5);

// Add OpenStreetMap tiles to the map
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Variables to hold user and place markers
let userMarker;
let placeMarkers = [];

// Access the reviews data passed from the Django template
const reviews = JSON.parse(document.getElementById('reviews-data').textContent);

/**
 * Function to locate the user's current position using geolocation
 * This is called when the user clicks the "Locate Me" button
 */
function locateUser() {
    // Check if the browser supports geolocation
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            position => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;

                // Center the map on the user's location and zoom in
                map.setView([lat, lon], 15);

                // Add or update the marker for the user's location
                if (userMarker) {
                    userMarker.setLatLng([lat, lon]).openPopup();
                } else {
                    userMarker = L.marker([lat, lon])
                        .addTo(map)
                        .bindPopup("You are here")
                        .openPopup();
                }
            },
            error => {
                console.error("Error getting location:", error);
                alert("Unable to access your location. Please allow location access.");
            },
            { enableHighAccuracy: true, timeout: 10000 }
        );
    } else {
        alert("Geolocation is not supported by this browser.");
    }
}

// Event listener for the "Locate Me" button to manually trigger geolocation
document.getElementById('locate-btn').addEventListener('click', locateUser);

/**
 * Function to search for places based on selected tag, ambiance, and sorting options
 */
function searchPlaces() {
    // Ensure user location is set before searching
    if (!userMarker) {
        alert("Please allow location access first.");
        locateUser(); // Try locating the user again if not already located
        return;
    }

    // Get values from the filter dropdowns
    const tag = document.getElementById('tag').value;
    const ambiance = document.getElementById('ambiance').value;
    const sortBy = document.getElementById('sort').value;

    // Get user's current latitude and longitude
    const userLat = userMarker.getLatLng().lat;
    const userLon = userMarker.getLatLng().lng;

    // Build the Overpass API query
    let query = `https://overpass-api.de/api/interpreter?data=[out:json];node["amenity"="${tag}"]`;
    if (ambiance !== "any") {
        query += `["atmosphere"="${ambiance}"]`;
    }
    query += `(around:3000,${userLat},${userLon});out qt;`;

    // Fetch data from the Overpass API
    fetch(query)
        .then(response => response.json())
        .then(data => {
            const places = data.elements || [];
            displayPlaces(places, sortBy, userLat, userLon);
        })
        .catch(error => console.error("Error fetching places:", error));
}

/**
 * Function to display the list of places on the map and in the list
 */
function displayPlaces(places, sortBy, userLat, userLon) {
    // Clear existing markers from the map
    placeMarkers.forEach(marker => map.removeLayer(marker));
    placeMarkers = [];

    const placeDetailsDiv = document.getElementById('place-details');
    placeDetailsDiv.innerHTML = "<h2>Places:</h2>";

    // Sort places based on the selected option (distance or reviews)
    if (sortBy === 'distance') {
        places.sort((a, b) => getDistance(userLat, userLon, a.lat, a.lon) - getDistance(userLat, userLon, b.lat, b.lon));
    } else if (sortBy === 'reviews') {
        places.sort((a, b) => (b.tags?.rating || 0) - (a.tags?.rating || 0));//TODO Display  
    }

    // Display each place on the map and list
    places.forEach((place, index) => {
        const lat = place.lat;
        const lon = place.lon;
        const name = place.tags?.name || `Place ${index + 1}`;
        const rating = place.tags?.rating || "No reviews";

        // Add a marker for each place
        const marker = L.marker([lat, lon]).addTo(map);
        marker.bindPopup(`<strong>${name}</strong><br>Rating: ${rating}`);
        placeMarkers.push(marker);

        // Add the place to the list with a rating input
        const placeItem = document.createElement('div');
        placeItem.className = 'place-item';
        placeItem.id = `place-item-${place.id}`;
        placeItem.innerHTML = `
            <strong>${name}</strong> -</span>
            <input type="number" min="1" max="5" id="rating-${place.id}" placeholder="Rate (1-5)">
            <button onclick="ratePlace('${place.id}')">Submit Rating</button>
        `;
        placeDetailsDiv.appendChild(placeItem);
    });
}

/**
 * Function to submit a rating to the backend
 */
function ratePlace(placeId) {
    const ratingInput = document.getElementById(`rating-${placeId}`);
    const ratingValue = parseFloat(ratingInput.value);

    if (isNaN(ratingValue) || ratingValue < 1 || ratingValue > 5) {
        alert("Please enter a rating between 1 and 5");
        return;
    }

    const userLat = userMarker.getLatLng().lat;
    const userLon = userMarker.getLatLng().lng;

    const data = {
        placeId: placeId,
        rating: ratingValue,
        lat: userLat,
        lon: userLon
    };

    fetch('/rate_place/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert(data.message);
        } else {
            alert("Error: " + data.message);
        }
    })
    .catch(error => {
        console.error('Error submitting rating:', error);
        alert('An error occurred while submitting the rating');
    });
}

/**
 * Calculate the distance between two coordinates using the Haversine formula
 */
function getDistance(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

// Initialize user location when the page loads
document.getElementById('locate-btn').click();
