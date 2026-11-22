"""Read the private inventory for the local preview; no hosted API grants."""

from build_bikeway_catalog import input_fingerprints


def inventory_data(cursor, scope="tucson_3mi"):
    cursor.execute("select to_regclass('public.bikeway_builds')")
    if not cursor.fetchone()[0]:
        return None
    cursor.execute("select built_at, input_fingerprints, summary from bikeway_builds where scope_key=%s", (scope,))
    build = cursor.fetchone()
    if not build:
        return None
    built_at, fingerprints, summary = build
    try:
        stale = input_fingerprints(cursor, scope) != fingerprints
    except ValueError:
        stale = True
    cursor.execute("""
        select s.section_id, s.source, s.source_id, s.source_url, s.street,
          s.facility_type, s.source_date, s.facts,
          st_asgeojson(st_simplifypreservetopology(s.geom,0.000003),7)::json,
          st_length(s.geom::geography)/1609.344,
          array_agg(m.bikeway_id::text order by m.bikeway_id),
          array_agg(c.name order by m.bikeway_id)
        from bikeway_sections s
        join bikeway_memberships m using (scope_key,section_id)
        join bikeway_catalog c using (scope_key,bikeway_id)
        where s.scope_key=%s
        group by s.scope_key,s.section_id
        order by s.section_id
    """, (scope,))
    features = []
    for identifier, source, source_id, url, street, kind, date, facts, geometry, miles, ids, names in cursor:
        features.append({"type": "Feature", "id": identifier, "geometry": geometry,
            "properties": {"section_id": identifier, "source": source, "source_id": source_id,
                "source_url": url, "street": street, "facility_type": kind,
                "source_date": date.isoformat() if date else None, "facts": facts,
                "length_miles": miles, "bikeway_ids": ids, "bikeway_names": names}})
    cursor.execute("select bikeway_id::text,name,kind,source_names,details from bikeway_catalog where scope_key=%s order by lower(name)", (scope,))
    catalog = [{"id": identifier, "name": name, "kind": kind, "source_names": names, "details": details}
               for identifier, name, kind, names, details in cursor]
    cursor.execute("select issue_id,issue_type,section_id,bikeway_ids::text[],description,st_asgeojson(geom)::json,details from bikeway_issues where scope_key=%s order by issue_type,issue_id", (scope,))
    issues = [{"type": "Feature", "geometry": geometry, "properties": {
        "id": identifier, "issue_type": kind, "section_id": section_id,
        "bikeway_ids": [str(value) for value in ids], "description": description, "details": details}}
        for identifier, kind, section_id, ids, description, geometry, details in cursor]
    cursor.execute("select st_asgeojson(study_area)::json from osm_network_snapshots where scope_key=%s", (scope,))
    area = cursor.fetchone()[0]
    return {"routes": {"type": "FeatureCollection", "features": features}, "catalog": catalog,
            "issues": {"type": "FeatureCollection", "features": issues}, "area": area,
            "audit": {"built_at": built_at.isoformat(), "stale": stale,
                      "inputs": fingerprints, "summary": summary}}
