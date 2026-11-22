// Private examples are served only by the local preview, outside static assets.
async function initLocalRouteTraces(map) {
  if (!["localhost", "127.0.0.1", "[::1]"].includes(location.hostname)) return;
  const panel = document.getElementById("local-traces");
  const select = document.getElementById("local-trace-select");
  const status = document.getElementById("local-trace-status");
  const notes = document.getElementById("local-trace-notes");
  const fit = document.getElementById("local-trace-fit");
  panel.hidden = false;
  let layer;
  try {
    const response = await fetch("/api/local-route-traces", { cache: "no-store" });
    if (!response.ok) throw new Error("Generate the local commute traces to view examples.");
    const data = await response.json();
    for (const route of data.routes) {
      const option = document.createElement("option");
      option.value = route.id;
      option.textContent = route.label;
      select.append(option);
    }
    const colors = { "route-1": "#7c3aed", "route-2": "#0369a1", "route-3-park": "#047857", "route-3-fourth": "#be123c" };
    map.createPane("commute-traces");
    map.getPane("commute-traces").style.zIndex = 450;
    function render() {
      if (layer) map.removeLayer(layer);
      notes.replaceChildren();
      const route = data.routes.find(item => item.id === select.value);
      fit.disabled = !route;
      if (!route) {
        status.textContent = "Select a journey to inspect its draft trace.";
        return;
      }
      const features = data.features.filter(feature => feature.properties.route_id === route.id);
      const color = route.color || colors[route.id] || "#0369a1";
      layer = L.geoJSON(features, {
        pane: "commute-traces",
        style: feature => ({
          color: feature.properties.departure ? "#ea580c" : color,
          weight: 6, opacity: 1,
          dashArray: feature.properties.departure ? "7 6" : null,
        }),
        pointToLayer: (feature, latlng) => feature.properties.kind === "business_endpoint"
          ? L.marker(latlng, {
            pane: "commute-traces", title: feature.properties.label, zIndexOffset: 5000,
            icon: L.divIcon({
              className: `route-endpoint-marker ${feature.properties.role === "start" ? "route-endpoint-start" : "route-endpoint-finish"}`,
              html: feature.properties.role === "start" ? "S" : "E", iconSize: [26, 26], iconAnchor: [13, 13],
            }),
          })
          : feature.properties.kind === "crossing"
          ? L.marker(latlng, {
            pane: "commute-traces", title: feature.properties.label,
            icon: L.divIcon({ className: "crossing-marker", html: '<span aria-hidden="true">🚦</span>',
              iconSize: [30, 30], iconAnchor: [15, 15] }),
          })
          : L.circleMarker(latlng, {
            pane: "commute-traces", radius: 6, color: "#fff", weight: 2,
            fillColor: feature.properties.kind === "business_endpoint"
              ? (feature.properties.role === "start" ? "#047857" : "#be123c") : color,
            fillOpacity: 1,
          }),
        onEachFeature: (feature, segment) => {
          const p = feature.properties;
          if (p.kind === "business_endpoint") {
            segment.bindPopup(`<strong>${esc(p.label)}</strong><p>${p.role === "start" ? "Start" : "Destination"} · Business location; street access is approximate.</p>`);
            segment.bindTooltip(p.label, { direction: "top" });
            return;
          }
          if (p.kind === "crossing") {
            segment.bindPopup(`<strong>${esc(p.label)}</strong><div>Signal type: ${esc(p.signal_type)}</div><div>${esc(p.source)} · record ${esc(p.object_id)}</div>`);
            return;
          }
          if (p.kind === "checkpoint") {
            segment.bindPopup(esc(p.label));
            return;
          }
          const flags = p.flags.map(flag => `<li>${esc(flag)}</li>`).join("");
          const facilities = [...new Set((p.agency_matches || []).map(match =>
            `${match.facility_type}${match.bikeway ? ` · ${match.bikeway}` : ""}`))];
          segment.bindPopup(`<strong>${esc(p.street)}</strong><div>${esc(p.leg)}</div>
            <div>Agency facility: ${facilities.length ? facilities.map(esc).join("<br>") : "No match established"}</div>
            <div>Speed tag: ${esc(p.maxspeed || "Unknown")}</div>
            <div>Lanes tag: ${esc(p.lanes || "Unknown")}</div>
            <div>Bicycle tag: ${esc(p.bicycle || "Unspecified")}</div>
            ${p.observation ? `<div>${esc(p.observation)}</div>` : ""}
            <div class="s">OSM way ${esc(p.osm_way_id)} · Agency matching is provisional · Stress not calculated</div>
            ${flags ? `<ul class="trace-flags">${flags}</ul>` : ""}`);
        },
      }).addTo(map);
      status.textContent = `${route.miles.toFixed(2)} draft miles · ${(route.departure_meters / 1609.344).toFixed(2)} mi needs corridor review`;
      const messages = [...route.notes,
        route.endpoint_note || "Start approximated at Prince/Treat.",
        route.validation_note || "Access, one-way rules, turn restrictions, and crossing quality have not been validated."];
      const flags = new Set(features.flatMap(feature => feature.properties.flags || []));
      if ([...flags].some(flag => flag.includes("one-way"))) messages.push("Some segments conflict with OSM one-way tags; inspect before using this as directions.");
      if ([...flags].some(flag => flag.includes("Footway"))) messages.push("The draft touches footway geometry. Those connections need shared-use-path verification.");
      for (const message of messages) {
        const p = document.createElement("p");
        p.textContent = message;
        notes.append(p);
      }
      fit.onclick = () => map.fitBounds(layer.getBounds(), { padding: [15, 15] });
      fit.onclick();
    }
    select.disabled = false;
    select.onchange = render;
    const parameters = new URLSearchParams(location.search);
    const requested = parameters.get("example");
    select.value = data.routes.some(route => route.id === requested) ? requested : "";
    if (select.value) panel.open = true;
    render();
    if (select.value) {
      if (parameters.get("context") === "off") {
        document.getElementById("routes-none").click();
        for (const id of ["route-crossings", "route-stations"]) {
          const input = document.getElementById(id);
          if (input.checked) input.click();
        }
      }
      const sidebar = panel.closest(".route-panel");
      sidebar.scrollTop = panel.offsetTop - sidebar.offsetTop;
    }
  } catch (error) {
    status.textContent = error.message;
  }
}
