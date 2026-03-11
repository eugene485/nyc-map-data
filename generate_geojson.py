#!/usr/bin/env python3
"""
Generate NYC ED GeoJSON from MotherDuck voter file.

This script:
1. Loads ED boundary geometries from the base GeoJSON (NYC GIS source)
2. Aggregates fresh voter data from MotherDuck
3. Merges them into a complete GeoJSON with all properties
4. Outputs to nyc-eds.geojson for deployment

CRITICAL: Primary counts use ACTIVE voters only (status='A').
- 57% of voter file is Active
- 38% is Purged (P) - old addresses, may no longer live there
- 5% is Inactive (I) - haven't voted recently, addresses may be stale

SECONDARY counts (total_all, purged_count, inactive_count) include ALL voters
so that EDs with only purged voters still show SOMETHING on the map.

Run: python3 generate_geojson.py
Output: nyc-eds.geojson
"""

import duckdb
import json
import os
from datetime import datetime

# MotherDuck token from environment or hardcoded for local dev
TOKEN = os.environ.get('MOTHERDUCK_TOKEN') or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImV1Z2VuZUBsZWdpb24ubnljIiwibWRSZWdpb24iOiJhd3MtdXMtZWFzdC0xIiwic2Vzc2lvbiI6ImV1Z2VuZS5sZWdpb24ubnljIiwicGF0IjoiZFBHM2pxMGQxbUpRTGd5akxheW9lYmZtZkhsZXhzbS1EdnhHR2N6Ull5RSIsInVzZXJJZCI6ImU1NmIzZWU0LTFmZDUtNGJlNS1hNjkwLWU5NzEwZDA2YjdhYiIsImlzcyI6Im1kX3BhdCIsInJlYWRPbmx5IjpmYWxzZSwidG9rZW5UeXBlIjoicmVhZF93cml0ZSIsImlhdCI6MTc2NTA4MzUzMn0.N6SRMQmdcvFzI3S2mUBuNtq2knCNn2zFTVa_bFPe-9k"

# Base GeoJSON with ED boundaries (geometry only)
# IMPORTANT: Use nyc-all-eds-complete.geojson (4,338 official ED boundaries)
# NEVER use nyc-all-eds-merged.geojson (contains 1,896 bad approximate convex hulls)
BASE_GEOJSON = os.path.expanduser("~/legion-dashboard/public/nycmap/nyc-all-eds-complete.geojson")

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connecting to MotherDuck...")
    conn = duckdb.connect(f"md:my_db?motherduck_token={TOKEN}")

    # Aggregate voter data by ADED - includes BOTH active-only counts AND all-voter counts
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Aggregating voter data from NYC Voter File...")

    query = '''
    SELECT
        aded,
        -- Use MODE() to get most common district assignment (handles redistricting inconsistencies)
        MODE(ad) as ad,
        MODE(sd) as sd,
        MODE(cd) as cd,
        MODE(council) as council,
        MODE(countycode) as countycode,
        CASE MODE(countycode)
            WHEN 3 THEN 'Bronx'
            WHEN 24 THEN 'Brooklyn'
            WHEN 31 THEN 'Manhattan'
            WHEN 41 THEN 'Queens'
            WHEN 43 THEN 'Staten Island'
        END as county,

        -- ===== ALL VOTERS (regardless of status) =====
        -- These show in EDs that have ONLY purged/inactive voters
        COUNT(*) as total_all,
        SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) as active_count,
        SUM(CASE WHEN status = 'P' THEN 1 ELSE 0 END) as purged_count,
        SUM(CASE WHEN status = 'I' THEN 1 ELSE 0 END) as inactive_count,

        -- ===== ACTIVE VOTERS ONLY (status='A') =====
        -- Primary counts for map display and analysis
        SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) as total,

        -- Party counts (ACTIVE voters only)
        SUM(CASE WHEN status = 'A' AND enrollment = 'DEM' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN status = 'A' AND enrollment = 'REP' THEN 1 ELSE 0 END) as rep,
        SUM(CASE WHEN status = 'A' AND enrollment = 'CON' THEN 1 ELSE 0 END) as con,
        SUM(CASE WHEN status = 'A' AND enrollment = 'WOR' THEN 1 ELSE 0 END) as wor,
        SUM(CASE WHEN status = 'A' AND enrollment = 'GRE' THEN 1 ELSE 0 END) as gre,
        SUM(CASE WHEN status = 'A' AND enrollment = 'LBT' THEN 1 ELSE 0 END) as lbt,
        SUM(CASE WHEN status = 'A' AND enrollment = 'IND' THEN 1 ELSE 0 END) as ind,
        SUM(CASE WHEN status = 'A' AND enrollment = 'BLK' THEN 1 ELSE 0 END) as blk,
        SUM(CASE WHEN status = 'A' AND enrollment NOT IN ('DEM','REP','CON','WOR','GRE','LBT','IND','BLK') THEN 1 ELSE 0 END) as oth,

        -- Primary vote universes (ACTIVE only)
        SUM(CASE WHEN status = 'A' AND primary_votes >= 1 THEN 1 ELSE 0 END) as single_prime,
        SUM(CASE WHEN status = 'A' AND primary_votes >= 2 THEN 1 ELSE 0 END) as double_prime,
        SUM(CASE WHEN status = 'A' AND primary_votes >= 3 THEN 1 ELSE 0 END) as triple_prime,

        -- General vote universes (ACTIVE only)
        SUM(CASE WHEN status = 'A' AND general_votes >= 1 THEN 1 ELSE 0 END) as single_gen,
        SUM(CASE WHEN status = 'A' AND general_votes >= 2 THEN 1 ELSE 0 END) as double_gen,
        SUM(CASE WHEN status = 'A' AND general_votes >= 3 THEN 1 ELSE 0 END) as triple_gen,

        -- Party counts for single prime (ACTIVE only)
        SUM(CASE WHEN status = 'A' AND enrollment = 'DEM' AND primary_votes >= 1 THEN 1 ELSE 0 END) as dem_sp,
        SUM(CASE WHEN status = 'A' AND enrollment = 'REP' AND primary_votes >= 1 THEN 1 ELSE 0 END) as rep_sp,
        SUM(CASE WHEN status = 'A' AND enrollment = 'BLK' AND primary_votes >= 1 THEN 1 ELSE 0 END) as blk_sp,

        -- Party counts for double prime (ACTIVE only)
        SUM(CASE WHEN status = 'A' AND enrollment = 'DEM' AND primary_votes >= 2 THEN 1 ELSE 0 END) as dem_dp,
        SUM(CASE WHEN status = 'A' AND enrollment = 'REP' AND primary_votes >= 2 THEN 1 ELSE 0 END) as rep_dp,
        SUM(CASE WHEN status = 'A' AND enrollment = 'BLK' AND primary_votes >= 2 THEN 1 ELSE 0 END) as blk_dp,

        -- Age groups (ACTIVE only)
        SUM(CASE WHEN status = 'A' AND age BETWEEN 18 AND 25 THEN 1 ELSE 0 END) as age_18_25,
        SUM(CASE WHEN status = 'A' AND age BETWEEN 26 AND 34 THEN 1 ELSE 0 END) as age_26_34,
        SUM(CASE WHEN status = 'A' AND age BETWEEN 35 AND 44 THEN 1 ELSE 0 END) as age_35_44,
        SUM(CASE WHEN status = 'A' AND age BETWEEN 45 AND 54 THEN 1 ELSE 0 END) as age_45_54,
        SUM(CASE WHEN status = 'A' AND age BETWEEN 55 AND 64 THEN 1 ELSE 0 END) as age_55_64,
        SUM(CASE WHEN status = 'A' AND age >= 65 THEN 1 ELSE 0 END) as age_65_plus,

        -- Age groups for single prime (ACTIVE only)
        SUM(CASE WHEN status = 'A' AND age BETWEEN 18 AND 25 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_18_25_sp,
        SUM(CASE WHEN status = 'A' AND age BETWEEN 26 AND 34 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_26_34_sp,
        SUM(CASE WHEN status = 'A' AND age BETWEEN 35 AND 44 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_35_44_sp,
        SUM(CASE WHEN status = 'A' AND age BETWEEN 45 AND 54 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_45_54_sp,
        SUM(CASE WHEN status = 'A' AND age BETWEEN 55 AND 64 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_55_64_sp,
        SUM(CASE WHEN status = 'A' AND age >= 65 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_65_plus_sp,

        -- Age groups for double prime (ACTIVE only)
        SUM(CASE WHEN status = 'A' AND age BETWEEN 18 AND 25 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_18_25_dp,
        SUM(CASE WHEN status = 'A' AND age BETWEEN 26 AND 34 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_26_34_dp,
        SUM(CASE WHEN status = 'A' AND age BETWEEN 35 AND 44 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_35_44_dp,
        SUM(CASE WHEN status = 'A' AND age BETWEEN 45 AND 54 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_45_54_dp,
        SUM(CASE WHEN status = 'A' AND age BETWEEN 55 AND 64 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_55_64_dp,
        SUM(CASE WHEN status = 'A' AND age >= 65 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_65_plus_dp,

        -- Race (ACTIVE only)
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'White' THEN 1 ELSE 0 END) as white,
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'Black' THEN 1 ELSE 0 END) as black,
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'Hispanic' THEN 1 ELSE 0 END) as hispanic,
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'Asian' THEN 1 ELSE 0 END) as asian,
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'MENA' THEN 1 ELSE 0 END) as mena,

        -- Race for single prime (ACTIVE only)
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'White' AND primary_votes >= 1 THEN 1 ELSE 0 END) as white_sp,
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'Black' AND primary_votes >= 1 THEN 1 ELSE 0 END) as black_sp,
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'Hispanic' AND primary_votes >= 1 THEN 1 ELSE 0 END) as hispanic_sp,
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'Asian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as asian_sp,
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'MENA' AND primary_votes >= 1 THEN 1 ELSE 0 END) as mena_sp,

        -- Race for double prime (ACTIVE only)
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'White' AND primary_votes >= 2 THEN 1 ELSE 0 END) as white_dp,
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'Black' AND primary_votes >= 2 THEN 1 ELSE 0 END) as black_dp,
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'Hispanic' AND primary_votes >= 2 THEN 1 ELSE 0 END) as hispanic_dp,
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'Asian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as asian_dp,
        SUM(CASE WHEN status = 'A' AND Likely_Race = 'MENA' AND primary_votes >= 2 THEN 1 ELSE 0 END) as mena_dp,

        -- Key ethnicities (ACTIVE only)
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Jewish' THEN 1 ELSE 0 END) as jewish,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Chinese' THEN 1 ELSE 0 END) as chinese,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Korean' THEN 1 ELSE 0 END) as korean,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Indian' THEN 1 ELSE 0 END) as indian,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Pakistani' THEN 1 ELSE 0 END) as pakistani,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Bangladeshi' THEN 1 ELSE 0 END) as bangladeshi,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Filipino' THEN 1 ELSE 0 END) as filipino,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Vietnamese' THEN 1 ELSE 0 END) as vietnamese,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Arab' THEN 1 ELSE 0 END) as arab,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Haitian' THEN 1 ELSE 0 END) as haitian,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Jamaican' THEN 1 ELSE 0 END) as jamaican,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Irish' THEN 1 ELSE 0 END) as irish,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Italian' THEN 1 ELSE 0 END) as italian,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Polish' THEN 1 ELSE 0 END) as polish,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Greek' THEN 1 ELSE 0 END) as greek,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Tibetan' THEN 1 ELSE 0 END) as tibetan,
        SUM(CASE WHEN status = 'A' AND Likely_Ethnicity = 'Sikh' THEN 1 ELSE 0 END) as sikh

    FROM NYS_Voters_2026
    WHERE countycode IN (3, 24, 31, 41, 43)  -- NYC counties only
    AND aded IS NOT NULL AND aded != ''
    GROUP BY aded
    ORDER BY aded
    '''

    df = conn.execute(query).fetchdf()
    active_total = df['total'].sum()
    all_total = df['total_all'].sum()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Got {len(df)} ED aggregations")
    print(f"[{datetime.now().strftime('%H:%M:%S')}]   Active voters: {active_total:,}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}]   All voters: {all_total:,} (includes {df['purged_count'].sum():,} purged, {df['inactive_count'].sum():,} inactive)")

    # Convert to lookup dict
    def convert_row(row):
        result = {}
        for k, v in row.items():
            if hasattr(v, 'item'):
                result[k] = v.item()
            elif v is None or (isinstance(v, float) and str(v) == 'nan'):
                result[k] = 0
            else:
                result[k] = v
        return result

    voter_data = {row['aded']: convert_row(row) for _, row in df.iterrows()}

    # Load base GeoJSON (has geometries)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading base GeoJSON from {BASE_GEOJSON}...")
    with open(BASE_GEOJSON, 'r') as f:
        geojson = json.load(f)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loaded {len(geojson['features'])} features")

    # VALIDATION: Ensure all features have ADED property
    missing_aded = 0
    for feature in geojson['features']:
        props = feature['properties']
        if not props.get('ADED'):
            # Compute from ad+ed or ElectDist
            ad = props.get('ad')
            ed = props.get('ed')
            if ad is not None and ed is not None:
                props['ADED'] = f"{int(ad)}-{int(ed):03d}"
            elif props.get('ElectDist'):
                s = str(int(props['ElectDist']))
                props['ADED'] = f"{int(s[:2])}-{int(s[2:]):03d}"
            else:
                missing_aded += 1

    if missing_aded > 0:
        print(f"WARNING: {missing_aded} features have no ADED and cannot be matched!")

    # Merge voter data into GeoJSON properties
    # IMPORTANT: Skip dissolved EDs (purged-only) - these are stale pre-2022 redistricting boundaries
    updated_active = 0
    dissolved_removed = 0
    no_data = 0

    filtered_features = []

    for feature in geojson['features']:
        props = feature['properties']

        # Get ADED - compute from ad+ed if not present
        aded = props.get('ADED')
        if not aded:
            ad = props.get('ad')
            ed = props.get('ed')
            if ad is not None and ed is not None:
                # Format: "AD-EEE" (e.g., "23-003")
                aded = f"{int(ad)}-{int(ed):03d}"
                props['ADED'] = aded  # Add ADED property for consistency

        if aded and aded in voter_data:
            data = voter_data[aded]
            has_active = data.get('total', 0) > 0

            if not has_active:
                # DISSOLVED ED: Has voters but ALL are purged/inactive
                # These are stale pre-2022 redistricting boundaries - REMOVE from output
                dissolved_removed += 1
                continue  # Skip this feature entirely

            # Update voter count properties from voter data
            # IMPORTANT: Do NOT overwrite geographic district fields from shapefile
            geographic_fields = {'ad', 'sd', 'cd', 'council', 'countycode', 'county', 'aded'}
            for key, value in data.items():
                if key not in geographic_fields:
                    props[key] = value
            props['name'] = f"ED {aded}"
            props['has_active_voters'] = True
            props['data_quality'] = 'good'
            updated_active += 1
            filtered_features.append(feature)
        else:
            # No voter data - keep as uninhabited ED
            keep_props = {'OBJECTID', 'ElectDist', 'Shape__Area', 'Shape__Length',
                         'ed', 'ad', 'ADED', 'sd', 'cd', 'council', 'countycode'}
            keys_to_remove = [k for k in props.keys() if k not in keep_props]
            for k in keys_to_remove:
                del props[k]

            props['ADED'] = aded if aded else None
            props['name'] = f"ED {aded}" if aded else "Unknown"
            props['total'] = 0
            props['total_all'] = 0
            props['purged_count'] = 0
            props['inactive_count'] = 0
            props['active_count'] = 0
            props['single_prime'] = 0
            props['double_prime'] = 0
            props['has_active_voters'] = False
            props['data_quality'] = 'no_voters'
            no_data += 1
            filtered_features.append(feature)

    # Replace features with filtered list (dissolved EDs removed)
    geojson['features'] = filtered_features

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Updated {updated_active} EDs with active voters")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] REMOVED {dissolved_removed} dissolved EDs (stale pre-2022 boundaries)")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {no_data} EDs uninhabited/no-match")

    # Add metadata
    geojson['metadata'] = {
        'generated': datetime.now().isoformat(),
        'source': 'MotherDuck NYC Voter File',
        'active_voters': int(df['total'].sum()),
        'all_voters': int(df['total_all'].sum()),
        'purged_voters': int(df['purged_count'].sum()),
        'inactive_voters': int(df['inactive_count'].sum()),
        'eds_with_active': updated_active,
        'eds_dissolved_removed': dissolved_removed,
        'eds_no_voters': no_data,
        'total_eds': updated_active + no_data,
        'note': 'Dissolved EDs (stale pre-2022 redistricting boundaries with only purged voters) have been removed. Primary counts use ACTIVE voters only.',
        'data_quality_values': {
            'good': 'Has active voters - use for analysis',
            'no_voters': 'No voters in voter file - uninhabited or new ED'
        }
    }

    # Write output
    output_path = os.path.join(os.path.dirname(__file__), 'nyc-eds.geojson')
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Writing to {output_path}...")

    with open(output_path, 'w') as f:
        json.dump(geojson, f, separators=(',', ':'))

    # Also create a slim version (no geometry, just properties) for fast loading
    slim_output = os.path.join(os.path.dirname(__file__), 'nyc-eds-properties.json')
    props_only = {f['properties']['ADED']: f['properties'] for f in geojson['features'] if f['properties'].get('ADED')}
    with open(slim_output, 'w') as f:
        json.dump(props_only, f, separators=(',', ':'))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Wrote slim properties to {slim_output}")

    # Verify
    file_size = os.path.getsize(output_path) / 1024 / 1024
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Done! Output: {file_size:.1f} MB")

    # VALIDATION: Check output feature count
    # Expected: ~4,036 (4,338 base - 302 dissolved EDs)
    expected_min = 4000
    if len(geojson['features']) < expected_min:
        print(f"ERROR: Output has only {len(geojson['features'])} features, expected at least {expected_min}!")
        print("Check if base GeoJSON was corrupted or ADED matching failed.")
    else:
        print(f"VALIDATION PASSED: {len(geojson['features'])} features (>= {expected_min})")

    # Sample verification
    sample_aded = "62-007"
    for feature in geojson['features']:
        if feature['properties'].get('ADED') == sample_aded:
            props = feature['properties']
            print(f"\nVerification - ED {sample_aded}:")
            print(f"  total: {props.get('total')}")
            print(f"  dem: {props.get('dem')}")
            print(f"  single_prime: {props.get('single_prime')}")
            break

    conn.close()

if __name__ == '__main__':
    main()
