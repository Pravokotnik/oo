const grid = document.getElementById('grid');
const hueSlider = document.getElementById('hueSlider');
const hueValue = document.getElementById('hueValue');

const GRID_SIZE = 16;
const BUCKET_GRANULARITY = 16;

const JSON_FILES = [
  'Abstract_Expressionism.json', 'Art_Nouveau_Modern.json', 'Baroque.json',
  'Cubism.json', 'Expressionism.json', 'Fauvism.json', 'Impressionism.json',
  'Minimalism.json', 'Pop_Art.json', 'Post_Impressionism.json', 'Realism.json',
  'Renaissance.json', 'Romanticism.json', 'Surrealism.json', 'Symbolism.json',
  'Action_painting.json', 'Color_Field_Painting.json', 'Conceptual_Art.json',
  'Contemporary_Realism.json', 'Constructivism.json', 'Dada.json',
  'Divisionism.json', 'High_Renaissance.json', 'New_Realism.json',
  'Photorealism.json', 'Rococo.json', 'Suprematism.json'
];

let allImages = [];
let colorBuckets = new Map();

// Convert HSV (h in degrees, s and v in 0-1) to RGB (0-255)
function hsvToRgb(h, s, v) {
  let c = v * s;
  let hp = h / 60;
  let x = c * (1 - Math.abs(hp % 2 - 1));
  let r = 0, g = 0, b = 0;

  if (hp >= 0 && hp < 1) [r, g, b] = [c, x, 0];
  else if (hp < 2) [r, g, b] = [x, c, 0];
  else if (hp < 3) [r, g, b] = [0, c, x];
  else if (hp < 4) [r, g, b] = [0, x, c];
  else if (hp < 5) [r, g, b] = [x, 0, c];
  else if (hp <= 6) [r, g, b] = [c, 0, x];

  let m = v - c;
  return {
    r: Math.min(255, Math.round((r + m) * 255)),
    g: Math.min(255, Math.round((g + m) * 255)),
    b: Math.min(255, Math.round((b + m) * 255))
  };
}

// Convert RGB to bucket key string
function rgbToBucketKey(r, g, b) {
  let br = Math.min(Math.floor(r * BUCKET_GRANULARITY / 256), BUCKET_GRANULARITY - 1);
  let bg = Math.min(Math.floor(g * BUCKET_GRANULARITY / 256), BUCKET_GRANULARITY - 1);
  let bb = Math.min(Math.floor(b * BUCKET_GRANULARITY / 256), BUCKET_GRANULARITY - 1);
  return `${br},${bg},${bb}`;
}

// Build buckets from allImages array using HSV -> RGB -> bucket
function buildColorBuckets() {
  const buckets = new Map();
  for (const entry of allImages) {
    // Each entry has h, s, v, and path
    const rgb = hsvToRgb(entry.h, entry.s, entry.v);
    const bucketKey = rgbToBucketKey(rgb.r, rgb.g, rgb.b);
    if (!buckets.has(bucketKey)) buckets.set(bucketKey, []);
    buckets.get(bucketKey).push(entry.path);
  }
  return buckets;
}

// Given target hue(0..360), saturation(0..1), lightness(0..1)
// convert to RGB bucket, then pick a random image from that bucket
function findClosestImage(targetH, targetS, targetL) {
  // Note: The Python code uses colorsys.hls_to_rgb(h, l, s) (HLS order)
  // JS uses HSL, so we convert H, S, L properly.

  function hslToRgb(h, s, l) {
    h /= 360;
    let r, g, b;
    if (s === 0) {
      r = g = b = l;
    } else {
      const hue2rgb = (p, q, t) => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1/6) return p + (q - p) * 6 * t;
        if (t < 1/2) return q;
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
        return p;
      };
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      r = hue2rgb(p, q, h + 1/3);
      g = hue2rgb(p, q, h);
      b = hue2rgb(p, q, h - 1/3);
    }
    return {
      r: Math.round(r * 255),
      g: Math.round(g * 255),
      b: Math.round(b * 255)
    };
  }

  const rgb = hslToRgb(targetH, targetS, targetL);
  const bucketKey = rgbToBucketKey(rgb.r, rgb.g, rgb.b);
  const candidates = colorBuckets.get(bucketKey);

  if (!candidates || candidates.length === 0) return null;

  // Random choice
  return candidates[Math.floor(Math.random() * candidates.length)];
}

function createTile(imagePath) {
  const div = document.createElement('div');
  div.className = 'tile';
  div.onclick = () => {
    window.location.href = "./histogram.html";
  }

  if (imagePath) {
    const img = document.createElement('img');
    img.src = imagePath;
    div.appendChild(img);
  }

  return div;
}

function renderGrid(targetHue) {
  grid.innerHTML = '';
  hueValue.textContent = targetHue;

  for (let row = 0; row < GRID_SIZE; row++) {
    for (let col = 0; col < GRID_SIZE; col++) {
      // Saturation from 0 to 1 along X-axis
      const saturation = col / (GRID_SIZE - 1);
      // Lightness from 1 to 0 along Y-axis
      const lightness = 1 - row / (GRID_SIZE - 1);

      const imagePath = findClosestImage(targetHue, saturation, lightness);
      const tile = createTile(imagePath);
      grid.appendChild(tile);
    }
  }
}

async function loadAllJsons() {
  allImages = [];
  for (const file of JSON_FILES) {
    try {
      const res = await fetch(`mean_colors/${file}`);
      if (!res.ok) {
        console.warn(`Failed to load ${file}`);
        continue;
      }
      const json = await res.json();
      allImages.push(...Object.values(json));
    } catch (e) {
      console.warn(`Error loading ${file}:`, e);
    }
  }
  colorBuckets = buildColorBuckets();
  renderGrid(parseInt(hueSlider.value));
}

hueSlider.addEventListener('input', () => {
  renderGrid(parseInt(hueSlider.value));
});

loadAllJsons();
