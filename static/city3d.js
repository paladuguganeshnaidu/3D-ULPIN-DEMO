(() => {
  const buildings = window.CITY_BUILDINGS || [];
  const center = window.CITY_CENTER || { lat: 12.9166, lng: 77.6229 };
  Cesium.Ion.defaultAccessToken = '';
  const viewer = new Cesium.Viewer('city3d-container', { animation: false, timeline: false, geocoder: false, homeButton: false, sceneModePicker: false, baseLayerPicker: false, navigationHelpButton: false, infoBox: false, selectionIndicator: false, terrainProvider: new Cesium.EllipsoidTerrainProvider() });
  viewer.imageryLayers.removeAll();
  viewer.imageryLayers.addImageryProvider(new Cesium.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' }));
  viewer.scene.globe.depthTestAgainstTerrain = false;
  const entities = [];
  const panel = document.getElementById('city3d-panel');
  const editor = document.getElementById('floor-editor');
  const floorSelect = document.getElementById('floor-select');
  const data = document.getElementById('selected-data');
  let selectedBuilding;
  let selectedUnits = [];
  let selectedFloor;
  const colorFor = building => building.floors > building.sanctioned_floors ? Cesium.Color.ORANGE.withAlpha(.72) : Cesium.Color.fromCssColorString('#63d9ff').withAlpha(.62);
  const footprintPositions = footprint => Cesium.Cartesian3.fromDegreesArray(footprint.flatMap(point => [point[1], point[0]]));
  const unitForFloor = floor => selectedUnits.find(unit => unit.floor_no === floor) || selectedUnits.find(unit => unit.floor_no === 1);
  function fillEditor(unit, floor) {
    selectedFloor = floor;
    const details = unit?.details || {};
    document.getElementById('record-latitude').value = details.latitude ?? selectedBuilding.lat;
    document.getElementById('record-longitude').value = details.longitude ?? selectedBuilding.lng;
    document.getElementById('record-width').value = details.width ?? unit?.width ?? selectedBuilding.footprint_w;
    document.getElementById('record-depth').value = details.depth ?? unit?.depth ?? selectedBuilding.footprint_d;
    document.getElementById('record-owner').value = details.owner_name ?? unit?.owner_name ?? '';
    document.getElementById('record-legal').value = unit?.legal_status || 'REGISTERED';
    document.getElementById('save-status').textContent = '';
  }
  function chooseFloor(floor) {
    const unit = unitForFloor(Number(floor));
    selectedFloor = Number(floor);
    fillEditor(unit, selectedFloor);
    entities.forEach(item => { const material = item.building.id === selectedBuilding.id && item.floor === selectedFloor ? Cesium.Color.WHITE.withAlpha(.94) : item.building.id === selectedBuilding.id ? Cesium.Color.fromCssColorString('#63d9ff').withAlpha(.78) : colorFor(item.building); item.polygon.material = material; item.box.material = material; });
  }
  async function selectBuilding(building, floor = 1) {
    selectedBuilding = building;
    document.getElementById('selected-name').textContent = building.building_name;
    document.getElementById('selected-copy').textContent = `${building.address} · Fixed at ${building.lat.toFixed(6)}, ${building.lng.toFixed(6)}`;
    data.innerHTML = `<div><span>Base ULPIN</span><b>${building.ulpin}</b></div><div><span>Fixed coordinates</span><b>${building.lat.toFixed(6)}, ${building.lng.toFixed(6)}</b></div><div><span>Footprint</span><b>${building.footprint_w} × ${building.footprint_d} m</b></div><div><span>Floors</span><b>${building.floors} observed / ${building.sanctioned_floors} sanctioned</b></div><div><span>Record</span><a href="/api/buildings/${building.id}" target="_blank">Open public JSON</a> · <a href="/view/${building.id}">3D detail</a></div>`;
    panel.classList.add('has-selection');
    try {
      const response = await fetch(`/api/buildings/${building.id}`);
      const result = await response.json();
      selectedUnits = result.units || [];
    } catch (error) { selectedUnits = []; }
    floorSelect.replaceChildren();
    for (let number = 1; number <= building.floors; number += 1) {
      const option = document.createElement('option'); option.value = number; option.textContent = `Floor ${String(number).padStart(2, '0')} · ${selectedUnits.filter(unit => unit.floor_no === number).length || 0} flats`; floorSelect.appendChild(option);
    }
    floorSelect.value = floor;
    editor.classList.remove('hidden');
    chooseFloor(floor);
  }
  buildings.forEach(building => {
    const footprint = building.footprint || [];
    if (footprint.length < 3) return;
    const positions = footprintPositions(footprint);
    for (let floor = 1; floor <= building.floors; floor += 1) {
      const base = (floor - 1) * Number(building.floor_height);
      const top = floor * Number(building.floor_height) - 0.08;
      const entity = viewer.entities.add({ name: `${building.building_name} · Floor ${floor}`, position: Cesium.Cartesian3.fromDegrees(building.lng, building.lat, base + building.floor_height / 2), box: { dimensions: new Cesium.Cartesian3(building.footprint_w, building.footprint_d, Math.max(building.floor_height - .08, .2)), heightReference: Cesium.HeightReference.NONE, material: colorFor(building), outline: true, outlineColor: Cesium.Color.WHITE.withAlpha(.6), outlineWidth: 1 }, polygon: { hierarchy: positions, height: base, extrudedHeight: top, heightReference: Cesium.HeightReference.NONE, extrudedHeightReference: Cesium.HeightReference.NONE, material: colorFor(building), outline: true, outlineColor: Cesium.Color.WHITE.withAlpha(.45), outlineWidth: 1 }, properties: { buildingId: building.id, floor } });
      entities.push({ entity, polygon: entity.polygon, box: entity.box, building, floor });
    }
  });
  viewer.screenSpaceEventHandler.setInputAction(click => { const picked = viewer.scene.pick(click.position); if (!picked?.id?.properties?.buildingId) return; const id = picked.id.properties.buildingId.getValue(); const floor = picked.id.properties.floor.getValue(); const item = entities.find(entry => entry.building.id === id); if (item) selectBuilding(item.building, floor); }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  floorSelect.addEventListener('change', () => chooseFloor(floorSelect.value));
  document.getElementById('save-floor').addEventListener('click', async () => {
    if (!selectedBuilding) return;
    const status = document.getElementById('save-status'); status.textContent = 'Saving JSON record...';
    const unit = unitForFloor(selectedFloor); const unitCode = unit?.unit_code || `F${String(selectedFloor).padStart(2, '0')}-U01`;
    const payload = { floor_no: selectedFloor, unit_code: unitCode, latitude: document.getElementById('record-latitude').value, longitude: document.getElementById('record-longitude').value, width: document.getElementById('record-width').value, depth: document.getElementById('record-depth').value, owner_name: document.getElementById('record-owner').value, legal_status: document.getElementById('record-legal').value };
    try { const response = await fetch(`/api/buildings/${selectedBuilding.id}/floor-record`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); const result = await response.json(); if (!response.ok || !result.ok) throw new Error(result.error || 'Save failed'); status.textContent = 'Saved to the protected JSON record.'; const index = selectedUnits.findIndex(item => item.unit_code === unitCode); if (index >= 0) selectedUnits[index] = result.unit; } catch (error) { status.textContent = error.message.includes('Unexpected') ? 'Sign in as a surveyor or admin to save.' : error.message; }
  });
  const points = buildings.flatMap(building => building.footprint || [[building.lat, building.lng]]);
  const west = Math.min(...points.map(point => point[1])); const east = Math.max(...points.map(point => point[1])); const south = Math.min(...points.map(point => point[0])); const north = Math.max(...points.map(point => point[0]));
  const cityCenter = { lng: (west + east) / 2, lat: (south + north) / 2 };
  const spanMeters = Math.max((east - west) * 111320, (north - south) * 111320);
  const cameraHeight = Math.max(spanMeters * 1.05, 110);
  const frame3d = () => viewer.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(cityCenter.lng, cityCenter.lat, cameraHeight), orientation: { heading: 0, pitch: Cesium.Math.toRadians(-52), roll: 0 }, duration: .8 });
  const frameTop = () => viewer.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(cityCenter.lng, cityCenter.lat, cameraHeight), orientation: { heading: 0, pitch: Cesium.Math.toRadians(-90), roll: 0 }, duration: .8 });
  if (entities.length) frame3d(); else viewer.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(center.lng, center.lat, 1000) });
  document.getElementById('mode3d').addEventListener('click', frame3d);
  document.getElementById('modeTop').addEventListener('click', frameTop);
})();
