#!/usr/bin/env python3
"""
Generate NYC ED GeoJSON from MotherDuck voter file.

This script:
1. Loads ED boundary geometries from the base GeoJSON (NYC GIS source)
2. Aggregates fresh voter data from MotherDuck
3. Merges them into a complete GeoJSON with all properties
4. Outputs to nyc-eds.geojson for deployment

CRITICAL: All counts are ACTIVE DEMOCRATS ONLY (status='A' AND enrollment='DEM').
This matches the Targeting Sheet which shows Democrats only.
- 3.2M active Democrats in NYC
- Maps and Targeting Sheet show consistent data

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
# Source: ArcGIS NYC DCP - has 100% coverage of voter file ADEDs
# The NYT 2024 shapefile is missing 69 EDs (36,890 voters)
_BASE_PRIMARY = os.path.expanduser("~/Downloads/ed_shapefile/arcgis_dcp_nyc_eds_complete.geojson")
_BASE_FALLBACK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nyc-eds.geojson")
BASE_GEOJSON = _BASE_PRIMARY if os.path.exists(_BASE_PRIMARY) else _BASE_FALLBACK

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

        -- ===== ALL COUNTS ARE DEMOCRATS ONLY =====
        -- (WHERE clause filters to status='A' AND enrollment='DEM')
        COUNT(*) as total,

        -- Primary vote universes
        SUM(CASE WHEN primary_votes >= 1 THEN 1 ELSE 0 END) as single_prime,
        SUM(CASE WHEN primary_votes >= 2 THEN 1 ELSE 0 END) as double_prime,
        SUM(CASE WHEN primary_votes >= 3 THEN 1 ELSE 0 END) as triple_prime,

        -- General vote universes
        SUM(CASE WHEN general_votes >= 1 THEN 1 ELSE 0 END) as single_gen,
        SUM(CASE WHEN general_votes >= 2 THEN 1 ELSE 0 END) as double_gen,
        SUM(CASE WHEN general_votes >= 3 THEN 1 ELSE 0 END) as triple_gen,

        -- Age groups
        SUM(CASE WHEN age BETWEEN 18 AND 25 THEN 1 ELSE 0 END) as age_18_25,
        SUM(CASE WHEN age BETWEEN 26 AND 34 THEN 1 ELSE 0 END) as age_26_34,
        SUM(CASE WHEN age BETWEEN 35 AND 44 THEN 1 ELSE 0 END) as age_35_44,
        SUM(CASE WHEN age BETWEEN 45 AND 54 THEN 1 ELSE 0 END) as age_45_54,
        SUM(CASE WHEN age BETWEEN 55 AND 64 THEN 1 ELSE 0 END) as age_55_64,
        SUM(CASE WHEN age >= 65 THEN 1 ELSE 0 END) as age_65_plus,

        -- Age groups for single prime
        SUM(CASE WHEN age BETWEEN 18 AND 25 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_18_25_sp,
        SUM(CASE WHEN age BETWEEN 26 AND 34 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_26_34_sp,
        SUM(CASE WHEN age BETWEEN 35 AND 44 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_35_44_sp,
        SUM(CASE WHEN age BETWEEN 45 AND 54 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_45_54_sp,
        SUM(CASE WHEN age BETWEEN 55 AND 64 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_55_64_sp,
        SUM(CASE WHEN age >= 65 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_65_plus_sp,

        -- Age groups for double prime
        SUM(CASE WHEN age BETWEEN 18 AND 25 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_18_25_dp,
        SUM(CASE WHEN age BETWEEN 26 AND 34 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_26_34_dp,
        SUM(CASE WHEN age BETWEEN 35 AND 44 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_35_44_dp,
        SUM(CASE WHEN age BETWEEN 45 AND 54 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_45_54_dp,
        SUM(CASE WHEN age BETWEEN 55 AND 64 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_55_64_dp,
        SUM(CASE WHEN age >= 65 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_65_plus_dp,

        -- Race
        SUM(CASE WHEN Likely_Race = 'White' THEN 1 ELSE 0 END) as white,
        SUM(CASE WHEN Likely_Race = 'Black' THEN 1 ELSE 0 END) as black,
        SUM(CASE WHEN Likely_Race = 'Hispanic' THEN 1 ELSE 0 END) as hispanic,
        SUM(CASE WHEN Likely_Race = 'Asian' THEN 1 ELSE 0 END) as asian,
        SUM(CASE WHEN Likely_Race = 'MENA' THEN 1 ELSE 0 END) as mena,

        -- Race for single prime
        SUM(CASE WHEN Likely_Race = 'White' AND primary_votes >= 1 THEN 1 ELSE 0 END) as white_sp,
        SUM(CASE WHEN Likely_Race = 'Black' AND primary_votes >= 1 THEN 1 ELSE 0 END) as black_sp,
        SUM(CASE WHEN Likely_Race = 'Hispanic' AND primary_votes >= 1 THEN 1 ELSE 0 END) as hispanic_sp,
        SUM(CASE WHEN Likely_Race = 'Asian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as asian_sp,
        SUM(CASE WHEN Likely_Race = 'MENA' AND primary_votes >= 1 THEN 1 ELSE 0 END) as mena_sp,

        -- Race for double prime
        SUM(CASE WHEN Likely_Race = 'White' AND primary_votes >= 2 THEN 1 ELSE 0 END) as white_dp,
        SUM(CASE WHEN Likely_Race = 'Black' AND primary_votes >= 2 THEN 1 ELSE 0 END) as black_dp,
        SUM(CASE WHEN Likely_Race = 'Hispanic' AND primary_votes >= 2 THEN 1 ELSE 0 END) as hispanic_dp,
        SUM(CASE WHEN Likely_Race = 'Asian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as asian_dp,
        SUM(CASE WHEN Likely_Race = 'MENA' AND primary_votes >= 2 THEN 1 ELSE 0 END) as mena_dp,

        -- Key ethnicities (total, single prime, double prime)
        SUM(CASE WHEN Likely_Ethnicity = 'Jewish' THEN 1 ELSE 0 END) as jewish,
        SUM(CASE WHEN Likely_Ethnicity = 'Jewish' AND primary_votes >= 1 THEN 1 ELSE 0 END) as jewish_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Jewish' AND primary_votes >= 2 THEN 1 ELSE 0 END) as jewish_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Chinese' THEN 1 ELSE 0 END) as chinese,
        SUM(CASE WHEN Likely_Ethnicity = 'Chinese' AND primary_votes >= 1 THEN 1 ELSE 0 END) as chinese_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Chinese' AND primary_votes >= 2 THEN 1 ELSE 0 END) as chinese_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Korean' THEN 1 ELSE 0 END) as korean,
        SUM(CASE WHEN Likely_Ethnicity = 'Korean' AND primary_votes >= 1 THEN 1 ELSE 0 END) as korean_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Korean' AND primary_votes >= 2 THEN 1 ELSE 0 END) as korean_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Indian' THEN 1 ELSE 0 END) as indian,
        SUM(CASE WHEN Likely_Ethnicity = 'Indian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as indian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Indian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as indian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Pakistani' THEN 1 ELSE 0 END) as pakistani,
        SUM(CASE WHEN Likely_Ethnicity = 'Pakistani' AND primary_votes >= 1 THEN 1 ELSE 0 END) as pakistani_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Pakistani' AND primary_votes >= 2 THEN 1 ELSE 0 END) as pakistani_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Bangladeshi' THEN 1 ELSE 0 END) as bangladeshi,
        SUM(CASE WHEN Likely_Ethnicity = 'Bangladeshi' AND primary_votes >= 1 THEN 1 ELSE 0 END) as bangladeshi_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Bangladeshi' AND primary_votes >= 2 THEN 1 ELSE 0 END) as bangladeshi_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Filipino' THEN 1 ELSE 0 END) as filipino,
        SUM(CASE WHEN Likely_Ethnicity = 'Filipino' AND primary_votes >= 1 THEN 1 ELSE 0 END) as filipino_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Filipino' AND primary_votes >= 2 THEN 1 ELSE 0 END) as filipino_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Vietnamese' THEN 1 ELSE 0 END) as vietnamese,
        SUM(CASE WHEN Likely_Ethnicity = 'Vietnamese' AND primary_votes >= 1 THEN 1 ELSE 0 END) as vietnamese_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Vietnamese' AND primary_votes >= 2 THEN 1 ELSE 0 END) as vietnamese_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Arab' THEN 1 ELSE 0 END) as arab,
        SUM(CASE WHEN Likely_Ethnicity = 'Arab' AND primary_votes >= 1 THEN 1 ELSE 0 END) as arab_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Arab' AND primary_votes >= 2 THEN 1 ELSE 0 END) as arab_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Haitian' THEN 1 ELSE 0 END) as haitian,
        SUM(CASE WHEN Likely_Ethnicity = 'Haitian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as haitian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Haitian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as haitian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Jamaican' THEN 1 ELSE 0 END) as jamaican,
        SUM(CASE WHEN Likely_Ethnicity = 'Jamaican' AND primary_votes >= 1 THEN 1 ELSE 0 END) as jamaican_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Jamaican' AND primary_votes >= 2 THEN 1 ELSE 0 END) as jamaican_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Irish' THEN 1 ELSE 0 END) as irish,
        SUM(CASE WHEN Likely_Ethnicity = 'Irish' AND primary_votes >= 1 THEN 1 ELSE 0 END) as irish_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Irish' AND primary_votes >= 2 THEN 1 ELSE 0 END) as irish_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Italian' THEN 1 ELSE 0 END) as italian,
        SUM(CASE WHEN Likely_Ethnicity = 'Italian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as italian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Italian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as italian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Polish' THEN 1 ELSE 0 END) as polish,
        SUM(CASE WHEN Likely_Ethnicity = 'Polish' AND primary_votes >= 1 THEN 1 ELSE 0 END) as polish_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Polish' AND primary_votes >= 2 THEN 1 ELSE 0 END) as polish_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Greek' THEN 1 ELSE 0 END) as greek,
        SUM(CASE WHEN Likely_Ethnicity = 'Greek' AND primary_votes >= 1 THEN 1 ELSE 0 END) as greek_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Greek' AND primary_votes >= 2 THEN 1 ELSE 0 END) as greek_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Tibetan' THEN 1 ELSE 0 END) as tibetan,
        SUM(CASE WHEN Likely_Ethnicity = 'Tibetan' AND primary_votes >= 1 THEN 1 ELSE 0 END) as tibetan_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Tibetan' AND primary_votes >= 2 THEN 1 ELSE 0 END) as tibetan_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Sikh' THEN 1 ELSE 0 END) as sikh,
        SUM(CASE WHEN Likely_Ethnicity = 'Sikh' AND primary_votes >= 1 THEN 1 ELSE 0 END) as sikh_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Sikh' AND primary_votes >= 2 THEN 1 ELSE 0 END) as sikh_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Ethiopian' THEN 1 ELSE 0 END) as ethiopian,
        SUM(CASE WHEN Likely_Ethnicity = 'Ethiopian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as ethiopian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Ethiopian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as ethiopian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Ghanaian' THEN 1 ELSE 0 END) as ghanaian,
        SUM(CASE WHEN Likely_Ethnicity = 'Ghanaian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as ghanaian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Ghanaian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as ghanaian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Japanese' THEN 1 ELSE 0 END) as japanese,
        SUM(CASE WHEN Likely_Ethnicity = 'Japanese' AND primary_votes >= 1 THEN 1 ELSE 0 END) as japanese_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Japanese' AND primary_votes >= 2 THEN 1 ELSE 0 END) as japanese_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Nigerian' THEN 1 ELSE 0 END) as nigerian,
        SUM(CASE WHEN Likely_Ethnicity = 'Nigerian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as nigerian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Nigerian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as nigerian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Persian' THEN 1 ELSE 0 END) as persian,
        SUM(CASE WHEN Likely_Ethnicity = 'Persian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as persian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Persian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as persian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Russian' THEN 1 ELSE 0 END) as russian,
        SUM(CASE WHEN Likely_Ethnicity = 'Russian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as russian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Russian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as russian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Turkish' THEN 1 ELSE 0 END) as turkish,
        SUM(CASE WHEN Likely_Ethnicity = 'Turkish' AND primary_votes >= 1 THEN 1 ELSE 0 END) as turkish_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Turkish' AND primary_votes >= 2 THEN 1 ELSE 0 END) as turkish_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Ukrainian' THEN 1 ELSE 0 END) as ukrainian,
        SUM(CASE WHEN Likely_Ethnicity = 'Ukrainian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as ukrainian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Ukrainian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as ukrainian_dp,

        -- ED number (handy)
        MODE(ed) as ed,

        -- Primary turnout by year (any-format match: catches "20YYMMDD PR(", "Primary Election YYYY", "20YY Primary Election")
        SUM(CASE WHEN voterhistory ILIKE '%20200623 PR%' OR voterhistory ILIKE '%PR 20200623%' OR voterhistory ILIKE '%2020 Primary Election%' OR voterhistory ILIKE '%Primary Election 2020%' THEN 1 ELSE 0 END) as turnout_2020,
        SUM(CASE WHEN voterhistory ILIKE '%20210622 PR%' OR voterhistory ILIKE '%PR 20210622%' OR voterhistory ILIKE '%2021 Primary Election%' OR voterhistory ILIKE '%Primary Election 2021%' THEN 1 ELSE 0 END) as turnout_2021,
        SUM(CASE WHEN voterhistory ILIKE '%20220628 PR%' OR voterhistory ILIKE '%PR 20220628%' OR voterhistory ILIKE '%20220823 PR%' OR voterhistory ILIKE '%PR 20220823%' OR voterhistory ILIKE '%2022 Primary Election%' OR voterhistory ILIKE '%Primary Election 2022%' THEN 1 ELSE 0 END) as turnout_2022,
        SUM(CASE WHEN voterhistory ILIKE '%20230627 PR%' OR voterhistory ILIKE '%PR 20230627%' OR voterhistory ILIKE '%2023 Primary Election%' OR voterhistory ILIKE '%Primary Election 2023%' THEN 1 ELSE 0 END) as turnout_2023,
        SUM(CASE WHEN voterhistory ILIKE '%20240625 PR%' OR voterhistory ILIKE '%PR 20240625%' OR voterhistory ILIKE '%20240402 PP%' OR voterhistory ILIKE '%PP 20240402%' OR voterhistory ILIKE '%2024 Primary Election%' OR voterhistory ILIKE '%Primary Election 2024%' THEN 1 ELSE 0 END) as turnout_2024,
        SUM(CASE WHEN voterhistory ILIKE '%20250624 PR%' OR voterhistory ILIKE '%PR 20250624%' OR voterhistory ILIKE '%2025 Primary Election%' OR voterhistory ILIKE '%Primary Election 2025%' THEN 1 ELSE 0 END) as turnout_2025,
        SUM(CASE WHEN voterhistory ILIKE '%20260624 PR%' OR voterhistory ILIKE '%PR 20260624%' OR voterhistory ILIKE '%2026 Primary Election%' OR voterhistory ILIKE '%Primary Election 2026%' THEN 1 ELSE 0 END) as turnout_2026

    FROM NYS_Voters_2026
    WHERE countycode IN (3, 24, 31, 41, 43)  -- NYC counties only
    AND aded IS NOT NULL AND aded != ''
    AND status = 'A'           -- Active voters only
    AND enrollment = 'DEM'     -- Democrats only (matches Targeting Sheet)
    GROUP BY aded
    ORDER BY aded
    '''

    df = conn.execute(query).fetchdf()
    dem_total = df['total'].sum()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Got {len(df)} ED aggregations")
    print(f"[{datetime.now().strftime('%H:%M:%S')}]   Active Democrats: {dem_total:,}")

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

    # Pull census data per ED and merge into voter_data
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading census per ED...")
    census_df = conn.execute("""
        SELECT aded, median_income, pct_poverty, pct_bachelors, pct_rent_burdened
        FROM nyc_ed_census
    """).fetchdf()
    for _, row in census_df.iterrows():
        aded = row['aded']
        if aded in voter_data:
            voter_data[aded]['median_income'] = None if row['median_income'] is None else float(row['median_income'])
            voter_data[aded]['pct_poverty'] = None if row['pct_poverty'] is None else float(row['pct_poverty'])
            voter_data[aded]['pct_bachelors'] = None if row['pct_bachelors'] is None else float(row['pct_bachelors'])
            voter_data[aded]['pct_rent_burdened'] = None if row['pct_rent_burdened'] is None else float(row['pct_rent_burdened'])
    print(f"[{datetime.now().strftime('%H:%M:%S')}]   Joined census for {len(census_df)} EDs")

    # Load base GeoJSON (has geometries)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading base GeoJSON from {BASE_GEOJSON}...")
    with open(BASE_GEOJSON, 'r') as f:
        geojson = json.load(f)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loaded {len(geojson['features'])} features")

    # VALIDATION: Ensure all features have ADED property
    # ArcGIS format uses ElectDist (e.g., 23003 = AD 23, ED 003)
    # NYT format uses ADED (e.g., "23-003")
    missing_aded = 0
    for feature in geojson['features']:
        props = feature['properties']
        if not props.get('ADED'):
            # Try ElectDist first (ArcGIS format)
            if props.get('ElectDist'):
                electdist = int(props['ElectDist'])
                s = str(electdist)
                if len(s) >= 4:
                    # Format: AAEEE (e.g., 23003 = AD 23, ED 003)
                    ad = int(s[:-3]) if len(s) > 3 else int(s[0])
                    ed = int(s[-3:])
                    props['ADED'] = f"{ad}-{ed:03d}"
                else:
                    missing_aded += 1
            # Try ad+ed (some formats)
            elif props.get('ad') is not None and props.get('ed') is not None:
                props['ADED'] = f"{int(props['ad'])}-{int(props['ed']):03d}"
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
            # Update properties from voter data
            # Write ALL fields from MotherDuck including districts (ad, sd, cd, council)
            for key, value in data.items():
                if key != 'aded':  # Keep ADED from shapefile (already computed)
                    props[key] = value
            props['name'] = f"ED {aded}"
            props['has_active_voters'] = True
            props['data_quality'] = 'good'
            updated_active += 1
            filtered_features.append(feature)
        else:
            # ED exists in shapefile but no active Democrats in voter file
            # This could be:
            # 1. Non-residential ED (parks, water, cemeteries)
            # 2. ED with only Republicans/independents
            # 3. Stale ED where voters were reassigned (redistricting)
            # INCLUDE these EDs with 0 values so boundaries show on map
            props['name'] = f"ED {aded}"
            props['ADED'] = aded
            # Parse AD from ADED (e.g., "30-055" -> 30)
            if aded:
                try:
                    props['ad'] = int(aded.split('-')[0])
                except:
                    pass
            props['total'] = 0
            props['single_prime'] = 0
            props['double_prime'] = 0
            props['triple_prime'] = 0
            props['has_active_voters'] = False
            props['data_quality'] = 'no_voters'
            no_data += 1
            filtered_features.append(feature)  # INCLUDE in output

    # Replace features with filtered list (dissolved EDs removed)
    geojson['features'] = filtered_features

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Updated {updated_active} EDs with active voters")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] REMOVED {dissolved_removed} dissolved EDs (stale pre-2022 boundaries)")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {no_data} EDs uninhabited/no-match")

    # Add metadata
    geojson['metadata'] = {
        'generated': datetime.now().isoformat(),
        'source': 'MotherDuck NYC Voter File',
        'population': 'Active Democrats only (status=A, enrollment=DEM)',
        'active_democrats': int(df['total'].sum()),
        'single_prime': int(df['single_prime'].sum()),
        'double_prime': int(df['double_prime'].sum()),
        'eds_with_dems': updated_active,
        'eds_dissolved_removed': dissolved_removed,
        'eds_no_dems': no_data,
        'total_eds': updated_active + no_data,
        'note': 'This GeoJSON contains DEMOCRATS ONLY to match Targeting Sheet. Non-Dems and inactive voters excluded.',
        'data_quality_values': {
            'good': 'Has active Democrats - use for analysis',
            'no_voters': 'No Democrats in voter file - uninhabited or non-Dem ED'
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
