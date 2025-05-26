// Configuration
const CHUNKS_DIR = 'histogram_chunks';
const CHUNK_SIZE = 1000;

// Distance Metrics
const METRICS = {
    HELLINGER: 'hellinger',
    L2: 'l2'
};

// State
let allImages = [];
let currentImage = null;
let userHistogram = null;
let isDragging = false;
let lastDragPosition = null;
let totalChunks = 0;
let loadedChunks = 0;
let globalHistogramMax = 0;
let currentMetric = METRICS.HELLINGER;

// DOM Elements
const loadingScreen = document.getElementById('loading-screen');
const appContainer = document.getElementById('app-container');
const displayImage = document.getElementById('display-image');
const imageInfo = document.getElementById('image-info');
const histogramCanvas = document.getElementById('histogram-canvas');
const ctx = histogramCanvas.getContext('2d');
const distanceDisplay = document.getElementById('distance-display');
const randomBtn = document.getElementById('random-btn');
const resetBtn = document.getElementById('reset-btn');
const loadingStatus = document.getElementById('loading-status');
const progressBar = document.getElementById('progress-bar');
const metricSelect = document.getElementById('metric-select');

// Constants for log scale
const LOG_EPSILON = 1e-9;
const LOG_MIN = Math.log10(LOG_EPSILON); // -9
const LOG_MAX = 0; // log10(1) = 0

// Initialize
async function init() {
    // Setup canvas
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Setup event listeners
    histogramCanvas.addEventListener('mousedown', startDrag);
    histogramCanvas.addEventListener('mousemove', dragHistogram);
    histogramCanvas.addEventListener('mouseup', endDrag);
    histogramCanvas.addEventListener('mouseleave', endDrag);
    randomBtn.addEventListener('click', loadRandomImage);
    resetBtn.addEventListener('click', resetHistogram);
    metricSelect.addEventListener('change', (e) => {
        currentMetric = e.target.value;
        updateDistance();
    });

    // Load data
    totalChunks = await detectChunkCount();
    if (totalChunks === 0) {
        loadingStatus.textContent = 'Error: No data files found';
        return;
    }

    await loadAllChunks();

    // Start app
    loadingScreen.style.display = 'none';
    appContainer.style.display = 'block';
    loadRandomImage();

    resizeCanvas();
}

// Data loading functions
async function detectChunkCount() {
    let count = 0;
    while (true) {
        try {
            const test = await fetch(`${CHUNKS_DIR}/chunk_${count.toString().padStart(4, '0')}.json`);
            if (!test.ok) break;
            count++;
            if (count > 9999) break;
        } catch {
            break;
        }
    }
    return count;
}

async function loadAllChunks() {
    for (let i = 0; i < totalChunks; i++) {
        try {
            const chunkName = `chunk_${i.toString().padStart(4, '0')}.json`;
            const response = await fetch(`${CHUNKS_DIR}/${chunkName}`);

            if (!response.ok) continue;

            const chunkData = await response.json();

            for (const [relPath, imgData] of Object.entries(chunkData)) {
                const currentMax = Math.max(...imgData.histogram);
                if (currentMax > globalHistogramMax) {
                    globalHistogramMax = currentMax;
                }

                allImages.push({
                    path: relPath,
                    img_path: imgData.img_path,
                    img_shape: imgData.img_shape,
                    histogram: imgData.histogram,
                    bins: imgData.bins
                });
            }

            loadedChunks++;
            updateProgress();

            if (i % 5 === 0) await new Promise(r => setTimeout(r, 0));

        } catch (error) {
            console.error(`Error loading chunk ${i}:`, error);
        }
    }
    console.log("Global histogram max:", globalHistogramMax);
}

function updateProgress() {
    const percent = Math.round((loadedChunks / totalChunks) * 100);
    progressBar.style.width = `${percent}%`;
    loadingStatus.textContent = `Loaded ${loadedChunks} of ${totalChunks} chunks (${allImages.length} images)`;
}

// Image display functions
function loadRandomImage() {
    if (allImages.length === 0) return;

    const randomIndex = Math.floor(Math.random() * allImages.length);
    currentImage = allImages[randomIndex];

    displayImage.src = `wikiart/${currentImage.path}`;
    imageInfo.textContent = `${currentImage.path} (${currentImage.img_shape[1]}×${currentImage.img_shape[0]})`;

    userHistogram = [...currentImage.histogram];
    drawHistogram();
    updateDistance();
}

// Histogram functions
function resizeCanvas() {
    histogramCanvas.width = histogramCanvas.offsetWidth;
    histogramCanvas.height = histogramCanvas.offsetHeight;
    if (currentImage) drawHistogram();
}

function drawHistogram() {
    if (!currentImage || !userHistogram) return;

    ctx.clearRect(0, 0, histogramCanvas.width, histogramCanvas.height);

    const binCount = userHistogram.length;
    const canvasWidth = histogramCanvas.width;
    const canvasHeight = histogramCanvas.height;
    const displayBinCount = Math.min(binCount, canvasWidth);
    const binRatio = binCount / displayBinCount;
    const logRange = LOG_MAX - LOG_MIN;

    // Draw user histogram (log scale)
    ctx.fillStyle = 'rgba(0, 0, 255, 0.5)';
    for (let i = 0; i < displayBinCount; i++) {
        const startBin = Math.floor(i * binRatio);
        const endBin = Math.floor((i + 1) * binRatio);
        let logSum = 0;
        let validCount = 0;

        for (let j = startBin; j < endBin; j++) {
            const value = userHistogram[j];
            if (value > 0) {
                logSum += Math.log10(value + LOG_EPSILON);
                validCount++;
            }
        }

        const avgLog = validCount > 0 ? logSum / validCount : LOG_MIN;
        const normalized = (avgLog - LOG_MIN) / logRange;
        const barHeight = normalized * canvasHeight;

        ctx.fillRect(
            i * (canvasWidth / displayBinCount),
            canvasHeight - barHeight,
            canvasWidth / displayBinCount,
            barHeight
        );
    }

    // Draw original histogram (log scale)
    ctx.fillStyle = 'rgba(255, 0, 0, 0.5)';
    for (let i = 0; i < displayBinCount; i++) {
        const startBin = Math.floor(i * binRatio);
        const endBin = Math.floor((i + 1) * binRatio);
        let logSum = 0;
        let validCount = 0;

        for (let j = startBin; j < endBin; j++) {
            const value = currentImage.histogram[j];
            if (value > 0) {
                logSum += Math.log10(value + LOG_EPSILON);
                validCount++;
            }
        }

        const avgLog = validCount > 0 ? logSum / validCount : LOG_MIN;
        const normalized = (avgLog - LOG_MIN) / logRange;
        const barHeight = normalized * canvasHeight;

        ctx.fillRect(
            i * (canvasWidth / displayBinCount),
            canvasHeight - barHeight,
            canvasWidth / displayBinCount,
            barHeight
        );
    }
}

// Interaction functions
function startDrag(e) {
    isDragging = true;
    lastDragPosition = getCanvasPosition(e);
    updateHistogram(e);
}

function dragHistogram(e) {
    if (isDragging) {
        const currentPos = getCanvasPosition(e);
        if (lastDragPosition) {
            interpolateHistogram(lastDragPosition, currentPos);
        }
        lastDragPosition = currentPos;
        updateHistogram(e);
    }
}

function endDrag() {
    isDragging = false;
    lastDragPosition = null;
    updateDistance();
}

function getCanvasPosition(e) {
    const rect = histogramCanvas.getBoundingClientRect();
    return {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
    };
}

function interpolateHistogram(startPos, endPos) {
    const binCount = userHistogram.length;
    const displayBinCount = Math.min(binCount, histogramCanvas.width);
    const binWidth = histogramCanvas.width / displayBinCount;

    const startBin = Math.floor(startPos.x / binWidth);
    const endBin = Math.floor(endPos.x / binWidth);

    if (startBin === endBin) return;

    const minBin = Math.min(startBin, endBin);
    const maxBin = Math.max(startBin, endBin);

    // Convert mouse Y to logarithmic scale then back to linear
    const logRange = LOG_MAX - LOG_MIN;

    // Start position conversion
    const startNormY = 1 - (startPos.y / histogramCanvas.height);
    const startLogValue = LOG_MIN + (startNormY * logRange);
    const startValue = Math.pow(10, startLogValue) - LOG_EPSILON;

    // End position conversion
    const endNormY = 1 - (endPos.y / histogramCanvas.height);
    const endLogValue = LOG_MIN + (endNormY * logRange);
    const endValue = Math.pow(10, endLogValue) - LOG_EPSILON;

    // Update bins between positions
    for (let i = minBin; i <= maxBin; i++) {
        const ratio = (i - minBin) / (maxBin - minBin);
        const interpolatedValue = startValue + (endValue - startValue) * ratio;

        const binRatio = binCount / displayBinCount;
        const startBinIdx = Math.floor(i * binRatio);
        const endBinIdx = Math.floor((i + 1) * binRatio);

        for (let j = startBinIdx; j < endBinIdx; j++) {
            userHistogram[j] = Math.min(globalHistogramMax, Math.max(0, interpolatedValue));
        }
    }

    drawHistogram();
}

function updateHistogram(e) {
    const rect = histogramCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const binCount = userHistogram.length;
    const displayBinCount = Math.min(binCount, histogramCanvas.width);
    const binWidth = histogramCanvas.width / displayBinCount;

    // Convert mouse Y to logarithmic scale then back to linear
    const logRange = LOG_MAX - LOG_MIN;
    const normalizedY = 1 - (y / histogramCanvas.height);
    const logValue = LOG_MIN + (normalizedY * logRange);
    const linearValue = Math.pow(10, logValue) - LOG_EPSILON;

    // Update the bucket under the mouse
    const clickedDisplayBin = Math.floor(x / binWidth);
    const startBucket = Math.floor(clickedDisplayBin * (binCount / displayBinCount));
    const endBucket = Math.floor((clickedDisplayBin + 1) * (binCount / displayBinCount));

    for (let i = startBucket; i < endBucket; i++) {
        userHistogram[i] = Math.min(globalHistogramMax, Math.max(0, linearValue));
    }

    // Interpolate hidden buckets if needed
    if (binCount > displayBinCount) {
        const visibleValues = [];
        for (let i = 0; i < displayBinCount; i++) {
            const bucketStart = Math.floor(i * (binCount / displayBinCount));
            visibleValues.push({
                pos: (i + 0.5) / displayBinCount,
                value: userHistogram[bucketStart]
            });
        }

        for (let i = 0; i < binCount; i++) {
            const normalizedPos = i / binCount;
            let left = visibleValues[0];
            let right = visibleValues[visibleValues.length - 1];

            for (const v of visibleValues) {
                if (v.pos <= normalizedPos) left = v;
                if (v.pos >= normalizedPos) {
                    right = v;
                    break;
                }
            }

            const t = (normalizedPos - left.pos) / (right.pos - left.pos);
            userHistogram[i] = left.value + t * (right.value - left.value);
        }
    }

    drawHistogram();
}

function resetHistogram() {
    if (!currentImage) return;
    userHistogram = [...currentImage.histogram];
    drawHistogram();
    updateDistance();
}

// Distance calculation functions
function hellingerDistance(hist1, hist2) {
    const sum1 = hist1.reduce((a, b) => a + b, 0);
    const sum2 = hist2.reduce((a, b) => a + b, 0);
    let sum = 0;

    for (let i = 0; i < hist1.length; i++) {
        const p = hist1[i] / sum1;
        const q = hist2[i] / sum2;
        sum += (Math.sqrt(p) - Math.sqrt(q)) ** 2;
    }
    return Math.sqrt(sum) / Math.sqrt(2);
}

function l2Distance(hist1, hist2) {
    let sum = 0;
    for (let i = 0; i < hist1.length; i++) {
        sum += (hist1[i] - hist2[i]) ** 2;
    }
    return Math.sqrt(sum);
}

function getDistance(hist1, hist2, metric = currentMetric) {
    switch (metric) {
        case METRICS.HELLINGER:
            return hellingerDistance(hist1, hist2);
        case METRICS.L2:
            return l2Distance(hist1, hist2);
        default:
            throw new Error(`Unknown metric: ${metric}`);
    }
}

function updateDistance() {
    if (!currentImage || !userHistogram) return;

    // Calculate distance for current image
    const distance = getDistance(userHistogram, currentImage.histogram);
    distanceDisplay.textContent = `${currentMetric.toUpperCase()} Distance: ${distance.toFixed(4)}`;

    // Find closest image
    let minDistance = Infinity;
    let closestImage = null;

    for (const img of allImages) {
        const d = getDistance(userHistogram, img.histogram);
        if (d < minDistance) {
            minDistance = d;
            closestImage = img;
        }
    }

    // Update display if closer image found
    if (closestImage && closestImage !== currentImage) {
        currentImage = closestImage;
        displayImage.src = `wikiart/${currentImage.path}`;
        imageInfo.textContent = `Closest match (${currentMetric}): ${currentImage.path} (${minDistance.toFixed(4)})`;
    }

    drawHistogram();
}

// Error handling
displayImage.onerror = function () {
    this.src = '';
    imageInfo.textContent = `Image not found: wikiart/${currentImage.path}`;
};

// Start the application
window.addEventListener('DOMContentLoaded', init);