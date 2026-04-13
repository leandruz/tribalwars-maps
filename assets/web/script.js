let galleryData = null;
let currentWorldId = null;
let currentServer = null;
let currentTab = 'players';

// Zoom and Pan variables
let zoomLevel = 1;
let isDragging = false;
let startX = 0, startY = 0;
let translateX = 0, translateY = 0;

const SERVER_FLAGS = {
    ".BR": "🇧🇷",
    ".PT": "🇵🇹",
    ".NET": "🌐",
    ".DS": "🇩🇪"
};

const SERVER_NAMES = {
    ".BR": "Brasil",
    ".PT": "Portugal",
    ".NET": "Internacional",
    ".DS": "Alemanha"
};

async function init() {
    try {
        const response = await fetch('Resultados/gallery.json');
        if (!response.ok) throw new Error('Gallery data not found');
        galleryData = await response.json();
        
        document.getElementById('last-update').textContent = `Última atualização: ${galleryData.last_update}`;
        renderGallery();
        initZoomTool();
        
    } catch (error) {
        console.error('Error loading gallery:', error);
        document.getElementById('world-grid').innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; color: #ff6b6b; padding: 40px;">
                <p>Erro ao carregar dados da galeria.</p>
                <small>Certifique-se de que rodou <b>gerar_mapas.py</b> no GitHub Actions.</small>
            </div>
        `;
    }
}

function renderGallery() {
    const grid = document.getElementById('world-grid');
    grid.innerHTML = '';
    
    // Iterar por SERVIDORES
    const servers = Object.keys(galleryData.servers).sort();
    
    servers.forEach(srv => {
        const worldsObj = galleryData.servers[srv];
        const worldIds = Object.keys(worldsObj).sort((a, b) => b.localeCompare(a));
        
        if (worldIds.length === 0) return;

        // Título do Servidor
        const sectionHeader = document.createElement('div');
        sectionHeader.className = 'server-section-header';
        sectionHeader.style.gridColumn = "1 / -1";
        sectionHeader.style.margin = "30px 0 15px 0";
        sectionHeader.innerHTML = `
            <h2 style="display: flex; align-items: center; gap: 10px; font-size: 1.5rem;">
                <span>${SERVER_FLAGS[srv] || '🏳️'}</span>
                <span>${SERVER_NAMES[srv] || srv}</span>
                <span style="font-size: 0.9rem; color: var(--text-secondary); font-weight: normal;">(${srv})</span>
            </h2>
        `;
        grid.appendChild(sectionHeader);

        // Cards dos Mundos
        worldIds.forEach(id => {
            const world = worldsObj[id];
            const card = document.createElement('div');
            card.className = 'world-card';
            card.onclick = () => showWorld(srv, id);
            
            card.innerHTML = `
                <div class="icon">🏘️</div>
                <h3>${world.name}</h3>
                <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 5px;">
                    ${world.players.length + world.tribes.length} Mapas
                </p>
            `;
            grid.appendChild(card);
        });
    });
}

function showWorld(srv, worldId) {
    currentServer = srv;
    currentWorldId = worldId;
    
    document.getElementById('world-grid').style.display = 'none';
    document.getElementById('gallery-view').style.display = 'block';
    
    const worldData = galleryData.servers[srv][worldId];
    document.getElementById('world-title').innerHTML = `
        <span style="margin-right: 10px;">${SERVER_FLAGS[srv]}</span> ${worldData.name}
    `;
    
    renderMaps();
}

function goBack() {
    document.getElementById('world-grid').style.display = 'grid';
    document.getElementById('gallery-view').style.display = 'none';
    window.scrollTo(0, 0);
}

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`.tab-btn[onclick="switchTab('${tab}')"]`).classList.add('active');
    renderMaps();
}

function renderMaps() {
    const grid = document.getElementById('maps-grid');
    grid.innerHTML = '';
    
    const world = galleryData.servers[currentServer][currentWorldId];
    const maps = currentTab === 'players' ? world.players : world.tribes;
    
    if (!maps || maps.length === 0) {
        grid.innerHTML = '<p style="grid-column:1/-1; text-align:center; padding: 40px; color: var(--text-secondary);">Nenhum mapa disponível nesta categoria.</p>';
        return;
    }

    maps.forEach(map => {
        const card = document.createElement('div');
        card.className = 'map-card';
        
        // Caminho absoluto para os BBcodes
        const baseUrl = window.location.href.split('?')[0].split('#')[0].replace('index.html', '');
        const fullUrl = baseUrl + map.path;
        
        card.innerHTML = `
            <div class="map-img-container">
                <img src="${map.path}" class="map-thumb" onclick="openModal('${map.path}')">
            </div>
            <div class="map-info">
                <div class="map-title">${map.title}</div>
                <div class="copy-actions">
                    <button class="btn-copy" onclick="copyText('[IMG]${fullUrl}[/IMG]', this)">BBCode</button>
                    <button class="btn-copy" onclick="copyText('![${map.title}](${fullUrl})', this)">Markdown</button>
                    <button class="btn-copy" onclick="copyText('${fullUrl}', this)">URL</button>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function copyText(text, btn) {
    const originalText = btn.textContent;
    navigator.clipboard.writeText(text).then(() => {
        btn.textContent = 'Copiado!';
        btn.style.backgroundColor = '#10b981'; // Emerald 500
        btn.style.color = 'white';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.backgroundColor = '';
            btn.style.color = '';
        }, 1500);
    });
}

function openModal(src) {
    const modal = document.getElementById('modal');
    const modalImg = document.getElementById('modal-img');
    modalImg.src = src;
    
    // Reset zoom and pan
    zoomLevel = 1;
    translateX = 0;
    translateY = 0;
    updateModalTransform();
    
    modal.style.display = 'flex';
}

function updateModalTransform() {
    const modalImg = document.getElementById('modal-img');
    modalImg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${zoomLevel})`;
}

function initZoomTool() {
    const modalImg = document.getElementById('modal-img');
    const modal = document.getElementById('modal');

    // Zoom com o scroll do mouse
    modal.addEventListener('wheel', (e) => {
        if (modal.style.display !== 'flex') return;
        e.preventDefault();
        const zoomDelta = e.deltaY * -0.002;
        zoomLevel += zoomDelta;
        zoomLevel = Math.min(Math.max(0.5, zoomLevel), 5); // Limite de 0.5x a 5x
        updateModalTransform();
    }, { passive: false });

    // Iniciar Arrastar
    modalImg.addEventListener('mousedown', (e) => {
        isDragging = true;
        startX = e.clientX - translateX;
        startY = e.clientY - translateY;
        modalImg.style.cursor = 'grabbing';
        e.preventDefault();
    });

    // Parar Arrastar
    window.addEventListener('mouseup', () => {
        isDragging = false;
        modalImg.style.cursor = 'grab';
    });

    // Arrastar
    window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        e.preventDefault();
        translateX = e.clientX - startX;
        translateY = e.clientY - startY;
        updateModalTransform();
    });
    
    modalImg.style.cursor = 'grab';
    modalImg.style.transition = 'transform 0.1s ease-out';
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('modal');
    if (event.target == modal) closeModal();
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

init();
