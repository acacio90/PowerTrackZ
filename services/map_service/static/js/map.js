document.addEventListener('DOMContentLoaded', (event) => {
    fetch('/access_points')
        .then(response => response.json())
        .then(data => {
            console.log('Access Points:', data);
            // Initialize the map
            var map = L.map('map').setView([-24.061258, -52.386096], 19);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);
            // Add markers to the map
            data.forEach(ap => {
                L.marker([ap.latitude, ap.longitude])
                    .bindPopup(`${ap.description}<br>Frequency: ${ap.frequency}<br>Bandwidth: ${ap.bandwidth}<br>Channel: ${ap.channel}`)
                    .addTo(map);
            });
        })
        .catch(error => console.error('Error fetching access points:', error));
});
