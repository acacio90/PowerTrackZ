// Inicializa o mapa
document.addEventListener('DOMContentLoaded', function() {
    const mapElement = document.getElementById('map');
    if (!mapElement) return;
    
    let selectedCoordinates = null;
    let mapInstance = null;
    
    if (typeof L === 'undefined') {
        console.error('Leaflet não carregado');
        return;
    }
    
    const mapIframe = mapElement.querySelector('iframe');
    
    // Inicializa mapa de acordo com estado atual
    if (mapIframe) {
        mapElement.innerHTML = '';
        initMap();
    } else if (mapElement.innerHTML.includes('leaflet')) {
        setTimeout(addClickListenerToExistingMap, 500);
    } else if (mapElement.childElementCount === 0) {
        initMap();
    } else {
        mapElement.innerHTML = '';
        initMap();
    }
    
    // Botão para adicionar ponto
    const btnAddPoint = document.getElementById('btn-add-point');
    if (btnAddPoint) {
        btnAddPoint.addEventListener('click', () => {
            if (selectedCoordinates) {
                updateFormCoordinates(selectedCoordinates.lat, selectedCoordinates.lng);
            }
        });
    }
    
    // Inicializa mapa
    function initMap() {
        try {
            const map = L.map('map').setView([-24.061072, -52.386024], 20);
            mapInstance = map;
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            }).addTo(map);
            
            let currentMarker = null;
            let currentCircle = null;
            
            // Cria círculo baseado na frequência
            function createCircle(latlng, color = 'red', frequency = '2.4') {
                let radius = frequency === '5' ? 15 : frequency === '6' ? 10 : 20;
                
                return L.circle(latlng, {
                    color: color,
                    fillColor: color === 'red' ? '#f03' : color === 'green' ? '#0f0' : color === 'yellow' ? '#ff0' : '#03f',
                    fillOpacity: 0.2,
                    radius: radius
                });
            }
            
            // Gerencia cliques
            function onMapClick(e) {
                if (currentMarker) map.removeLayer(currentMarker);
                if (currentCircle) map.removeLayer(currentCircle);
                
                const redIcon = L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                });
                
                currentMarker = L.marker(e.latlng, {icon: redIcon}).addTo(map);
                currentCircle = createCircle(e.latlng, 'red').addTo(map);
                
                selectedCoordinates = { lat: e.latlng.lat, lng: e.latlng.lng };
                storeCoordinates(e.latlng.lat, e.latlng.lng);
            }
            
            map.on('click', onMapClick);
            
            // Carrega pontos da tabela
            document.querySelectorAll('.data-table tbody tr').forEach(row => {
                const coords = row.querySelector('.coords')?.textContent.trim().split(',');
                const frequency = row.querySelector('td:nth-child(3)')?.textContent.trim();
                
                if (coords?.length === 2) {
                    const [lat, lng] = coords.map(c => parseFloat(c.trim()));
                    
                    if (!isNaN(lat) && !isNaN(lng)) {
                        const iconColor = frequency.includes('5') ? 'green' : frequency.includes('6') ? 'yellow' : 'blue';
                        const freq = frequency.includes('5') ? '5' : frequency.includes('6') ? '6' : '2.4';
                        
                        L.marker([lat, lng], {
                            icon: L.icon({
                                iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${iconColor}.png`,
                                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                                iconSize: [25, 41],
                                iconAnchor: [12, 41],
                                popupAnchor: [1, -34],
                                shadowSize: [41, 41]
                            })
                        }).addTo(map).bindPopup(row.querySelector('td:first-child').textContent.trim());
                        
                        createCircle([lat, lng], iconColor, freq).addTo(map);
                    }
                }
            });
            
            document.dispatchEvent(new CustomEvent('mapReady', { detail: map }));
        } catch (error) {
            console.error("Erro ao inicializar mapa:", error);
        }
    }
    
    // Gerencia mapa existente
    function addClickListenerToExistingMap() {
        try {
            const leafletContainer = document.querySelector('.leaflet-container');
            
            if (leafletContainer) {
                let leafletMap = mapElement._leaflet_id ? mapElement._leaflet_map : null;
                
                if (!leafletMap) {
                    document.querySelectorAll('[class*="leaflet"]').forEach(el => {
                        if (el._leaflet_id) leafletMap = el._leaflet_map;
                    });
                }
                
                if (!leafletMap) {
                    mapElement.innerHTML = '';
                    initMap();
                    return;
                }
                
                mapInstance = leafletMap;
                leafletMap.off('click').on('click', e => handleMapClick(leafletMap, e.latlng.lat, e.latlng.lng));
                document.dispatchEvent(new CustomEvent('mapReady', { detail: leafletMap }));
            } else {
                setTimeout(() => {
                    if (!document.querySelector('.leaflet-container')) {
                        mapElement.innerHTML = '';
                        initMap();
                    } else {
                        addClickListenerToExistingMap();
                    }
                }, 1000);
            }
        } catch (error) {
            console.error('Erro ao acessar mapa:', error);
            mapElement.innerHTML = '';
            initMap();
        }
    }
    
    function handleMapClick(map, lat, lng) {
        L.popup()
            .setLatLng([lat, lng])
            .setContent(`Você clicou em: ${lat.toFixed(6)}, ${lng.toFixed(6)}`)
            .openOn(map);
        
        selectedCoordinates = { lat, lng };
        storeCoordinates(lat, lng);
    }
    
    function storeCoordinates(lat, lng) {
        window.lastSelectedCoordinates = { lat, lng };
    }
    
    function updateFormCoordinates(lat, lng) {
        if (typeof window.updateCoordinates === 'function') {
            window.updateCoordinates(lat, lng);
        } else {
            console.error("Função updateCoordinates não encontrada");
        }
    }
});