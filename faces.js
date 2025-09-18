// Configuration
const GRID_SIZE = 20;
const EMOTION_AXES = {
    'x': ['angry', 'happy'],
    'y': ['sad', 'fear']
};
const EMOTION_COLORS = {
    'angry': '#e74c3c',
    'happy': '#2ecc71',
    'sad': '#3498db',
    'fear': '#9b59b6',
    'surprise': '#f1c40f',
    'neutral': '#95a5a6',
    'disgust': '#1abc9c'
};
const CHUNKS_DIR = 'web_emotion_data/chunks';
const METADATA_URL = 'web_emotion_data/metadata.json';

// State
let emotionData = {};
let grid = {};
let currentPoint = { x: 10, y: 10 };
let currentImage = null;
let metadata = null;
let loadedChunks = 0;

// DOM Elements
const loadingScreen = document.getElementById('loading-screen');
const loadingStatus = document.getElementById('loading-status');
const progressBar = document.getElementById('progress-bar');
const displayImage = document.getElementById('display-image');
const faceBox = document.getElementById('face-box');
const imageTitle = document.getElementById('image-title');
const emotionStats = document.getElementById('emotion-stats');
const emotionGrid = document.getElementById('emotion-grid');
const gridCoords = document.getElementById('grid-coords');
const sliderX = document.getElementById('slider-x');
const sliderY = document.getElementById('slider-y');
const sliderXValue = document.getElementById('slider-x-value');
const sliderYValue = document.getElementById('slider-y-value');
const randomBtn = document.getElementById('random-btn');
const randomCellBtn = document.getElementById('random-cell');

// Initialize
async function init() {
    // Create grid cells
    createGrid();
    
    // Load metadata and then data chunks
    await loadMetadata();
    await loadDataChunks();
    
    // Set up event listeners
    setupEventListeners();
    
    // Start app
    loadingScreen.classList.add('hidden');
    selectCell(currentPoint.x, currentPoint.y);
}

async function loadMetadata() {
    try {
        loadingStatus.textContent = 'Loading metadata...';
        const response = await fetch(METADATA_URL);
        metadata = await response.json();
        
        // Initialize grid with counts from metadata
        for (const [coords, paths] of Object.entries(metadata.grid_index)) {
            let [x, y] = coords.split(',').map(Number);

            grid[coords] = paths;
            
            // Update grid cell color
            const cell = document.querySelector(`.grid-cell[data-x="${x}"][data-y="${y}"]`);
            if (cell) {
                cell.style.backgroundColor = getCellColor(paths.length);
            }
        }
    } catch (error) {
        console.error('Error loading metadata:', error);
        loadingStatus.textContent = 'Error loading metadata';
    }
}

async function loadDataChunks() {
    if (!metadata || !metadata.chunks) return;
    
    const totalChunks = metadata.chunks.length;
    loadingStatus.textContent = `Loading chunks (0/${totalChunks})`;
    
    for (const chunkName of metadata.chunks) {
        try {
            const response = await fetch(`${CHUNKS_DIR}/${chunkName}`);
            const chunkData = await response.json();
            
            // Merge chunk data into emotionData
            for (const [imgPath, data] of Object.entries(chunkData)) {
                emotionData[imgPath] = data;
            }
            
            loadedChunks++;
            progressBar.style.width = `${(loadedChunks / totalChunks) * 100}%`;
            loadingStatus.textContent = `Loading chunks (${loadedChunks}/${totalChunks})`;
            
            // Small delay to prevent UI freezing
            await new Promise(resolve => setTimeout(resolve, 10));
        } catch (error) {
            console.error(`Error loading chunk ${chunkName}:`, error);
        }
    }
}

function createGrid() {
    emotionGrid.innerHTML = '';
    for (let y = 0; y < GRID_SIZE; y++) {
        for (let x = 0; x < GRID_SIZE; x++) {
            const cell = document.createElement('div');
            cell.className = 'grid-cell';
            cell.dataset.x = x;
            cell.dataset.y = y;
            cell.style.backgroundColor = getCellColor(0);
            cell.addEventListener('click', () => {
                selectCell(parseInt(cell.dataset.x), parseInt(cell.dataset.y));
            });
            emotionGrid.appendChild(cell);
        }
    }
}

function getCellColor(count) {
    const logCount = Math.log(count + 1);
    const intensity = Math.min(1, logCount / 4);
    
    // Interpolate from dark blue to green
    const r = Math.floor(26 + intensity * 40);
    const g = Math.floor(82 + intensity * 120);
    const b = Math.floor(118 + intensity * 80);
    
    return `rgb(${r}, ${g}, ${b})`;
}

function setupEventListeners() {
    sliderX.addEventListener('input', () => {
        sliderXValue.textContent = sliderX.value;
        selectCell(parseInt(sliderX.value), parseInt(sliderY.value));
    });
    
    sliderY.addEventListener('input', () => {
        sliderYValue.textContent = sliderY.value;
        selectCell(parseInt(sliderX.value), parseInt(sliderY.value));
    });
    
    randomBtn.addEventListener('click', () => {
        displayRandomImage();
    });
    
    randomCellBtn.addEventListener('click', () => {
        // Get a random cell that has images
        const populatedCells = Object.keys(metadata.grid_index);
        if (populatedCells.length > 0) {
            const randomCell = populatedCells[Math.floor(Math.random() * populatedCells.length)];
            const [x, y] = randomCell.split(',').map(Number);
            selectCell(x, y);
        }
    });
}

function selectCell(x, y) {
    // Update current point
    currentPoint = { x, y };
    gridCoords.textContent = `${x},${y}`;
    
    // Update sliders
    sliderX.value = x;
    sliderY.value = y;
    sliderXValue.textContent = x;
    sliderYValue.textContent = y;
    
    // Update grid selection
    document.querySelectorAll('.grid-cell.selected').forEach(cell => {
        cell.classList.remove('selected');
    });
    
    const cell = document.querySelector(`.grid-cell[data-x="${x}"][data-y="${y}"]`);
    if (cell) {
        cell.classList.add('selected');
        cell.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
    }
    
    // Display a random image from this cell
    displayRandomImage();
}

function displayRandomImage() {
    const key = `${currentPoint.x},${currentPoint.y}`;
    const images = metadata.grid_index[key];
    
    if (!images || images.length === 0) {
        displayImage.src = '';
        faceBox.style.display = 'none';
        imageTitle.textContent = `Zone ${currentPoint.x},${currentPoint.y}: No images found`;
        emotionStats.innerHTML = '<div class="empty-message">No images in this emotion zone</div>';
        return;
    }
    
    // Select random image
    const imgPath = images[Math.floor(Math.random() * images.length)];
    currentImage = emotionData[imgPath];
    
    if (!currentImage) {
        console.error('No data for image:', imgPath);
        return;
    }
    
    // Update UI
    displayImage.src = `wikiart/${imgPath}`;
    imageTitle.textContent = `Artwork from Zone ${currentPoint.x},${currentPoint.y}`;
    
    // Hide face box until image loads and we position it
    faceBox.style.display = 'none';
    
    // Update emotion stats immediately (don't wait for image load)
    updateEmotionStats();
    
    // Set up image load and error handlers
    if (displayImage.complete) {
        // Image already loaded (cached)
        positionFaceBox();
    } else {
        displayImage.onload = positionFaceBox;
        displayImage.onerror = function() {
            this.src = '';
            imageTitle.textContent = `Error loading image: ${imgPath}`;
        };
    }
}

function positionFaceBox() {
    if (!currentImage || !currentImage.face_region) {
        faceBox.style.display = 'none';
        return;
    }
    
    const img = displayImage;
    const container = img.parentElement;
    
    // Get the displayed image dimensions (after scaling)
    const displayedWidth = img.clientWidth;
    const displayedHeight = img.clientHeight;
    
    // Calculate scaling factors
    const scaleX = displayedWidth / img.naturalWidth;
    const scaleY = displayedHeight / img.naturalHeight;
    
    // Calculate image offset within container (due to centering)
    const offsetX = (container.clientWidth - displayedWidth) / 2;
    const offsetY = (container.clientHeight - displayedHeight) / 2;
    
    // Scale and position the face box
    const face = currentImage.face_region;
    faceBox.style.display = 'block';
    faceBox.style.left = `${offsetX + (face.x * scaleX)}px`;
    faceBox.style.top = `${offsetY + (face.y * scaleY)}px`;
    faceBox.style.width = `${face.w * scaleX}px`;
    faceBox.style.height = `${face.h * scaleY}px`;
}

function updateEmotionStats() {
    if (!currentImage || !currentImage.emotion) return;
    
    emotionStats.innerHTML = '';
    
    // Sort emotions by percentage
    const sortedEmotions = Object.entries(currentImage.emotion)
        .sort((a, b) => b[1] - a[1]);
    
    sortedEmotions.forEach(([emotion, percent]) => {
        const emotionBar = document.createElement('div');
        emotionBar.className = 'emotion-bar';
        
        emotionBar.innerHTML = `
            <div class="emotion-label">
                <span>${emotion.charAt(0).toUpperCase() + emotion.slice(1)}</span>
                <span>${percent.toFixed(1)}%</span>
            </div>
            <div class="bar-container">
                <div class="bar-fill" style="width: ${percent}%; background: ${EMOTION_COLORS[emotion] || '#3498db'}"></div>
            </div>
        `;
        
        emotionStats.appendChild(emotionBar);
    });
}

// Handle image loading errors
displayImage.onerror = function() {
    this.src = '';
    faceBox.style.display = 'none';
    imageTitle.textContent = `Error loading image: ${currentImage ? currentImage.path : ''}`;
};

// Update face box on window resize
window.addEventListener('resize', () => {
    if (currentImage) {
        positionFaceBox();
    }
});

// Start the application
window.addEventListener('DOMContentLoaded', init);