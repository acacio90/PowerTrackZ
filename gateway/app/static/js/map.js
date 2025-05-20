document.addEventListener('DOMContentLoaded', function() {
    // Variáveis globais
    let map;
    let markers = [];
    let currentMarker = null;

    // Inicializa o mapa
    function initMap() {
        const mapContainer = document.querySelector('.map-content');
        if (!mapContainer) return;

        // Configuração inicial do mapa
        map = L.map(mapContainer).setView([-24.061258, -52.386096], 13);
        
        // Adiciona o tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        // Adiciona os marcadores existentes
        addExistingMarkers();

        // Adiciona evento de clique no mapa
        map.on('click', function(e) {
            const lat = e.latlng.lat;
            const lng = e.latlng.lng;
            
            // Atualiza os campos do formulário
            document.getElementById('latitude').value = lat.toFixed(6);
            document.getElementById('longitude').value = lng.toFixed(6);
            
            // Atualiza o marcador
            updateMarker(lat, lng);
        });
    }

    // Adiciona marcadores existentes
    function addExistingMarkers() {
        const accessPoints = document.querySelectorAll('tbody tr');
        accessPoints.forEach(row => {
            const cells = row.querySelectorAll('td');
            const lat = parseFloat(cells[1].textContent);
            const lng = parseFloat(cells[2].textContent);
            const description = cells[0].textContent;

            if (!isNaN(lat) && !isNaN(lng)) {
                addMarker(lat, lng, description);
            }
        });
    }

    // Adiciona um novo marcador
    function addMarker(lat, lng, description) {
        const marker = L.marker([lat, lng]).addTo(map);
        marker.bindPopup(description);
        markers.push(marker);
    }

    // Atualiza o marcador atual
    function updateMarker(lat, lng) {
        if (currentMarker) {
            map.removeLayer(currentMarker);
        }
        currentMarker = L.marker([lat, lng]).addTo(map);
    }

    // Atualiza o mapa quando novos pontos são adicionados
    function updateMap() {
        fetch('/api/access-points')
            .then(response => response.json())
            .then(data => {
                // Limpa marcadores existentes
                markers.forEach(marker => map.removeLayer(marker));
                markers = [];

                // Adiciona novos marcadores
                data.forEach(ap => {
                    addMarker(ap.latitude, ap.longitude, ap.description);
                });
            })
            .catch(error => {
                console.error('Erro ao atualizar mapa:', error);
                showAlert('Erro ao atualizar o mapa', 'danger');
            });
    }

    // Inicializa o mapa
    initMap();

    // Atualiza o mapa a cada 30 segundos
    setInterval(updateMap, 30000);
}); 