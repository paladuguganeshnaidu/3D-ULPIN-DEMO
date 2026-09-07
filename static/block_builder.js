(() => {
  const floorInput = document.getElementById('floor-count');
  const unitInput = document.getElementById('unit-count');
  const heightInput = document.getElementById('floor-height');
  const volume = document.getElementById('block-volume');
  const scene = document.getElementById('block-scene');
  const floorsText = document.getElementById('preview-floors');
  const flatsText = document.getElementById('preview-flats');
  const heightText = document.getElementById('preview-height');
  const refresh = () => {
    const floors = Math.max(1, Number(floorInput.value) || 1);
    const units = Math.max(1, Number(unitInput.value) || 1);
    const height = Math.max(1, Number(heightInput.value) || 1);
    floorsText.textContent = floors;
    flatsText.textContent = floors * units;
    heightText.textContent = `${(floors * height).toFixed(1)} m`;
    volume.replaceChildren();
    for (let floor = floors; floor >= 1; floor -= 1) {
      const band = document.createElement('button');
      band.type = 'button';
      band.className = 'floor-band';
      band.style.setProperty('--floor-index', floor);
      band.innerHTML = `<span>F${String(floor).padStart(2, '0')}</span><small>${units} flats</small>`;
      band.title = `Floor ${floor}: ${units} flats`;
      band.addEventListener('click', () => { document.querySelectorAll('.floor-band').forEach(item => item.classList.remove('selected')); band.classList.add('selected'); });
      volume.appendChild(band);
    }
  };
  [floorInput, unitInput, heightInput].forEach(input => input.addEventListener('input', refresh));
  document.getElementById('preview-3d').addEventListener('click', () => { scene.classList.remove('top-mode'); document.getElementById('preview-3d').classList.add('active'); document.getElementById('preview-top').classList.remove('active'); });
  document.getElementById('preview-top').addEventListener('click', () => { scene.classList.add('top-mode'); document.getElementById('preview-top').classList.add('active'); document.getElementById('preview-3d').classList.remove('active'); });
  const mapsUrl = document.querySelector('[data-resolve-url]');
  const latInput = document.getElementById('latitude');
  const lngInput = document.getElementById('longitude');
  let timer;
  mapsUrl.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(async () => { if (!mapsUrl.value) return; mapsUrl.setCustomValidity('Resolving Maps link...'); try { const response = await fetch('/api/maps/resolve?url=' + encodeURIComponent(mapsUrl.value)); const result = await response.json(); if (!result.ok) throw new Error(result.error); latInput.value = result.lat; lngInput.value = result.lng; mapsUrl.setCustomValidity(''); } catch (error) { mapsUrl.setCustomValidity(error.message); } }, 350); });
  refresh();
})();
