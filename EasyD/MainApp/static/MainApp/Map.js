// Wait for DOM content to load before initializing the map
document.addEventListener('DOMContentLoaded', () => {
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

    // Function to locate the user's current position using geolocation
    function locateUser() {
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

    // Add event listener to "Locate Me" button
    document.getElementById('locate-btn').addEventListener('click', locateUser);

    // Function to search for places based on user input and filters
    function searchPlaces() {
        if (!userMarker) {
            alert("Please locate yourself first using the 'Locate Me' button.");
            return;
        }

        const tag = document.getElementById('tag').value;
        const ambiance = document.getElementById('ambiance').value;
        const sortBy = document.getElementById('sort').value;

        const userLat = userMarker.getLatLng().lat;
        const userLon = userMarker.getLatLng().lng;

        // Build the Overpass API query
        let query = `https://overpass-api.de/api/interpreter?data=[out:json];node["amenity"="${tag}"]`;
        if (ambiance !== "any") {
            query += `["atmosphere"="${ambiance}"]`;
        }
        query += `(around:3000,${userLat},${userLon});out qt;`;

        fetch(query)
            .then(response => response.json())
            .then(data => {
                const places = data.elements || [];
                if (sortBy === 'reviews') {
                    fetch('/sort_places_by_reviews/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ places })
                    })
                    .then(response => response.json())
                    .then(sortedData => {
                        if (sortedData.status === 'success') {
                            displayPlaces(sortedData.sorted_places, sortBy, userLat, userLon);
                        } else {
                            console.error("Error sorting places by reviews:", sortedData.message);
                        }
                    })
                    .catch(error => console.error("Error fetching sorted places by reviews:", error));
                } else {
                    displayPlaces(places, sortBy, userLat, userLon);
                }
            })
            .catch(error => console.error("Error fetching places:", error));
    }

    // Function to display the list of places on the map and in the details section
    function displayPlaces(places, sortBy, userLat, userLon) {
        placeMarkers.forEach(marker => map.removeLayer(marker));
        placeMarkers = [];

        const placeDetailsDiv = document.getElementById('place-details');
        placeDetailsDiv.innerHTML = "<h2>Places:</h2>";

        if (sortBy === 'distance') {
            places.sort((a, b) => getDistance(userLat, userLon, a.lat, a.lon) - getDistance(userLat, userLon, b.lat, b.lon));
        } else if (sortBy === 'reviews') {
            places.sort((a, b) => (b.tags?.rating || 0) - (a.tags?.rating || 0));
        }

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
            placeItem.id = `place-item-${place.id}`;
            placeItem.innerHTML = `
                <strong>${name}</strong> - 
                <input type="number" min="1" max="5" id="rating-${place.id}" placeholder="Rate (1-5)">
                <button onclick="ratePlace('${place.id}')">Submit Rating</button>
            `;
            placeDetailsDiv.appendChild(placeItem);
        });
    }

    // Function to calculate the distance between two points
    function getDistance(lat1, lon1, lat2, lon2) {
        const R = 6371;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }
});
