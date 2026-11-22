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
function drawWards(map, wards, onWardClick) {
  return L.geoJSON(wardsToGeoJSON(wards), {
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
  }).addTo(map);
}