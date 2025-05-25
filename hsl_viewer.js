const grid = document.getElementById('grid');
const hueSlider = document.getElementById('hueSlider');
const hueValue = document.getElementById('hueValue');

const GRID_SIZE = 16;
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

function hslDistance(h1, s1, l1, h2, s2, l2) {
  const dh = Math.min(Math.abs(h1 - h2), 360 - Math.abs(h1 - h2)) / 180;
  const ds = Math.abs(s1 - s2);
  const dl = Math.abs(l1 - l2);
  return dh + ds + dl;
}

function renderGrid(targetHue) {
  grid.innerHTML = '';
  const cells = [];

  for (let y = 0; y < GRID_SIZE; y++) {
    for (let x = 0; x < GRID_SIZE; x++) {
      const s = x / (GRID_SIZE - 1);
      const l = 1 - y / (GRID_SIZE - 1);
      cells.push({ h: targetHue, s, l });
    }
  }

  const maxDistanceThreshold = 0.6; // Adjust this value to tune matching strictness

  for (const { h, s, l } of cells) {
    const match = allImages.reduce((acc, img) => {
      const dist = hslDistance(h, s, l, img.h, img.s, img.v);
      return dist < acc.dist ? { img, dist } : acc;
    }, { img: null, dist: Infinity });

    const div = document.createElement('div');
    div.className = 'tile';

    if (match.dist < maxDistanceThreshold) {
      const img = document.createElement('img');
      img.src = match.img.path;
      img.title = `H:${match.img.h} S:${match.img.s} V:${match.img.v}`;
      div.appendChild(img);
    }

    grid.appendChild(div);
  }
}

async function loadAllJsons() {
  for (const file of JSON_FILES) {
    try {
      const res = await fetch(`mean_colors/${file}`);
      const json = await res.json();
      allImages.push(...Object.values(json));
    } catch (e) {
      console.warn(`Failed to load ${file}`);
    }
  }
  renderGrid(parseInt(hueSlider.value));
}

hueSlider.addEventListener('input', () => {
  const hue = parseInt(hueSlider.value);
  hueValue.textContent = hue;
  renderGrid(hue);
});

loadAllJsons();
