// Infrastructure inspection only. Source membership is not a route recommendation.
function initBikewayCatalog(map, onFilterChange) {
  const panel = document.getElementById("bikeway-inventory");
  const select = document.getElementById("bikeway-select");
  const search = document.getElementById("bikeway-search");
  const detail = document.getElementById("bikeway-detail");
  const coverage = document.getElementById("inventory-coverage");
  const auditSelect = document.getElementById("inventory-issue-type");
  const showIssues = document.getElementById("inventory-issues-on");
  const issueList = document.getElementById("inventory-issue-list");
  const issueCount = document.getElementById("inventory-issue-count");
  const more = document.getElementById("inventory-issue-more");
  const sources = { pag: document.getElementById("inventory-source-pag"), osm: document.getElementById("inventory-source-osm") };
  const issueLabels = {
    reported_source_update: "Reported updates",
    bicycle_tag_conflict: "Conflicting bicycle tags",
    named_route_continuity_review: "Named-route continuity",
    agency_no_osm_match: "Agency without OSM match",
    osm_no_agency_match: "OSM without agency match",
    footway_shared_use_unverified: "Footways needing verification",
    route_members_unavailable: "Route members outside local geometry",
    nonstandard_facility_status: "Proposed / nonstandard status",
    route_identity_review: "Possible route-name aliases",
  };
  let data;
  let selected = "";
  let pageSize = 15;
  let markerLayer = L.layerGroup();

  function matches(feature) {
    const p = feature.properties;
    return (!sources[p.source] || sources[p.source].checked)
      && (!selected || (p.bikeway_ids || []).includes(selected));
  }

  function selectedFeatures() {
    return data.routes.features.filter(matches);
  }

  function fitFeatures(features) {
    const layer = L.geoJSON(features);
    const bounds = layer.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [25, 25] });
  }

  function renderDetail() {
    detail.replaceChildren();
    const route = data.catalog.find(item => item.id === selected);
    if (!route) {
      detail.textContent = "All source facilities, including unnamed sections. Agency lines are solid; OSM lines are dashed. Bicycle permission is not the same as dedicated infrastructure.";
      return;
    }
    const heading = document.createElement("strong");
    heading.textContent = route.name;
    detail.append(heading);
    for (const [source, info] of Object.entries(route.details.sources)) {
      const p = document.createElement("p");
      p.textContent = `${source === "pag" ? "Agency" : "OSM"}: ${info.sections} sections · ${info.source_miles} source miles · ${info.geometry_groups} geometry groups`;
      detail.append(p);
    }
    const evidence = document.createElement("p");
    evidence.textContent = `${route.details.facility_types.join(", ")}. Separate geometry groups need review; they do not prove a physical gap.`;
    detail.append(evidence);
    const names = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "Source names and streets";
    const text = document.createElement("p");
    text.textContent = [...route.source_names, ...route.details.streets].join(" · ") || "Not named in source";
    names.append(summary, text);
    detail.append(names);
    for (const relation of route.details.osm_relations || []) {
      const p = document.createElement("p");
      const a = document.createElement("a");
      a.href = relation.source_url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = `OSM route ${relation.id}`;
      p.append(a, ` · ${relation.local_way_members}/${relation.flattened_way_members} way memberships represented locally`);
      detail.append(p);
    }
  }

  function renderOptions() {
    const query = search.value.trim().toLocaleLowerCase();
    select.replaceChildren(new Option("All facilities", ""));
    for (const route of data.catalog) {
      if (!["named_bikeway", "area_network"].includes(route.kind)) continue;
      if (!Object.keys(route.details.sources).length) continue;
      if (query && ![route.name, ...route.source_names, ...route.details.streets].some(name => name.toLocaleLowerCase().includes(query))) continue;
      select.append(new Option(route.name, route.id));
    }
    // Keep an active route selected while typing a new search.
    if (selected && ![...select.options].some(option => option.value === selected)) {
      const route = data.catalog.find(item => item.id === selected);
      if (route) select.append(new Option(route.name, route.id));
    }
    select.value = selected;
  }

  function renderIssues() {
    map.removeLayer(markerLayer);
    markerLayer = L.layerGroup();
    issueList.replaceChildren();
    const issues = data.issues.features.filter(feature => {
      const p = feature.properties;
      return (!selected || p.bikeway_ids.includes(selected))
        && (!auditSelect.value || p.issue_type === auditSelect.value);
    });
    issueCount.textContent = `${issues.length.toLocaleString()} review items${selected ? " for this bikeway" : " in the study area"}. Matching differences are not necessarily physical defects.`;
    for (const feature of issues) {
      if (!feature.geometry) continue;
      const point = L.geoJSON(feature).getBounds().getCenter();
      const marker = L.circleMarker(point, { radius: 7, color: "#9a3412", fillColor: "#fb923c", fillOpacity: .8, weight: 2 });
      marker.bindPopup(`<strong>${esc(issueLabels[feature.properties.issue_type] || feature.properties.issue_type)}</strong><p>${esc(feature.properties.description)}</p>`);
      markerLayer.addLayer(marker);
    }
    if (showIssues.checked) markerLayer.addTo(map);
    for (const feature of issues.slice(0, pageSize)) {
      const li = document.createElement("li");
      const p = feature.properties;
      const text = document.createElement("p");
      text.textContent = `${p.section_id || issueLabels[p.issue_type] || "Source review"}: ${p.description}`;
      li.append(text);
      if (feature.geometry) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "Locate";
        button.onclick = () => {
          const bounds = L.geoJSON(feature).getBounds();
          map.setView(bounds.getCenter(), Math.max(map.getZoom(), 17));
          if (!showIssues.checked) { showIssues.checked = true; markerLayer.addTo(map); }
        };
        li.append(button);
      }
      issueList.append(li);
    }
    more.hidden = issues.length <= pageSize;
  }

  select.onchange = () => {
    selected = select.value;
    pageSize = 15;
    onFilterChange();
    renderDetail();
    renderIssues();
    if (selected) fitFeatures(selectedFeatures());
  };
  search.oninput = renderOptions;
  Object.values(sources).forEach(input => { input.onchange = () => { onFilterChange(); renderDetail(); }; });
  auditSelect.onchange = () => { pageSize = 15; renderIssues(); };
  showIssues.onchange = renderIssues;
  more.onclick = () => { pageSize += 15; renderIssues(); };
  document.getElementById("bikeway-fit").onclick = () => fitFeatures(selectedFeatures());
  document.getElementById("inventory-fit-area").onclick = () => map.fitBounds(L.geoJSON(data.area).getBounds());
  document.getElementById("inventory-download").onclick = () => {
    const blob = new Blob([JSON.stringify({ audit: data.audit, catalog: data.catalog, issues: data.issues }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "bikeway-audit-tucson_3mi.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  return {
    matches,
    setData(value) {
      if (!value.audit || !value.catalog) return;
      data = value;
      panel.hidden = false;
      const summary = data.audit.summary;
      const built = new Date(data.audit.built_at).toLocaleString("en-US", { timeZone: "America/Phoenix" });
      document.getElementById("inventory-freshness").textContent = data.audit.stale
        ? "Inputs changed. Rebuild the inventory before relying on this snapshot."
        : `Inventory built: ${built}`;
      document.getElementById("inventory-freshness").classList.toggle("inventory-stale", data.audit.stale);
      coverage.textContent = `${summary.agency_sections_in_scope.toLocaleString()}/${summary.agency_sections_in_scope.toLocaleString()} agency sections represented within Tucson + 3 miles. ${summary.osm_bicycle_sections.toLocaleString()} OSM bicycle-evidence sections. ${summary.osm_bicycle_route_relations} OSM route relations. ${summary.agency_sections_without_osm_candidates.toLocaleString()} agency sections need matching review. This accounts for imported sources, not every real-world facility.`;
      const previousIssue = auditSelect.value;
      auditSelect.replaceChildren(new Option("All review types", ""));
      for (const [key, count] of Object.entries(summary.issues)) {
        auditSelect.append(new Option(`${issueLabels[key] || key} (${count.toLocaleString()})`, key));
      }
      auditSelect.value = [...auditSelect.options].some(option => option.value === previousIssue) ? previousIssue : "";
      renderOptions();
      renderDetail();
      renderIssues();
    },
  };
}

function bikewaySectionPopup(p) {
  if (!p.source) return `<strong>${esc(p.street || "Unnamed bikeway")}</strong><div>${esc(p.facility_type)}</div>`;
  const facts = p.facts || {};
  const tags = facts.osm_tags || facts.agency_properties || {};
  const when = p.source_date ? new Date(p.source_date).toLocaleDateString("en-US", { timeZone: "America/Phoenix" }) : "Unknown";
  const matched = facts.agency_matches || [];
  const conflicts = ["no", "dismount"].includes(tags.bicycle) ? `<p>OSM bicycle=${esc(tags.bicycle)}. Facility and access evidence require reconciliation.</p>` : "";
  const source = p.source === "pag" ? "PAG agency layer" : "OpenStreetMap";
  return `<strong>${esc(p.street || "Unnamed facility")}</strong><div>${esc(p.facility_type)}</div>
    <div>${(p.bikeway_names || []).map(esc).join("<br>")}</div>
    <p>${esc(source)} · ${facts.source_date_kind === "imported_at" ? "Imported" : "Snapshot"}: ${esc(when)}</p>
    <div>Status: ${esc(facts.status || "Unknown")}</div>
    ${p.source === "osm" ? `<div>Agency geometry candidates: ${matched.length}</div>` : ""}
    ${conflicts}<p>Infrastructure inventory. Riding eligibility and stress are not calculated.</p>
    <a href="${esc(p.source_url)}" target="_blank" rel="noopener noreferrer">Inspect source record ${esc(p.source_id)}</a>
    <details class="source-tags"><summary>Original source attributes</summary><pre>${esc(JSON.stringify(tags, null, 2))}</pre></details>`;
}
