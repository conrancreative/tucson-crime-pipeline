// Tucson bike-theft map. Reads the config constants (SUPABASE_URL,
// SUPABASE_ANON_KEY, YEAR) defined in an inline <script> in index.html, which
// loads before this file. Leaflet (global `L`) loads in the <head>.

// Size the app to the actual visible height. iOS reports window.innerHeight
// correctly (unlike 100vh/100dvh at load), so drive layout from it and keep
// it in sync on rotate/resize; snap scroll to top in case anything nudged it.
const setAppHeight = () => {
  document.documentElement.style.setProperty("--app-height", window.innerHeight + "px");
  window.scrollTo(0, 0);
};
setAppHeight();
["resize", "orientationchange", "pageshow"].forEach(e => window.addEventListener(e, setAppHeight));

const apiHeaders = { apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${SUPABASE_ANON_KEY}` };

// push a custom event to GTM's dataLayer (safe no-op if GTM is blocked/absent)
const track = (event, props = {}) =>
  (window.dataLayer = window.dataLayer || []).push({ event, ...props });
// bigger, easier-to-tap dots on phones (20px diameter, slightly translucent so
// overlaps read better) vs other screens (16px)
const IS_MOBILE = window.matchMedia("(max-width: 640px)").matches;
const DOT_RADIUS = IS_MOBILE ? 10 : 8;
const DOT_FILL = IS_MOBILE ? 0.7 : 0.9;

// grayscale basemap — only the markers carry color
const map = L.map("map", { zoomControl: true }).setView([32.221, -110.955], 12);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// ward colors — shared by the map overlays AND the table key for consistency
const WARD_COLORS = { "1": "#4E79A7", "2": "#59A14F", "3": "#8158B0", "4": "#C94F9C", "5": "#76B7B2", "6": "#E24A43" };
const wardColor = w => WARD_COLORS[w] || "#9ca3af";

// dot colors by source: TPD (city) vs UAPD (University of Arizona PD)
const TPD_COLOR = "#e8833a";   // existing orange accent
const UA_COLOR  = "#AB0520";   // UA cardinal red
const dotColor  = src => (src === "UAPD" ? UA_COLOR : TPD_COLOR);

// wards go in a lower pane so the theft dots sit on top and stay clickable
map.createPane("wards");
map.getPane("wards").style.zIndex = 350;        // ward fills, below the overlay pane (400)
map.createPane("wardlabels");
map.getPane("wardlabels").style.zIndex = 360;   // big ward numbers, above fills but below dots

// ---- ward selection: click a ward → zoom in + filter to its dots --------
const crimesLayer = L.layerGroup().addTo(map);
const crimeMarkers = [];      // { marker, ward }
let allPts = [];
let selectedWard = null;

function applyMapFilter(ward) {
  crimesLayer.clearLayers();
  crimeMarkers.forEach(m => { if (!ward || m.ward === ward) crimesLayer.addLayer(m.marker); });
}
function applyTableFilter(ward) {
  document.querySelectorAll("#rows tr").forEach(tr => {
    tr.style.display = (!ward || tr.dataset.ward === ward) ? "" : "none";
  });
}
function updateHeader(ward) {
  const set = ward ? crimeMarkers.filter(m => m.ward === ward) : crimeMarkers;
  const ua = set.filter(m => m.source === "UAPD").length;
  const tpd = set.length - ua;
  document.getElementById("count").textContent = set.length;
  document.getElementById("scope").textContent = ward ? `in Ward ${ward}` : "in 2026";
  // show the TPD vs UA split whenever the current view contains UA thefts (Ward 6)
  document.getElementById("split").innerHTML = ua > 0
    ? ` · <b>${tpd}</b> TPD · <b class="ua-tag">${ua}</b> UA`
    : "";
  document.getElementById("reset").style.display = ward ? "inline-flex" : "none";
}
function selectWard(ward, member, layer) {
  if (selectedWard === ward) { resetSelection(); return; }   // click again to deselect
  selectedWard = ward;
  track("ward_filter", {                                     // custom event: ward selected
    ward,
    council_member: member || undefined,
    theft_count: crimeMarkers.filter(m => m.ward === ward).length
  });
  const b = layer.getBounds();
  map.setView(b.getCenter(), Math.min(map.getBoundsZoom(b) + 1, 18));   // fit, then a step closer
  applyMapFilter(ward); applyTableFilter(ward); updateHeader(ward);
  document.getElementById("reset-label").textContent = `Ward ${ward}${member ? " · " + member : ""}`;
  document.getElementById("reset").style.background = wardColor(ward);  // pill matches the ward
}
function resetSelection() {
  selectedWard = null;
  applyMapFilter(null); applyTableFilter(null); updateHeader(null);
  if (allPts.length) map.fitBounds(allPts, { padding: [40, 40] });
}
document.getElementById("reset").onclick = resetSelection;

// ---- tabs ---------------------------------------------------------------
function show(view) {
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("active", v.id === "view-" + view));
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("on", t.dataset.view === view));
  // the count/date subbar only makes sense for the map & table
  document.querySelector(".subbar").style.display = view === "sources" ? "none" : "";
  if (view === "map") setTimeout(() => map.invalidateSize(), 0);
}
document.querySelectorAll(".tab").forEach(t => t.onclick = () => {
  track("tab_view", {                            // custom event: which tab was opened
    tab: t.dataset.view,
    filter_active: selectedWard != null,         // was a ward filter applied?
    filtered_ward: selectedWard || "none"     // if so, which ward
  });
  show(t.dataset.view);
});

// ---- table row → its dot on the map -------------------------------------
function goToMarker(rec) {
  track("row_to_map", {                                         // custom event: table row -> dot
    source: rec.source,
    ward: rec.ward,                                            // ward of the clicked row
    filter_active: selectedWard != null,                      // was a ward filter applied?
    filtered_ward: selectedWard || "none"                  // if so, which ward
  });
  show("map");
  if (!crimesLayer.hasLayer(rec.marker)) crimesLayer.addLayer(rec.marker);
  setTimeout(() => {                                   // after the map re-sizes
    const p = rec.marker.getPopup();
    if (p) p.options.autoPan = false;                 // don't let the popup shove the dot off-center
    rec.marker.openPopup();
    map.setView(rec.marker.getLatLng(), Math.max(map.getZoom(), 16), { animate: true });
    if (p) setTimeout(() => { p.options.autoPan = true; }, 400);  // restore for normal dot clicks
  }, 60);
}

const statusEl = document.getElementById("status");
const setStatus = (m, err) => {
  statusEl.style.display = m ? "block" : "none";
  if (m) { statusEl.textContent = m; statusEl.classList.toggle("err", !!err); }
};
const esc = s => (s == null ? "" : String(s)).replace(/[&<>"]/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmtDate = az => {
  if (!az) return "Unknown";
  const d = new Date(az.replace(" ", "T"));
  return isNaN(d) ? az : d.toLocaleString("en-US",
    { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
};
const fmtDay = (az, withYear = true) => {
  if (!az) return "—";
  const d = new Date(az.replace(" ", "T"));
  return isNaN(d) ? az : d.toLocaleDateString("en-US",
    withYear ? { month: "short", day: "numeric", year: "numeric" } : { month: "short", day: "numeric" });
};

// ---- ward overlays (color-coded, translucent) ---------------------------
async function loadWards() {
  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/api_wards?select=ward,council_member,geometry`,
      { headers: apiHeaders });
    if (!res.ok) return;
    const wards = await res.json();
    const fc = {
      type: "FeatureCollection",
      features: wards.map(w => ({
        type: "Feature",
        properties: { ward: w.ward, member: w.council_member },
        geometry: w.geometry
      }))
    };
    L.geoJSON(fc, {
      pane: "wards",
      style: f => ({ color: wardColor(f.properties.ward), weight: 1.5, opacity: 0.85,
                     fillColor: wardColor(f.properties.ward), fillOpacity: 0.20 }),
      onEachFeature: (f, layer) => {
        layer.bindTooltip(`<span style="color:${wardColor(f.properties.ward)}">${esc(f.properties.ward)}</span>`,
          { permanent: true, direction: "center", className: "ward-label", pane: "wardlabels", opacity: 0.5 });
        layer.on("click", () => selectWard(f.properties.ward, f.properties.member, layer));
      }
    }).addTo(map);
  } catch (_) { /* wards are optional decoration */ }
}

// ---- crimes -------------------------------------------------------------
async function loadCrimes() {
  const params = new URLSearchParams({
    select: "id,occurred_at_az,ward,neighborhood,address,lat,lon,source,geocoded",
    year: `eq.${YEAR}`, order: "occurred_at.desc"
  });
  let rows;
  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/mart_bike_crimes?${params}`, { headers: apiHeaders });
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
    rows = await res.json();
  } catch (e) {
    setStatus("Couldn't load data — " + e.message, true);
    return;
  }

  const pts = [];
  const tbody = document.getElementById("rows");
  let newest = null, oldest = null;
  for (const r of rows) {
    const t = r.occurred_at_az;
    if (t) { if (!newest || t > newest) newest = t; if (!oldest || t < oldest) oldest = t; }

    const isUA = r.source === "UAPD";
    const approx = isUA && r.geocoded === false;   // placed at campus center

    let rec = null;
    if (r.lat != null && r.lon != null) {
      const marker = L.circleMarker([r.lat, r.lon], {
        radius: DOT_RADIUS, color: "#fff", weight: 1.5,
        fillColor: dotColor(r.source), fillOpacity: DOT_FILL,
        dashArray: approx ? "2 3" : null        // dashed ring = approximate location
      }).bindPopup(
        (isUA ? `<div class="src-ua">UAPD</div>` : "") +
        `<div class="d">${fmtDate(r.occurred_at_az)}</div>` +
        `<div>${esc(r.address) || "Address withheld"}</div>` +
        `<div class="s">Ward ${esc(r.ward) || "?"}${r.neighborhood ? " · " + esc(r.neighborhood) : ""}</div>` +
        (approx ? `<div class="approx">Approximate — placed at campus center</div>` : "")
      );
      rec = { marker, ward: r.ward, source: r.source };
      crimeMarkers.push(rec);
      pts.push([r.lat, r.lon]);
    }

    const tr = document.createElement("tr");
    tr.dataset.ward = r.ward || "";
    tr.dataset.source = r.source || "";
    tr.innerHTML =
      `<td>${fmtDate(r.occurred_at_az)}</td>` +
      `<td class="addr">${esc(r.address) || "—"}${isUA ? `<span class="ua-badge">UA</span>` : ""}` +
        `<span class="go-map"><span class="go-map-txt">View on map </span>↗</span></td>` +
      `<td><span class="ward-pill" style="background:${wardColor(r.ward)};color:#fff">${esc(r.ward) || "?"}</span></td>` +
      `<td>${esc(r.neighborhood) || "—"}</td>`;
    if (rec) tr.onclick = () => goToMarker(rec);       // click the row → its dot
    tbody.appendChild(tr);
  }

  allPts = pts;
  applyMapFilter(null);            // add all markers via the filter layer
  updateHeader(null);
  document.getElementById("from").textContent = fmtDay(oldest, false);
  document.getElementById("through").textContent = fmtDay(newest, true);
  if (pts.length) map.fitBounds(pts, { padding: [40, 40] });
  setStatus(null);
}

// ---- data sources tab ---------------------------------------------------
// Static copy per source; live timestamps/counts come from the api_data_sources
// view and are matched by `key`. `live` sources are flagged stale after 48h;
// static ones (backfilled once) are exempt. `desc` may contain inline HTML.
const SOURCES = [
  {
    key: "reported_2026", live: true, method: ["API", "ArcGIS"],
    name: "Tucson Police Department: Reported Crimes",
    desc: `The City of Tucson's official open-data crime layer, filtered to bicycle ` +
          `larceny (offense code <span class="code">0606</span>). This is the primary ` +
          `source for current-year thefts shown on the map.`,
    coverage: "Jan 2026 to present",
    cadence: "Source updates ~daily; pulled daily at 5:00 AM AZ",
    endpoint: "https://services3.arcgis.com/9coHY2fvuFjG9HQX/arcgis/rest/services/TPDOpenDataReportedCrimes2026/FeatureServer/0"
  },
  {
    key: "uapd", live: true, method: ["Scraper", "HTML"],
    name: "University of Arizona Police Department: Daily Activity Log",
    desc: `The University of Arizona Police Department's Clery Act daily crime and ` +
          `safety log for the campus area. Scraped, filtered to bicycle larceny, then ` +
          `geocoded to campus locations.`,
    coverage: "2019 to present",
    cadence: "Posted daily; scraped daily at 5:00 AM AZ",
    endpoint: "https://uapd.arizona.edu/public-information/uapd-daily-activity-log"
  },
  {
    key: "incidents_history", live: false, method: ["API", "ArcGIS"],
    name: "Tucson Police Department: Incident Records (2018 to 2025)",
    desc: `Tucson Police incident records by year, used for the historical ` +
          `bicycle-theft trend. Backfilled once from the annual open-data layers.`,
    coverage: "2018 to 2025",
    cadence: "Static; backfilled once",
    endpoint: "https://gis.tucsonaz.gov/arcgis/rest/services/PublicMaps/OpenData_PublicSafety/MapServer (year layers 40, 48, 54, 69, 71, 78, 80, 81)"
  },
  {
    key: "incidents_45day", live: true, method: ["API", "ArcGIS"],
    name: "Tucson Police Department: 45-Day Incidents",
    desc: `The rolling 45-day window of Tucson Police incident records. Kept as a ` +
          `backup to fill any gaps if the primary Reported Crimes source falls behind ` +
          `or drops rows. Stored but not shown on the map, and used as a freshness signal.`,
    coverage: "Rolling last 45 days",
    cadence: "Updated daily; pulled daily at 5:00 AM AZ",
    endpoint: "https://gis.tucsonaz.gov/arcgis/rest/services/PublicMaps/OpenData_PublicSafety/MapServer/42"
  },
  {
    key: "cfs_bike", live: true, method: ["API", "ArcGIS"],
    name: "Tucson Police Department: Calls for Service",
    desc: `The preliminary police dispatch feed (about a two-day lag), filtered to ` +
          `bicycle-related calls. Kept to catch recent thefts that have not yet appeared ` +
          `in the primary Reported Crimes source. Stored but not shown on the map.`,
    coverage: "Rolling last 45 days",
    cadence: "Updated daily (~2-day lag); pulled daily",
    endpoint: "https://gis.tucsonaz.gov/arcgis/rest/services/PublicMaps/OpenData_PublicSafety/MapServer/41"
  },
  {
    key: "geocoding", live: true, method: ["Geocoder"],
    name: "Address Geocoding",
    desc: `Address-to-coordinate lookups from the U.S. Census geocoder and ` +
          `OpenStreetMap, plus manual overrides for campus locations the geocoders ` +
          `cannot place.`,
    coverage: "All source addresses",
    cadence: "Runs after each scrape; new addresses only",
    endpoint: "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress · https://nominatim.openstreetmap.org/search",
    latestFromCount: true, countLabel: "Addresses cached", countUnit: ""
  },
  {
    key: "wards", live: false, method: ["Reference"],
    name: "Tucson City Council Ward Boundaries",
    desc: `Council ward boundaries used to color and filter the map. A static ` +
          `reference layer from Pima County open data.`,
    coverage: "Current boundaries",
    cadence: "Static reference",
    endpoint: "https://gisopendata.pima.gov/datasets/PimaMaps::wards-city-of-tucson.geojson",
    latestFromCount: true, countLabel: "Boundaries", countUnit: " wards"
  }
];

// parse a plain YYYY-MM-DD as a local date (avoids the UTC "off by one day" bug)
const fmtDateOnly = s => {
  if (!s) return "—";
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US",
    { month: "short", day: "numeric", year: "numeric" });
};
// format the AZ-local refresh stamp ("2026-09-01 08:42:…") as "Sep 1, 2026 · 8:42 AM"
const fmtStamp = az => {
  if (!az) return "—";
  const d = new Date(az.replace(" ", "T"));
  if (isNaN(d)) return az;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) +
    " · " + d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
};

async function loadSources() {
  let rows = [];
  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/api_data_sources`, { headers: apiHeaders });
    if (res.ok) rows = await res.json();
  } catch (_) { /* leave timestamps blank if unreachable */ }
  const byKey = Object.fromEntries(rows.map(r => [r.source_key, r]));

  document.getElementById("src-asof").textContent = "as of " +
    new Date().toLocaleString("en-US", { timeZone: "America/Phoenix",
      month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" }) + " AZ";

  let staleCount = 0;
  document.getElementById("src-cards").innerHTML = SOURCES.map(src => {
    const row = byKey[src.key] || {};
    const hrs = row.last_refreshed ? (Date.now() - new Date(row.last_refreshed)) / 36e5 : Infinity;
    const stale = src.live && hrs > 48;
    if (stale) staleCount++;
    const chip = src.method.map(esc).join('<span class="sep">·</span>');
    const left = src.latestFromCount
      ? { lbl: src.countLabel, val: (row.row_count ?? 0).toLocaleString() + (src.countUnit || "") }
      : { lbl: "Latest data row", val: fmtDateOnly(row.latest_data_row) };
    const days = isFinite(hrs) ? Math.floor(hrs / 24) : null;
    return `<div class="src-card">
      <div class="src-card-top">
        <div class="src-name"><span class="src-dot ${stale ? "warn" : "ok"}"></span><h3>${esc(src.name)}</h3></div>
        <span class="src-chip">${chip}</span>
      </div>
      <p class="src-desc">${src.desc}</p>
      <div class="src-meta">
        <div><span class="lbl">Coverage</span><span class="val">${esc(src.coverage)}</span></div>
        <div><span class="lbl">Update cadence</span><span class="val">${esc(src.cadence)}</span></div>
      </div>
      <div class="src-endpoint"><span class="k">GET</span><span class="u">${esc(src.endpoint)}</span></div>
      <div class="src-stats">
        <div class="src-stat"><span class="lbl">${esc(left.lbl)}</span><span class="big">${left.val}</span></div>
        <div class="src-stat"><span class="lbl">Last refreshed</span>
          <span class="big">${fmtStamp(row.last_refreshed_az)} <span class="az">AZ</span></span>
          ${stale ? `<span class="warn">Not refreshed in ${days} days</span>` : ""}
        </div>
      </div>
    </div>`;
  }).join("");

  const overall = document.getElementById("src-overall");
  overall.className = "src-overall " + (staleCount ? "warn" : "ok");
  overall.innerHTML = staleCount
    ? `<span class="pip"></span> <b>${staleCount} of ${SOURCES.length} sources</b>&nbsp;not refreshed in 48 hours`
    : `<span class="pip"></span> <b>All ${SOURCES.length} sources</b>&nbsp;refreshed on schedule`;
}

loadWards();
loadCrimes();
loadSources();

// re-measure after load + a beat (iOS' toolbar settles late) and refresh the map
const settle = () => { setAppHeight(); map.invalidateSize(); };
window.addEventListener("load", settle);
setTimeout(settle, 300);
