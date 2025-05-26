const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const WIDTH = canvas.width;
const HEIGHT = canvas.height;

let allRatios = {};
let imageDetails = {};

let currentClass = null;
let currentBucket = 50;
let currentImages = [];
let currentImageIdx = 0;

function normalizePath(p) {
  const cleanPath = p.replace(/\\/g, "/");
  if (cleanPath.startsWith("wikiart/")) {
    return cleanPath;
  }
  return "wikiart/" + cleanPath;
}

function loadCurrentImages() {
  if (!allRatios[currentClass]) return;
  currentImages = allRatios[currentClass][currentBucket] || [];
  currentImageIdx = 0;

  console.log("🔍 loadCurrentImages()");
  console.log(" - currentClass:", currentClass);
  console.log(" - currentBucket:", currentBucket);
  console.log(" - currentImages:", currentImages);
}

function drawImage() {
  ctx.clearRect(0, 0, WIDTH, HEIGHT);

  if (!currentImages.length) {
    ctx.fillText("No images in this bucket", 50, 50);
    console.warn("⚠️ No images available in current bucket:", currentBucket);
    return;
  }

  const imgPath = normalizePath(currentImages[currentImageIdx]);
  const img = new Image();

  console.log("🎯 drawImage()");
  console.log(" - imgPath:", imgPath);
  console.log(" - currentImageIdx:", currentImageIdx);

  img.onload = () => {
    console.log("✅ Image loaded:", img.width, "x", img.height);

    const scale = Math.min(WIDTH / img.width, HEIGHT / img.height);
    const scaledWidth = img.width * scale;
    const scaledHeight = img.height * scale;

    const offsetX = (WIDTH - scaledWidth) / 2;
    const offsetY = (HEIGHT - scaledHeight) / 2;

    ctx.drawImage(img, offsetX, offsetY, scaledWidth, scaledHeight);

    const detections = imageDetails[imgPath]?.detections || [];
    console.log("📦 Detections for this image:", detections.length);

    for (let det of detections) {
      if (det.class_name !== currentClass) continue;
      const [x1, y1, x2, y2] = det.box_coords.map(v => v * scale);
      const sx = x1 + offsetX;
      const sy = y1 + offsetY;
      const ex = x2 + offsetX;
      const ey = y2 + offsetY;

      ctx.strokeStyle = 'red';
      ctx.lineWidth = 2;
      ctx.strokeRect(sx, sy, ex - sx, ey - sy);
      ctx.fillStyle = 'red';
      ctx.fillText(`${det.class_name} (${det.confidence.toFixed(2)})`, sx, sy - 5);
    }
  };

  img.onerror = () => {
    console.error("❌ Failed to load image:", imgPath);
  };

  img.src = imgPath;
}

function loadJSONs() {
  Promise.all([
    fetch("ratio/").then(r => r.text()),
    fetch("details/").then(r => r.text())
  ]).then(([ratioHTML, detailHTML]) => {
    const ratioFiles = [...ratioHTML.matchAll(/href="([^"]+\.json)"/g)].map(m => m[1]);
    const detailFiles = [...detailHTML.matchAll(/href="([^"]+\.json)"/g)].map(m => m[1]);

    Promise.all([
      ...ratioFiles.map(f => fetch("ratio/" + f).then(r => r.json()).then(data => ({ f, data }))),
      ...detailFiles.map(f => fetch("details/" + f).then(r => r.json()).then(data => ({ f, data })))
    ]).then(all => {
      all.forEach(({ f, data }) => {
        if (f.startsWith("ratio/") || ratioFiles.includes(f)) {
          const key = f.replace(".json", "").split("/").pop();
          allRatios[key] = data[key];
        } else {
          for (let img in data) {
            imageDetails["wikiart/" + img] = data[img];
          }
        }
      });

      const select = document.getElementById("classSelect");
      Object.keys(allRatios).forEach(className => {
        const option = document.createElement("option");
        option.value = className;
        option.text = className;
        select.appendChild(option);
      });

      currentClass = select.value;
      loadCurrentImages();
      drawImage();
    });
  });
}

document.getElementById("classSelect").addEventListener("change", e => {
  currentClass = e.target.value;
  loadCurrentImages();
  drawImage();
});

document.addEventListener("keydown", e => {
  if (e.key === "ArrowRight") {
    currentImageIdx = (currentImageIdx + 1) % currentImages.length;
    drawImage();
  } else if (e.key === "ArrowLeft") {
    currentImageIdx = (currentImageIdx - 1 + currentImages.length) % currentImages.length;
    drawImage();
  } else if (e.key === "ArrowUp") {
    currentBucket = Math.min(99, currentBucket + 1);
    loadCurrentImages();
    drawImage();
  } else if (e.key === "ArrowDown") {
    currentBucket = Math.max(0, currentBucket - 1);
    loadCurrentImages();
    drawImage();
  }
});

window.onload = loadJSONs;
