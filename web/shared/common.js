// Shared helpers for the theft and bike-route frontends. Load before app scripts.

const esc = s => (s == null ? "" : String(s)).replace(/[&<>"]/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// Size the app to the actual visible height. iOS reports window.innerHeight
// correctly (unlike 100vh/100dvh at load), so drive layout from it and keep
// it in sync on rotate/resize; snap scroll to top in case anything nudged it.
const setAppHeight = () => {
  document.documentElement.style.setProperty("--app-height", window.innerHeight + "px");
  window.scrollTo(0, 0);
};
setAppHeight();
["resize", "orientationchange", "pageshow"].forEach(e => window.addEventListener(e, setAppHeight));

// Keep both maps on the same basemap and starting extent.
function createTucsonMap(container, { preferCanvas = false, attribution = "" } = {}) {
  const map = L.map(container, { preferCanvas }).setView([32.221, -110.955], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' + attribution
  }).addTo(map);
  return map;
}

// Preview navigation becomes visible on the local site.
if (["localhost", "127.0.0.1", "[::1]"].includes(location.hostname)) {
  document.querySelectorAll(".local-preview-link").forEach(link => { link.hidden = false; });
}

// ward colors — shared by the map overlays AND the table key for consistency
const WARD_COLORS = { "1": "#4E79A7", "2": "#59A14F", "3": "#8158B0", "4": "#C94F9C", "5": "#76B7B2", "6": "#E24A43" };
const wardColor = w => WARD_COLORS[w] || "#9ca3af";

// receive ward records and turn into geoJSON collection
function wardsToGeoJSON(wards) {
  return {
    type: "FeatureCollection",
    features: wards.map(ward => ({
      type: "Feature",
      properties: {
        ward: ward.ward,
        member: ward.council_member
      },
      geometry: ward.geometry
    }))
  };
}

// reusable map drawing
function drawWards(map, wards, onWardClick, visible = true) {
  // Ward panes are created once per map, beneath route lines and markers.
  if (!map.getPane("wards")) {
    map.createPane("wards");
    map.getPane("wards").style.zIndex = 350;
  }
  if (!map.getPane("wardlabels")) {
    map.createPane("wardlabels");
    map.getPane("wardlabels").style.zIndex = 360;
  }
  const wardLayer = L.geoJSON(wardsToGeoJSON(wards), {
    pane: "wards",
    style: feature => ({
      color: wardColor(feature.properties.ward),
      weight: 1.5,
      opacity: 0.85,
      fillColor: wardColor(feature.properties.ward),
      fillOpacity: 0.30
    }),
    onEachFeature: (feature, layer) => {
      const ward = feature.properties.ward;

      layer.bindTooltip(
        () => {
          const label = document.createElement("span");
          label.style.color = wardColor(ward);
          label.textContent = ward;
          return label;
        },
        {
          permanent: true,
          direction: "center",
          className: "ward-label",
          pane: "wardlabels",
          opacity: 0.5
        }
      );

      if (onWardClick) {
        layer.on("click", () => {
          onWardClick(ward, feature.properties.member, layer);
        });
      }
    }
  });
  if (visible) wardLayer.addTo(map);
  return wardLayer;
}
