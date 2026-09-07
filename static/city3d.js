(() => {
  const buildings = window.CITY_BUILDINGS || [];
  const center = window.CITY_CENTER || { lat: 12.9166, lng: 77.6229 };
  Cesium.Ion.defaultAccessToken = '';
  const viewer = new Cesium.Viewer('city3d-container', { animation: false, timeline: false, geocoder: false, homeButton: false, sceneModePicker: false, baseLayerPicker: false, navigationHelpButton: false, infoBox: false, selectionIndicator: false });
  viewer.imageryLayers.removeAll();
  viewer.imageryLayers.addImageryProvider(new Cesium.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' }));
  viewer.scene.globe.depthTestAgainstTerrain = false;
  const entities = [];
  let selected;
  const colorFor = building => building.floors > building.sanctioned_floors ? Cesium.Color.ORANGE.withAlpha(.72) : Cesium.Color.fromCssColorString('#63d9ff').withAlpha(.62);
  const footprintPositions = footprint => Cesium.Cartesian3.fromDegreesArray(footprint.flatMap(point => [point[1], point[0]]));
  const heightScale = 2.2;
  const panel = document.getElementById('city3d-panel');
  const data = document.getElementById('selected-data');
  function selectBuilding(building) {
    selected = building;
    document.getElementById('selected-name').textContent = building.building_name;
    document.getElementById('selected-copy').textContent = `${building.address} · ${building.usage}`;
    data.innerHTML = `<div><span>ULPIN</span><b>${building.ulpin}</b></div><div><span>Floors</span><b>${building.floors} observed / ${building.sanctioned_floors} sanctioned</b></div><div><span>Height</span><b>${building.height} m</b></div><div><span>Map record</span><a href="/api/buildings/${building.id}" target="_blank">Open JSON</a></div><div><span>Detail view</span><a href="/view/${building.id}">Open building</a></div>`;
    panel.classList.add('has-selection');
    entities.forEach(item => { item.polygon.material = item.building.id === building.id ? Cesium.Color.fromCssColorString('#ffffff').withAlpha(.9) : colorFor(item.building); });
  }
  buildings.forEach(building => {
    const footprint = building.footprint || [[building.lat, building.lng]];
    if (footprint.length < 3) return;
    const positions = footprintPositions(footprint);
    for (let floor = 1; floor <= building.floors; floor += 1) {
      const base = (floor - 1) * building.floor_height * heightScale;
      const top = floor * building.floor_height * heightScale - 0.18;
      const entity = viewer.entities.add({ name: `${building.building_name} · Floor ${floor}`, polygon: { hierarchy: positions, height: base, extrudedHeight: top, material: colorFor(building), outline: true, outlineColor: Cesium.Color.WHITE.withAlpha(.35), outlineWidth: 1 }, properties: { buildingId: building.id, floor } });
      entities.push({ entity, polygon: entity.polygon, building });
    }
  });
  viewer.screenSpaceEventHandler.setInputAction(click => { const picked = viewer.scene.pick(click.position); if (!picked || !picked.id || !picked.id.properties || !picked.id.properties.buildingId) return; const id = picked.id.properties.buildingId.getValue(); const item = entities.find(entry => entry.building.id === id); if (item) selectBuilding(item.building); }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  const points = buildings.flatMap(building => building.footprint || [[building.lat, building.lng]]);
  const west = Math.min(...points.map(point => point[1])); const east = Math.max(...points.map(point => point[1]));
  const south = Math.min(...points.map(point => point[0])); const north = Math.max(...points.map(point => point[0]));
  const cityRectangle = Cesium.Rectangle.fromDegrees(west, south, east, north);
  const frame3d = () => viewer.camera.flyTo({ destination: cityRectangle, orientation: { heading: 0, pitch: Cesium.Math.toRadians(-48), roll: 0 }, duration: .8 });
  const frameTop = () => viewer.camera.flyTo({ destination: cityRectangle, orientation: { heading: 0, pitch: Cesium.Math.toRadians(-90), roll: 0 }, duration: .8 });
  if (points.length) frame3d(); else viewer.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(center.lng, center.lat, 1200) });
  document.getElementById('mode3d').addEventListener('click', frame3d);
  document.getElementById('modeTop').addEventListener('click', frameTop);
})();
