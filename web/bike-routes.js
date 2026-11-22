// Standalone infrastructure map. One layer per facility type keeps filtering simple.
(() => {
  const view = document.getElementById("view-routes");
  if (!view) return;

  const colors = {
    "Bike Lane": "#2563eb",
    "Shared-Use Path": "#15803d",
    "Bike Route": "#b45309",
    "Bike Boulevard": "#7e22ce",
    "Bike Lane - Frontage Road": "#be123c",
    "Enhanced Bike Route": "#0e7490",
    "Separated Bike Lane": "#c2410c",
    "OSM cycleway": "#15803d",
    "OSM bicycle street": "#7e22ce",
    "OSM cycle track": "#c2410c",
    "OSM bicycle lane": "#2563eb",
    "OSM shared-lane markings": "#b45309",
    "OSM bicycle route": "#b45309",
    "OSM bicycle permission only": "#64748b"
  };
  const summary = document.getElementById("route-summary");
  const filters = document.getElementById("route-filters");
  const crossingToggle = document.getElementById("route-crossings");
  const stationToggle = document.getElementById("route-stations");
  const wardToggle = document.getElementById("route-wards");
  const reload = document.getElementById("routes-reload");
  const groups = new Map();
  const routeMap = createTucsonMap("routes-map", {
    preferCanvas: true,
    attribution: " · Infrastructure: PAG and OpenStreetMap · Stations: TuGo"
  });
  const inventory = initBikewayCatalog(routeMap, refreshFacilityLayers);
  let crossingLayer;
  let wardLayer;
  let stationLayer;
  let networkBounds;
  let crossingCount = 0;
  let stationCount = 0;
  let loading = false;

  function updateSummary() {
    let segments = 0;
    let miles = 0;
    groups.forEach(group => {
      if (routeMap.hasLayer(group.layer)) {
        segments += group.segments;
        miles += group.miles;
      }
    });
    summary.textContent = `${segments.toLocaleString()} source sections · ${miles.toLocaleString(undefined, { maximumFractionDigits: 1 })} source miles · ${crossingToggle.checked ? crossingCount : 0} crossings · ${stationToggle.checked ? stationCount : 0} TuGo stations`;
  }

  function refreshFacilityLayers() {
    groups.forEach(group => {
      const visible = group.features.filter(inventory.matches);
      group.layer.clearLayers();
      group.layer.addData(visible);
      group.segments = visible.length;
      group.miles = visible.reduce((sum, feature) => sum + (Number(feature.properties.length_miles) || 0), 0);
    });
    updateSummary();
  }

  function setVisible(group, visible) {
    group.checkbox.checked = visible;
    if (visible) group.layer.addTo(routeMap);
    else routeMap.removeLayer(group.layer);
  }

  async function loadData() {
    if (loading) return;
    loading = true;
    reload.disabled = true;
    summary.textContent = "Loading local bike data…";
    const previous = new Map([...groups].map(([type, group]) => [type, group.checkbox.checked]));
    try {
      const response = await fetch(view.dataset.endpoint || "/api/bike-routes", { cache: "no-store" });
      if (!response.ok) throw new Error("Could not load bike infrastructure data.");
      const data = await response.json();
      if (!data.routes?.features?.length) throw new Error("No bikeways found. Import the PAG data locally, then reload.");

      groups.forEach(group => routeMap.removeLayer(group.layer));
      if (crossingLayer) routeMap.removeLayer(crossingLayer);
      if (wardLayer) routeMap.removeLayer(wardLayer);
      wardLayer = drawWards(routeMap, data.wards, undefined, wardToggle.checked);
      if (stationLayer) routeMap.removeLayer(stationLayer);
      groups.clear();
      filters.replaceChildren();
      const featuresByType = new Map();
      data.routes.features.forEach(feature => {
        const type = feature.properties.facility_type;
        if (!featuresByType.has(type)) featuresByType.set(type, []);
        featuresByType.get(type).push(feature);
      });
      const bounds = L.latLngBounds([]);
      [...featuresByType].sort(([a], [b]) => a.localeCompare(b)).forEach(([type, features]) => {
        const color = colors[type] || "#475569";
        const layer = L.geoJSON(features, {
          renderer: L.canvas({ padding: 0.5 }),
          style: feature => ({ color, weight: feature.properties.source === "osm" ? 2.5 : 3.5,
            opacity: feature.properties.source === "osm" ? .75 : .9,
            dashArray: feature.properties.source === "osm" ? "6 5" : null }),
          onEachFeature: (feature, segment) => {
            const p = feature.properties;
            segment.bindPopup(bikewaySectionPopup(p), { maxWidth: 360 });
          }
        });
        bounds.extend(layer.getBounds());
        const label = document.createElement("label");
        label.className = "route-filter";
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = previous.get(type) ?? true;
        const swatch = document.createElement("span");
        swatch.className = "route-swatch";
        swatch.style.background = color;
        const text = document.createElement("span");
        text.textContent = type;
        label.append(checkbox, swatch, text);
        filters.append(label);
        const group = {
          layer, checkbox, features, segments: features.length,
          miles: features.reduce((total, f) => total + (Number(f.properties.length_miles) || 0), 0)
        };
        groups.set(type, group);
        setVisible(group, checkbox.checked);
        checkbox.onchange = () => {
          setVisible(group, checkbox.checked);
          updateSummary();
        };
      });

      crossingCount = data.crossings.features.length;
      crossingLayer = L.geoJSON(data.crossings, {
        pointToLayer: (feature, latlng) => L.marker(latlng, {
          icon: L.divIcon({
            className: "crossing-marker",
            html: '<span aria-hidden="true">🚦</span>',
            iconSize: [26, 26], iconAnchor: [13, 13]
          }),
          title: [feature.properties.Street, feature.properties.Intersecti].filter(Boolean).join(" / ") || "Push-button crossing"
        }),
        onEachFeature: (feature, marker) => {
          const p = feature.properties;
          marker.bindPopup(`<div class="d">Push-button crossing</div><div>${esc([p.Street, p.Intersecti].filter(Boolean).join(" / "))}</div><div class="s">${esc(p.SignalType || "Signal type unspecified")}</div>`);
        }
      });
      if (crossingToggle.checked) crossingLayer.addTo(routeMap);

      stationCount = data.stations.features.length;
      stationLayer = L.geoJSON(data.stations, {
        pointToLayer: (feature, latlng) => L.marker(latlng, {
          icon: L.divIcon({
            className: "station-marker",
            html: '<span aria-hidden="true">🚲</span>',
            iconSize: [28, 28], iconAnchor: [14, 14]
          }),
          title: feature.properties.name || feature.id,
          zIndexOffset: 200
        }),
        onEachFeature: (feature, marker) => {
          const p = feature.properties;
          const updatedAt = p.status_reported_at || p.status_captured_at;
          const updated = updatedAt
            ? new Date(updatedAt).toLocaleString("en-US", { timeZone: "America/Phoenix" })
            : "Unknown";
          const content = `<div class="d">${esc(p.name || feature.id)}</div>
            ${p.is_smart ? '<div class="station-smart">SMART · App rental</div>' : ""}
            <div>Bikes available: <b>${esc(p.bikes_available ?? "Unknown")}</b></div>
            <div>Spots available: <b>${esc(p.spots_available ?? "Unknown")}</b></div>
            <div class="s">Refreshed: ${esc(updated)}</div>`;
          marker.bindTooltip(content, { direction: "top", className: "station-tooltip" });
          marker.bindPopup(content);
        }
      });
      if (stationToggle.checked) stationLayer.addTo(routeMap);
      networkBounds = bounds;
      inventory.setData(data);
      refreshFacilityLayers();
      document.getElementById("route-snapshot").textContent = data.snapshot_at
        ? `Oldest agency import · ${new Date(data.snapshot_at).toLocaleDateString()}` : "";
      updateSummary();
    } catch (error) {
      summary.textContent = `${error.message} Check the data service and try Reload local data.`;
    } finally {
      loading = false;
      reload.disabled = false;
    }
  }

  document.getElementById("routes-all").onclick = () => {
    groups.forEach(group => setVisible(group, true));
    updateSummary();
  };
  document.getElementById("routes-none").onclick = () => {
    groups.forEach(group => setVisible(group, false));
    updateSummary();
  };
  wardToggle.onchange = () => {
    if (!wardLayer) return;
    if (wardToggle.checked) wardLayer.addTo(routeMap);
    else routeMap.removeLayer(wardLayer);
  };
  crossingToggle.onchange = () => {
    if (!crossingLayer) return;
    if (crossingToggle.checked) crossingLayer.addTo(routeMap);
    else routeMap.removeLayer(crossingLayer);
    updateSummary();
  };
  stationToggle.onchange = () => {
    if (!stationLayer) return;
    if (stationToggle.checked) stationLayer.addTo(routeMap);
    else routeMap.removeLayer(stationLayer);
    updateSummary();
  };
  document.getElementById("routes-fit").onclick = () => {
    if (networkBounds?.isValid()) routeMap.fitBounds(networkBounds, { padding: [20, 20] });
  };
  reload.onclick = loadData;
  window.addEventListener("resize", () => routeMap.invalidateSize());
  document.querySelector(".route-panel details").addEventListener("toggle", () => routeMap.invalidateSize());
  loadData().then(() => initLocalRouteTraces(routeMap));
})();
