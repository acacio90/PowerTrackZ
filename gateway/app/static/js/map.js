document.addEventListener('DOMContentLoaded', function() {
    // Verifica se o elemento do mapa existe
    const mapElement = document.getElementById('map');
    if (!mapElement) return;
    
    // Variáveis globais
    let tempMarker = null;
    let selectedCoordinates = null;
    let mapInstance = null;
    
    // Verifica se o Leaflet está carregado
    if (typeof L === 'undefined') {
        console.error('Leaflet não foi carregado!');
        return;
    }
    
    // Se um iframe do mapa for carregado (a partir do HTML do serviço de mapa)
    const mapIframe = mapElement.querySelector('iframe');
    
    if (mapIframe) {
        console.log("Iframe do mapa detectado. Criando novo mapa...");
        // Substituímos o iframe por um novo mapa Leaflet
        mapElement.innerHTML = '';
        initMap();
    } else if (mapElement.innerHTML.includes('leaflet')) {
        console.log("Conteúdo do Leaflet detectado. Adicionando listener...");
        // Se o elemento já tem conteúdo do Leaflet, tentamos adicionar listeners
        setTimeout(addClickListenerToExistingMap, 500);
    } else if (mapElement.childElementCount === 0) {
        console.log("Elemento do mapa vazio. Inicializando novo mapa...");
        // Se o elemento do mapa estiver vazio, inicializar um novo mapa
        initMap();
    } else {
        console.log("Situação não esperada do mapa. Tentando reinicializar...");
        // Para qualquer outra situação, tentamos reinicializar o mapa
        mapElement.innerHTML = '';
        initMap();
    }
    
    // Adicionar evento ao botão "Adicionar Ponto de Acesso"
    const btnAddPoint = document.getElementById('btn-add-point');
    if (btnAddPoint) {
        btnAddPoint.addEventListener('click', function() {
            // Se tiver coordenadas selecionadas, preenche o formulário
            if (selectedCoordinates) {
                updateFormCoordinates(selectedCoordinates.lat, selectedCoordinates.lng);
            }
        });
    }
    
    // Função para inicializar um novo mapa
    function initMap() {
        try {
            // Criar mapa centrado no Brasil
            const map = L.map('map').setView([-15.77972, -47.92972], 5);
            mapInstance = map;
            
            // Adicionar camada de mapa base
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);
            
            // Adicionar marcadores para os pontos de acesso existentes
            addExistingMarkers(map);
            
            // Adicionar evento de clique no mapa
            map.on('click', function(e) {
                handleMapClick(map, e.latlng.lat, e.latlng.lng);
            });
            
            console.log("Mapa inicializado com sucesso.");
            
            // Disparar evento personalizado de que o mapa está pronto
            document.dispatchEvent(new CustomEvent('mapReady', { detail: map }));
        } catch (error) {
            console.error("Erro ao inicializar mapa:", error);
        }
    }
    
    // Função para adicionar listener de clique ao mapa existente
    function addClickListenerToExistingMap() {
        try {
            // Verificar se há div do Leaflet (classes 'leaflet-container', 'leaflet-pane', etc)
            const leafletContainer = document.querySelector('.leaflet-container');
            
            if (leafletContainer) {
                console.log("Container Leaflet encontrado. Tentando acessar o mapa...");
                
                // Tentar encontrar a instância do mapa no elemento ou seus filhos
                let leafletMap = null;
                
                // Verificar se o mapa está no próprio elemento
                if (mapElement._leaflet_id) {
                    leafletMap = mapElement._leaflet_map;
                }
                
                // Se não encontrou, procurar em todos os elementos filhos com classe leaflet
                if (!leafletMap) {
                    const leafletElements = document.querySelectorAll('[class*="leaflet"]');
                    for (const el of leafletElements) {
                        if (el._leaflet_id) {
                            leafletMap = el._leaflet_map;
                            if (leafletMap) break;
                        }
                    }
                }
                
                // Última tentativa: criar um mapa sobre o existente
                if (!leafletMap) {
                    console.log("Não foi possível acessar a instância do mapa. Recriando...");
                    mapElement.innerHTML = '';
                    initMap();
                    return;
                }
                
                mapInstance = leafletMap;
                console.log("Instância do mapa encontrada. Adicionando evento de clique.");
                
                // Remover eventos antigos e adicionar novo
                leafletMap.off('click');
                leafletMap.on('click', function(e) {
                    handleMapClick(leafletMap, e.latlng.lat, e.latlng.lng);
                });
                
                // Disparar evento de que o mapa está pronto
                document.dispatchEvent(new CustomEvent('mapReady', { detail: leafletMap }));
            } else {
                console.log("Container Leaflet não encontrado. Tentando novamente...");
                // Tentar novamente após um tempo ou recriar o mapa
                setTimeout(function() {
                    // Se ainda não encontrou, criar novo mapa
                    if (!document.querySelector('.leaflet-container')) {
                        console.log("Recriando mapa após espera...");
                        mapElement.innerHTML = '';
                        initMap();
                    } else {
                        addClickListenerToExistingMap();
                    }
                }, 1000);
            }
        } catch (error) {
            console.error('Erro ao tentar acessar o mapa:', error);
            // Criar um novo mapa como fallback
            console.log("Erro ao tentar acessar o mapa. Recriando...");
            mapElement.innerHTML = '';
            initMap();
        }
    }
    
    // Função para adicionar marcadores existentes
    function addExistingMarkers(map) {
        try {
            // Buscar coordenadas da tabela
            const rows = document.querySelectorAll('.data-table tbody tr');
            console.log(`Processando ${rows.length} pontos existentes.`);
            
            rows.forEach(row => {
                const coordsCell = row.querySelector('.coords');
                if (coordsCell) {
                    const coordsText = coordsCell.textContent.trim();
                    const coordParts = coordsText.split(',');
                    
                    if (coordParts.length === 2) {
                        const lat = parseFloat(coordParts[0].trim());
                        const lng = parseFloat(coordParts[1].trim());
                        
                        if (!isNaN(lat) && !isNaN(lng)) {
                            console.log(`Adicionando marcador em [${lat}, ${lng}]`);
                            L.marker([lat, lng]).addTo(map)
                                .bindPopup(row.querySelector('td:first-child').textContent.trim());
                        }
                    }
                }
            });
        } catch (error) {
            console.error("Erro ao adicionar marcadores:", error);
        }
    }
    
    // Função para lidar com o clique no mapa
    function handleMapClick(map, lat, lng) {
        console.log(`Coordenadas selecionadas: ${lat.toFixed(6)}, ${lng.toFixed(6)}`);
        
        // Remover marcador temporário anterior, se existir
        if (tempMarker) {
            map.removeLayer(tempMarker);
        }
        
        // Criar um novo marcador temporário com ícone personalizado
        const tempIcon = L.divIcon({
            className: 'temp-marker',
            html: '<i class="fas fa-map-marker-alt" style="color: #ff0000; font-size: 32px;"></i>',
            iconSize: [32, 32],
            iconAnchor: [16, 32]
        });
        
        // Adicionar o novo marcador
        tempMarker = L.marker([lat, lng], {icon: tempIcon}).addTo(map);
        tempMarker.bindPopup("Local selecionado<br>Clique em 'Adicionar Ponto de Acesso' para registrar").openPopup();
        
        // Armazenar as coordenadas selecionadas
        selectedCoordinates = { lat, lng };
        
        // Armazenar as coordenadas para uso posterior sem abrir modal
        storeCoordinates(lat, lng);
    }
    
    // Armazenar coordenadas para uso ao abrir a modal
    function storeCoordinates(lat, lng) {
        window.lastSelectedCoordinates = { lat, lng };
    }
    
    // Atualizar coordenadas no formulário da modal
    function updateFormCoordinates(lat, lng) {
        if (typeof window.updateCoordinates === 'function') {
            window.updateCoordinates(lat, lng);
        } else {
            console.error("Função updateCoordinates não encontrada");
        }
    }
}); 