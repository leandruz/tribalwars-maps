let galleryData = null;
let currentWorld = null;
let currentTab = 'players';

async function init() {
    try {
        const response = await fetch('Resultados/gallery.json');
        if (!response.ok) throw new Error('Gallery data not found');
        galleryData = await response.json();
        
        document.getElementById('last-update').textContent = `Última atualização: ${galleryData.last_update}`;
        renderWorldGrid();
        
    } catch (error) {
        console.error('Error loading gallery:', error);
        document.getElementById('world-grid').innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; color: #ff6b6b;">
                Erro ao carregar dados da galeria. Certifique-se de que rodou <b>gerar_mapas.py</b> primeiro.
            </div>
        `;
    }
}

function renderWorldGrid() {
    const grid = document.getElementById('world-grid');
    grid.innerHTML = '';
    
    // Sort worlds by name (br141, br140, etc)
    const worlds = Object.keys(galleryData.worlds).sort((a, b) => b.localeCompare(a));
    
    worlds.forEach(id => {
        const world = galleryData.worlds[id];
        const card = document.createElement('div');
        card.className = 'world-card';
        card.onclick = () => showWorld(id);
        
        card.innerHTML = `
            <div class="icon">🌍</div>
            <h3>${world.name}</h3>
            <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 5px;">
                ${world.players.length + world.tribes.length} Mapas
            </p>
        `;
        grid.appendChild(card);
    });
}

function showWorld(worldId) {
    currentWorld = worldId;
    document.getElementById('world-grid').style.display = 'none';
    document.getElementById('gallery-view').style.display = 'block';
    document.getElementById('world-title').textContent = galleryData.worlds[worldId].name;
    
    renderMaps();
}

function goBack() {
    document.getElementById('world-grid').style.display = 'grid';
    document.getElementById('gallery-view').style.display = 'none';
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
    
    const world = galleryData.worlds[currentWorld];
    const maps = currentTab === 'players' ? world.players : world.tribes;
    
    maps.forEach(map => {
        const card = document.createElement('div');
        card.className = 'map-card';
        
        const fullUrl = window.location.origin + window.location.pathname.replace('index.html', '') + map.path;
        
        card.innerHTML = `
            <img src="${map.path}" class="map-thumb" onclick="openModal('${map.path}')">
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
        btn.style.backgroundColor = 'var(--primary)';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.backgroundColor = '';
        }, 1500);
    });
}

function openModal(src) {
    const modal = document.getElementById('modal');
    const modalImg = document.getElementById('modal-img');
    modalImg.src = src;
    modal.style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

// Close modal on click outside
window.onclick = function(event) {
    const modal = document.getElementById('modal');
    if (event.target == modal) {
        closeModal();
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

init();
