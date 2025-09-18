// Config
const GRID_SIZE = 20;
const EMOTION_AXES = {
  x: ['angry', 'happy'],
  y: ['sad', 'fear']
};

// List your JSON files here (adjust paths to your JSON files)
const JSON_FILES = [
  'emotion_json/Abstract_Expressionism_emotion_cache.json',
  'emotion_json/Abstract_Expressionism_emotion_cache_filtered.json',
  // Add more as needed
];

let results = {};
let gridBuckets = new Map();
let selectedCell = null;

// Rotate point by 45 degrees
function rotatePoint(x, y, angleDegrees = 45) {
  const rad = (angleDegrees * Math.PI) / 180;
  const cosT = Math.cos(rad);
  const sinT = Math.sin(rad);
  return {
    x: cosT * x - sinT * y,
    y: sinT * x + cosT * y,
  };
}

// Map emotion to grid coords
function emotionToCoords(emotion) {
  const xVal = (emotion[EMOTION_AXES.x[1]] - emotion[EMOTION_AXES.x[0]]) / 100.1;
  const yVal = (emotion[EMOTION_AXES.y[1]] - emotion[EMOTION_AXES.y[0]]) / 100.1;
  const rotated = rotatePoint(xVal, yVal, 45);
  const x = Math.min(GRID_SIZE - 1, Math.max(0, Math.floor(((rotated.x + 1) * GRID_SIZE) / 2)));
  const y = Math.min(GRID_SIZE - 1, Math.max(0, Math.floor(((rotated.y + 1) * GRID_SIZE) / 2)));
  return { x, y };
}

// Load JSON file
async function loadJson(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Failed to load JSON: ${url}`);
  return resp.json();
}

// Merge multiple JSON files into one object
async function loadAllJsonFiles(urls) {
  const combined = {};
  for (const url of urls) {
    try {
      const data = await loadJson(url);
      Object.assign(combined, data); // merge all key-value pairs
    } catch (err) {
      console.warn(err.message);
    }
  }
  return combined;
}

// Build bucket map (x,y) => [imgPaths]
function buildGridBuckets(data) {
  const buckets = new Map();
  for (const [imgPath, det] of Object.entries(data)) {
    if (!det || !det.emotion) continue;
    const { x, y } = emotionToCoords(det.emotion);
    const key = `${x},${y}`;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(imgPath);
  }
  return buckets;
}

// Render grid heatmap
function renderGrid() {
  const gridDiv = document.getElementById('grid');
  gridDiv.innerHTML = '';
  for (let y = 0; y < GRID_SIZE; y++) {
    for (let x = 0; x < GRID_SIZE; x++) {
      const key = `${x},${y}`;
      const count = gridBuckets.get(key)?.length || 0;
      const cell = document.createElement('div');
      cell.classList.add('cell');
      const brightness = count > 0 ? Math.min(1, Math.log(count + 1) / 3) : 0;
      const green = Math.floor(255 * brightness);
      cell.style.backgroundColor = `rgb(0, ${green}, 0)`;
      cell.title = `Cell ${x},${y}: ${count} images`;
      cell.dataset.key = key;
      cell.onclick = () => selectCell(x, y);
      gridDiv.appendChild(cell);
    }
  }
}

// Select a cell, highlight it, show image + face box
function selectCell(x, y) {
  if (selectedCell) {
    const prev = document.querySelector(`.cell.selected`);
    if (prev) prev.classList.remove('selected');
  }
  const key = `${x},${y}`;
  selectedCell = key;
  const cell = document.querySelector(`.cell[data-key='${key}']`);
  if (cell) cell.classList.add('selected');
  document.getElementById('selected-cell').textContent = key;
  showRandomImage(key);
}

// Show a random image for selected bucket with face box overlay
function showRandomImage(key) {
  const paths = gridBuckets.get(key);
  const faceImg = document.getElementById('face-image');
  const canvas = document.getElementById('face-canvas');
  const ctx = canvas.getContext('2d');
  const infoDiv = document.getElementById('emotion-details');

  if (!paths || paths.length === 0) {
    faceImg.src = '';
    infoDiv.textContent = 'No images in this cell.';
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    return;
  }

  const imgPath = paths[Math.floor(Math.random() * paths.length)];
  const data = results[imgPath];

  faceImg.onload = () => {
    // Match canvas size exactly to loaded image size
    canvas.width = faceImg.width;
    canvas.height = faceImg.height;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (data.face_region) {
      const fr = data.face_region;
      ctx.lineWidth = 3;
      ctx.strokeStyle = 'lime';
      ctx.strokeRect(fr.x, fr.y, fr.w, fr.h);
    }
  };

  faceImg.onerror = () => {
    infoDiv.textContent = 'Failed to load image.';
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  };

  faceImg.src = imgPath;

  infoDiv.innerHTML =
    `<strong>Dominant:</strong> ${data.dominant}<br/>Emotions:<br/>` +
    Object.entries(data.emotion)
      .sort((a, b) => b[1] - a[1])
      .map(([e, v]) => `${e}: ${v.toFixed(1)}%`)
      .join('<br/>');
}

// Initialization
(async () => {
  try {
    results = await loadAllJsonFiles(JSON_FILES);
    gridBuckets = buildGridBuckets(results);
    renderGrid();
  } catch (e) {
    alert('Error loading data: ' + e.message);
  }
})();
