window.addEventListener('DOMContentLoaded', function() {
    fetch(window.ACCESS_POINT_URL)
        .then(response => response.json())
        .then(points => {

            function getRaio(frequency) {
                if (!frequency) return 10;
                const freq = String(frequency).replace(',', '.');
                if (freq.startsWith('2.4')) return 20;
                if (freq.startsWith('5')) return 15;
                if (freq.startsWith('6')) return 12;
                return 10;
            }
            const aps = (points || [])
                .filter(p => p.latitude !== null && p.latitude !== undefined && p.longitude !== null && p.longitude !== undefined)
                .map(p => ({
                    id: p.id || p.name,
                    x: p.latitude,
                    y: p.longitude,
                    raio: getRaio(p.frequency),
                    label: p.name,
                    canal: p.channel
                }));

            const payload = { aps };
            const backendUrl = window.BACKEND_URL || 'http://localhost:5002/collision-graph';

            fetch(backendUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
            .then(response => response.json())
            .then(data => {
                const elements = [];
                data.nodes.forEach(node => {
                    elements.push({ data: { id: node.id, label: node.label || node.id, canal: node.canal } });
                });
                data.links.forEach(link => {
                    elements.push({ data: { source: link.source, target: link.target, peso: link.peso } });
                });

                cytoscape({
                    container: document.getElementById('cy'),
                    elements: elements,
                    style: [
                        { selector: 'node[canal = "1"]', style: { 'background-color': '#FF4136', 'label': 'data(label)' } },
                        { selector: 'node[canal = "6"]', style: { 'background-color': '#2ECC40', 'label': 'data(label)' } },
                        { selector: 'node[canal = "11"]', style: { 'background-color': '#0074D9', 'label': 'data(label)' } },
                        { selector: 'node', style: { 'background-color': '#888', 'label': 'data(label)' } }, // padrão
                        { selector: 'edge', style: {
                            'width': 'mapData(peso, 0, 50, 8, 1)',
                            'line-color': '#ccc',
                            'label': 'data(peso)',
                            'font-size': 10,
                            'color': '#333',
                            'text-background-color': '#fff',
                            'text-background-opacity': 0.7,
                            'text-background-padding': 2
                        } }
                    ],
                    layout: { name: 'cose' }
                });
            })
            .catch(err => {
                document.getElementById('cy').innerHTML = '<p style="color:red">Erro ao carregar o grafo.</p>';
                console.error(err);
            });
        })
        .catch(err => {
            document.getElementById('cy').innerHTML = '<p style="color:red">Erro ao buscar pontos de acesso.</p>';
            console.error(err);
        });
}); 