document.addEventListener('DOMContentLoaded', function() {
    const mapElement = document.getElementById('map');
    if (!mapElement || typeof L === 'undefined') {
        return;
    }

    const DEFAULT_CENTER = [-24.061072, -52.386024];
    const DEFAULT_ZOOM = 20;

    let selectedCoordinates = null;
    let mapInstance = null;
    let currentMarker = null;
    let currentCircle = null;
    let accessPointLayer = null;
    let lastMarkerBounds = [];

    initMap();

    const btnAddPoint = document.getElementById('btn-add-point');
    if (btnAddPoint) {
        btnAddPoint.addEventListener('click', () => {
            if (selectedCoordinates) {
                updateFormCoordinates(selectedCoordinates.lat, selectedCoordinates.lng);
            }
        });
    }

    function initMap() {
        try {
            mapElement.innerHTML = '';
            mapInstance = L.map('map').setView(DEFAULT_CENTER, DEFAULT_ZOOM);

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            }).addTo(mapInstance);

            accessPointLayer = L.layerGroup().addTo(mapInstance);
            mapInstance.on('click', onMapClick);
            refreshAccessPointMap();
            window.setTimeout(refreshAccessPointMap, 250);

            document.dispatchEvent(new CustomEvent('mapReady', { detail: mapInstance }));
        } catch (error) {
            console.error('Erro ao inicializar mapa:', error);
        }
    }

    function onMapClick(event) {
        if (currentMarker) {
            mapInstance.removeLayer(currentMarker);
        }
        if (currentCircle) {
            mapInstance.removeLayer(currentCircle);
        }

        const redIcon = buildMarkerIcon('red');
        currentMarker = L.marker(event.latlng, { icon: redIcon }).addTo(mapInstance);
        currentCircle = createCircle(event.latlng, 'red').addTo(mapInstance);

        selectedCoordinates = {
            lat: event.latlng.lat,
            lng: event.latlng.lng
        };
        storeCoordinates(selectedCoordinates.lat, selectedCoordinates.lng);
    }

    function renderStoredAccessPoints() {
        const markerBounds = [];
        if (accessPointLayer) {
            accessPointLayer.clearLayers();
        }

        document.querySelectorAll('.data-table tbody tr').forEach(row => {
            const frequency = row.querySelector('td:nth-child(3)')?.textContent.trim() || '';
            const lat = parseFloat(row.dataset.latitude || '');
            const lng = parseFloat(row.dataset.longitude || '');
            if (Number.isNaN(lat) || Number.isNaN(lng)) {
                return;
            }

            const iconColor = frequency.includes('5') ? 'green' : frequency.includes('6') ? 'yellow' : 'blue';
            const freq = frequency.includes('5') ? '5' : frequency.includes('6') ? '6' : '2.4';
            const latLng = [lat, lng];

            L.marker(latLng, { icon: buildMarkerIcon(iconColor) })
                .addTo(accessPointLayer)
                .bindPopup(row.querySelector('td:first-child').textContent.trim());

            createCircle(latLng, iconColor, freq).addTo(accessPointLayer);
            markerBounds.push(latLng);
        });

        lastMarkerBounds = markerBounds;
        focusMap(markerBounds);
    }

    function focusMap(markerBounds) {
        mapInstance.invalidateSize();

        if (!markerBounds.length) {
            mapInstance.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
            return;
        }

        if (markerBounds.length === 1) {
            mapInstance.setView(markerBounds[0], 18);
            return;
        }

        const bounds = L.latLngBounds(markerBounds);
        mapInstance.fitBounds(bounds, { padding: [30, 30], maxZoom: 18 });
    }

    function refreshAccessPointMap() {
        window.requestAnimationFrame(() => {
            if (!mapInstance) {
                return;
            }

            mapInstance.invalidateSize();
            renderStoredAccessPoints();
        });
    }

    window.addEventListener('load', refreshAccessPointMap);
    window.addEventListener('resize', () => {
        if (!mapInstance) {
            return;
        }

        mapInstance.invalidateSize();
        focusMap(lastMarkerBounds);
    });

    function buildMarkerIcon(color) {
        return L.icon({
            iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        });
    }

    function createCircle(latlng, color = 'red', frequency = '2.4') {
        const radius = frequency === '5' ? 15 : frequency === '6' ? 10 : 20;
        const fillColor = color === 'red'
            ? '#f03'
            : color === 'green'
                ? '#0f0'
                : color === 'yellow'
                    ? '#ff0'
                    : '#03f';

        return L.circle(latlng, {
            color: color,
            fillColor: fillColor,
            fillOpacity: 0.2,
            radius: radius
        });
    }

    function storeCoordinates(lat, lng) {
        window.lastSelectedCoordinates = { lat, lng };
    }

    function updateFormCoordinates(lat, lng) {
        if (typeof window.updateCoordinates === 'function') {
            window.updateCoordinates(lat, lng);
        }
    }

    window.refreshAccessPointMap = refreshAccessPointMap;
});
