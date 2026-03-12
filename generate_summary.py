#!/usr/bin/env python3
"""
Generate NYC ED Summary JSON from MotherDuck voter file.

This is the SINGLE SOURCE OF TRUTH for ED-level aggregations used by:
- Public static map (legion-dashboard/public/nycmap)
- DeckGL map (legion-atlas)
- Targeting tools
- Search

CRITICAL: Only ACTIVE DEMOCRATS (status='A' AND enrollment='DEM') are included.
This matches the map and Targeting Sheet (Democrats only for primary targeting).

Run: python3 generate_summary.py
Output: nyc-ed-summary.json
"""

import duckdb
import json
import os
from datetime import datetime

TOKEN = os.environ.get('MOTHERDUCK_TOKEN') or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImV1Z2VuZUBsZWdpb24ubnljIiwibWRSZWdpb24iOiJhd3MtdXMtZWFzdC0xIiwic2Vzc2lvbiI6ImV1Z2VuZS5sZWdpb24ubnljIiwicGF0IjoiZFBHM2pxMGQxbUpRTGd5akxheW9lYmZtZkhsZXhzbS1EdnhHR2N6Ull5RSIsInVzZXJJZCI6ImU1NmIzZWU0LTFmZDUtNGJlNS1hNjkwLWU5NzEwZDA2YjdhYiIsImlzcyI6Im1kX3BhdCIsInJlYWRPbmx5IjpmYWxzZSwidG9rZW5UeXBlIjoicmVhZF93cml0ZSIsImlhdCI6MTc2NTA4MzUzMn0.N6SRMQmdcvFzI3S2mUBuNtq2knCNn2zFTVa_bFPe-9k"

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connecting to MotherDuck...")
    conn = duckdb.connect(f"md:my_db?motherduck_token={TOKEN}")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating ED summary from NYC Voter File...")

    # Main aggregation query - ACTIVE VOTERS ONLY
    query = '''
    SELECT
        aded,
        MODE(ad) as ad,
        MODE(ed) as ed,
        MODE(sd) as sd,
        MODE(cd) as cd,
        MODE(council) as council,
        MODE(county) as county,

        -- Total
        COUNT(*) as total,

        -- Vote universes
        SUM(CASE WHEN primary_votes >= 1 THEN 1 ELSE 0 END) as single_prime,
        SUM(CASE WHEN primary_votes >= 2 THEN 1 ELSE 0 END) as double_prime,
        SUM(CASE WHEN primary_votes >= 3 THEN 1 ELSE 0 END) as triple_prime,
        SUM(CASE WHEN general_votes >= 1 THEN 1 ELSE 0 END) as single_gen,
        SUM(CASE WHEN general_votes >= 2 THEN 1 ELSE 0 END) as double_gen,
        SUM(CASE WHEN general_votes >= 3 THEN 1 ELSE 0 END) as triple_gen,

        -- Race (5 categories)
        SUM(CASE WHEN Likely_Race = 'White' THEN 1 ELSE 0 END) as white,
        SUM(CASE WHEN Likely_Race = 'White' AND primary_votes >= 1 THEN 1 ELSE 0 END) as white_sp,
        SUM(CASE WHEN Likely_Race = 'White' AND primary_votes >= 2 THEN 1 ELSE 0 END) as white_dp,
        SUM(CASE WHEN Likely_Race = 'Black' THEN 1 ELSE 0 END) as black,
        SUM(CASE WHEN Likely_Race = 'Black' AND primary_votes >= 1 THEN 1 ELSE 0 END) as black_sp,
        SUM(CASE WHEN Likely_Race = 'Black' AND primary_votes >= 2 THEN 1 ELSE 0 END) as black_dp,
        SUM(CASE WHEN Likely_Race = 'Hispanic' THEN 1 ELSE 0 END) as hispanic,
        SUM(CASE WHEN Likely_Race = 'Hispanic' AND primary_votes >= 1 THEN 1 ELSE 0 END) as hispanic_sp,
        SUM(CASE WHEN Likely_Race = 'Hispanic' AND primary_votes >= 2 THEN 1 ELSE 0 END) as hispanic_dp,
        SUM(CASE WHEN Likely_Race = 'Asian' THEN 1 ELSE 0 END) as asian,
        SUM(CASE WHEN Likely_Race = 'Asian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as asian_sp,
        SUM(CASE WHEN Likely_Race = 'Asian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as asian_dp,
        SUM(CASE WHEN Likely_Race = 'MENA' THEN 1 ELSE 0 END) as mena,
        SUM(CASE WHEN Likely_Race = 'MENA' AND primary_votes >= 1 THEN 1 ELSE 0 END) as mena_sp,
        SUM(CASE WHEN Likely_Race = 'MENA' AND primary_votes >= 2 THEN 1 ELSE 0 END) as mena_dp,

        -- Detailed ethnicities (base, _sp, _dp for each)
        SUM(CASE WHEN Likely_Ethnicity = 'Jewish' THEN 1 ELSE 0 END) as jewish,
        SUM(CASE WHEN Likely_Ethnicity = 'Jewish' AND primary_votes >= 1 THEN 1 ELSE 0 END) as jewish_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Jewish' AND primary_votes >= 2 THEN 1 ELSE 0 END) as jewish_dp,
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
        SUM(CASE WHEN Likely_Ethnicity = 'Russian' THEN 1 ELSE 0 END) as russian,
        SUM(CASE WHEN Likely_Ethnicity = 'Russian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as russian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Russian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as russian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Ukrainian' THEN 1 ELSE 0 END) as ukrainian,
        SUM(CASE WHEN Likely_Ethnicity = 'Ukrainian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as ukrainian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Ukrainian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as ukrainian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Armenian' THEN 1 ELSE 0 END) as armenian,
        SUM(CASE WHEN Likely_Ethnicity = 'Armenian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as armenian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Armenian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as armenian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Dutch' THEN 1 ELSE 0 END) as dutch,
        SUM(CASE WHEN Likely_Ethnicity = 'Dutch' AND primary_votes >= 1 THEN 1 ELSE 0 END) as dutch_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Dutch' AND primary_votes >= 2 THEN 1 ELSE 0 END) as dutch_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Romanian' THEN 1 ELSE 0 END) as romanian,
        SUM(CASE WHEN Likely_Ethnicity = 'Romanian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as romanian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Romanian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as romanian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Hungarian' THEN 1 ELSE 0 END) as hungarian,
        SUM(CASE WHEN Likely_Ethnicity = 'Hungarian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as hungarian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Hungarian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as hungarian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Serbian' THEN 1 ELSE 0 END) as serbian,
        SUM(CASE WHEN Likely_Ethnicity = 'Serbian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as serbian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Serbian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as serbian_dp,

        -- Asian ethnicities
        SUM(CASE WHEN Likely_Ethnicity = 'Chinese' THEN 1 ELSE 0 END) as chinese,
        SUM(CASE WHEN Likely_Ethnicity = 'Chinese' AND primary_votes >= 1 THEN 1 ELSE 0 END) as chinese_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Chinese' AND primary_votes >= 2 THEN 1 ELSE 0 END) as chinese_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Korean' THEN 1 ELSE 0 END) as korean,
        SUM(CASE WHEN Likely_Ethnicity = 'Korean' AND primary_votes >= 1 THEN 1 ELSE 0 END) as korean_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Korean' AND primary_votes >= 2 THEN 1 ELSE 0 END) as korean_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Japanese' THEN 1 ELSE 0 END) as japanese,
        SUM(CASE WHEN Likely_Ethnicity = 'Japanese' AND primary_votes >= 1 THEN 1 ELSE 0 END) as japanese_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Japanese' AND primary_votes >= 2 THEN 1 ELSE 0 END) as japanese_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Filipino' THEN 1 ELSE 0 END) as filipino,
        SUM(CASE WHEN Likely_Ethnicity = 'Filipino' AND primary_votes >= 1 THEN 1 ELSE 0 END) as filipino_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Filipino' AND primary_votes >= 2 THEN 1 ELSE 0 END) as filipino_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Vietnamese' THEN 1 ELSE 0 END) as vietnamese,
        SUM(CASE WHEN Likely_Ethnicity = 'Vietnamese' AND primary_votes >= 1 THEN 1 ELSE 0 END) as vietnamese_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Vietnamese' AND primary_votes >= 2 THEN 1 ELSE 0 END) as vietnamese_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Tibetan' THEN 1 ELSE 0 END) as tibetan,
        SUM(CASE WHEN Likely_Ethnicity = 'Tibetan' AND primary_votes >= 1 THEN 1 ELSE 0 END) as tibetan_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Tibetan' AND primary_votes >= 2 THEN 1 ELSE 0 END) as tibetan_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Burmese' THEN 1 ELSE 0 END) as burmese,
        SUM(CASE WHEN Likely_Ethnicity = 'Burmese' AND primary_votes >= 1 THEN 1 ELSE 0 END) as burmese_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Burmese' AND primary_votes >= 2 THEN 1 ELSE 0 END) as burmese_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Cambodian' THEN 1 ELSE 0 END) as cambodian,
        SUM(CASE WHEN Likely_Ethnicity = 'Cambodian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as cambodian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Cambodian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as cambodian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Indonesian' THEN 1 ELSE 0 END) as indonesian,
        SUM(CASE WHEN Likely_Ethnicity = 'Indonesian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as indonesian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Indonesian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as indonesian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Laotian' THEN 1 ELSE 0 END) as laotian,
        SUM(CASE WHEN Likely_Ethnicity = 'Laotian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as laotian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Laotian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as laotian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Thai' THEN 1 ELSE 0 END) as thai,
        SUM(CASE WHEN Likely_Ethnicity = 'Thai' AND primary_votes >= 1 THEN 1 ELSE 0 END) as thai_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Thai' AND primary_votes >= 2 THEN 1 ELSE 0 END) as thai_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Mongolian' THEN 1 ELSE 0 END) as mongolian,
        SUM(CASE WHEN Likely_Ethnicity = 'Mongolian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as mongolian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Mongolian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as mongolian_dp,

        -- South Asian
        SUM(CASE WHEN Likely_Ethnicity = 'Indian' THEN 1 ELSE 0 END) as indian,
        SUM(CASE WHEN Likely_Ethnicity = 'Indian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as indian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Indian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as indian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Pakistani' THEN 1 ELSE 0 END) as pakistani,
        SUM(CASE WHEN Likely_Ethnicity = 'Pakistani' AND primary_votes >= 1 THEN 1 ELSE 0 END) as pakistani_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Pakistani' AND primary_votes >= 2 THEN 1 ELSE 0 END) as pakistani_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Bangladeshi' THEN 1 ELSE 0 END) as bangladeshi,
        SUM(CASE WHEN Likely_Ethnicity = 'Bangladeshi' AND primary_votes >= 1 THEN 1 ELSE 0 END) as bangladeshi_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Bangladeshi' AND primary_votes >= 2 THEN 1 ELSE 0 END) as bangladeshi_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Sikh' THEN 1 ELSE 0 END) as sikh,
        SUM(CASE WHEN Likely_Ethnicity = 'Sikh' AND primary_votes >= 1 THEN 1 ELSE 0 END) as sikh_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Sikh' AND primary_votes >= 2 THEN 1 ELSE 0 END) as sikh_dp,

        -- Caribbean/African
        SUM(CASE WHEN Likely_Ethnicity = 'Haitian' THEN 1 ELSE 0 END) as haitian,
        SUM(CASE WHEN Likely_Ethnicity = 'Haitian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as haitian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Haitian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as haitian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Jamaican' THEN 1 ELSE 0 END) as jamaican,
        SUM(CASE WHEN Likely_Ethnicity = 'Jamaican' AND primary_votes >= 1 THEN 1 ELSE 0 END) as jamaican_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Jamaican' AND primary_votes >= 2 THEN 1 ELSE 0 END) as jamaican_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Ghanaian' THEN 1 ELSE 0 END) as ghanaian,
        SUM(CASE WHEN Likely_Ethnicity = 'Ghanaian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as ghanaian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Ghanaian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as ghanaian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Nigerian' THEN 1 ELSE 0 END) as nigerian,
        SUM(CASE WHEN Likely_Ethnicity = 'Nigerian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as nigerian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Nigerian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as nigerian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Ethiopian' THEN 1 ELSE 0 END) as ethiopian,
        SUM(CASE WHEN Likely_Ethnicity = 'Ethiopian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as ethiopian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Ethiopian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as ethiopian_dp,

        -- MENA ethnicities
        SUM(CASE WHEN Likely_Ethnicity = 'Arab' THEN 1 ELSE 0 END) as arab,
        SUM(CASE WHEN Likely_Ethnicity = 'Arab' AND primary_votes >= 1 THEN 1 ELSE 0 END) as arab_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Arab' AND primary_votes >= 2 THEN 1 ELSE 0 END) as arab_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Persian' THEN 1 ELSE 0 END) as persian,
        SUM(CASE WHEN Likely_Ethnicity = 'Persian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as persian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Persian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as persian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Turkish' THEN 1 ELSE 0 END) as turkish,
        SUM(CASE WHEN Likely_Ethnicity = 'Turkish' AND primary_votes >= 1 THEN 1 ELSE 0 END) as turkish_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Turkish' AND primary_votes >= 2 THEN 1 ELSE 0 END) as turkish_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Afghan' THEN 1 ELSE 0 END) as afghan,
        SUM(CASE WHEN Likely_Ethnicity = 'Afghan' AND primary_votes >= 1 THEN 1 ELSE 0 END) as afghan_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Afghan' AND primary_votes >= 2 THEN 1 ELSE 0 END) as afghan_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Somali' THEN 1 ELSE 0 END) as somali,
        SUM(CASE WHEN Likely_Ethnicity = 'Somali' AND primary_votes >= 1 THEN 1 ELSE 0 END) as somali_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Somali' AND primary_votes >= 2 THEN 1 ELSE 0 END) as somali_dp,

        -- Uncoded (race identified but no specific ethnicity)
        SUM(CASE WHEN Likely_Ethnicity = 'Uncoded - White' THEN 1 ELSE 0 END) as uncoded_white,
        SUM(CASE WHEN Likely_Ethnicity = 'Uncoded - White' AND primary_votes >= 1 THEN 1 ELSE 0 END) as uncoded_white_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Uncoded - White' AND primary_votes >= 2 THEN 1 ELSE 0 END) as uncoded_white_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Uncoded - Black' THEN 1 ELSE 0 END) as uncoded_black,
        SUM(CASE WHEN Likely_Ethnicity = 'Uncoded - Black' AND primary_votes >= 1 THEN 1 ELSE 0 END) as uncoded_black_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Uncoded - Black' AND primary_votes >= 2 THEN 1 ELSE 0 END) as uncoded_black_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Uncoded - Asian' THEN 1 ELSE 0 END) as uncoded_asian,
        SUM(CASE WHEN Likely_Ethnicity = 'Uncoded - Asian' AND primary_votes >= 1 THEN 1 ELSE 0 END) as uncoded_asian_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Uncoded - Asian' AND primary_votes >= 2 THEN 1 ELSE 0 END) as uncoded_asian_dp,
        SUM(CASE WHEN Likely_Ethnicity = 'Uncoded - Hispanic' THEN 1 ELSE 0 END) as uncoded_hispanic,
        SUM(CASE WHEN Likely_Ethnicity = 'Uncoded - Hispanic' AND primary_votes >= 1 THEN 1 ELSE 0 END) as uncoded_hispanic_sp,
        SUM(CASE WHEN Likely_Ethnicity = 'Uncoded - Hispanic' AND primary_votes >= 2 THEN 1 ELSE 0 END) as uncoded_hispanic_dp,

        -- Age groups
        SUM(CASE WHEN age BETWEEN 18 AND 25 THEN 1 ELSE 0 END) as age_18_25,
        SUM(CASE WHEN age BETWEEN 18 AND 25 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_18_25_sp,
        SUM(CASE WHEN age BETWEEN 18 AND 25 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_18_25_dp,
        SUM(CASE WHEN age BETWEEN 26 AND 34 THEN 1 ELSE 0 END) as age_26_34,
        SUM(CASE WHEN age BETWEEN 26 AND 34 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_26_34_sp,
        SUM(CASE WHEN age BETWEEN 26 AND 34 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_26_34_dp,
        SUM(CASE WHEN age BETWEEN 35 AND 44 THEN 1 ELSE 0 END) as age_35_44,
        SUM(CASE WHEN age BETWEEN 35 AND 44 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_35_44_sp,
        SUM(CASE WHEN age BETWEEN 35 AND 44 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_35_44_dp,
        SUM(CASE WHEN age BETWEEN 45 AND 54 THEN 1 ELSE 0 END) as age_45_54,
        SUM(CASE WHEN age BETWEEN 45 AND 54 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_45_54_sp,
        SUM(CASE WHEN age BETWEEN 45 AND 54 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_45_54_dp,
        SUM(CASE WHEN age BETWEEN 55 AND 64 THEN 1 ELSE 0 END) as age_55_64,
        SUM(CASE WHEN age BETWEEN 55 AND 64 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_55_64_sp,
        SUM(CASE WHEN age BETWEEN 55 AND 64 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_55_64_dp,
        SUM(CASE WHEN age >= 65 THEN 1 ELSE 0 END) as age_65_plus,
        SUM(CASE WHEN age >= 65 AND primary_votes >= 1 THEN 1 ELSE 0 END) as age_65_plus_sp,
        SUM(CASE WHEN age >= 65 AND primary_votes >= 2 THEN 1 ELSE 0 END) as age_65_plus_dp,

        -- Turnout by year (parsed from voterhistory)
        SUM(CASE WHEN voterhistory LIKE '%2020 General%' THEN 1 ELSE 0 END) as turnout_2020,
        SUM(CASE WHEN voterhistory LIKE '%2021 %' AND voterhistory LIKE '%General%' THEN 1 ELSE 0 END) as turnout_2021,
        SUM(CASE WHEN voterhistory LIKE '%2022 General%' THEN 1 ELSE 0 END) as turnout_2022,
        SUM(CASE WHEN voterhistory LIKE '%2023 General%' THEN 1 ELSE 0 END) as turnout_2023,
        SUM(CASE WHEN voterhistory LIKE '%2024 General%' THEN 1 ELSE 0 END) as turnout_2024,
        SUM(CASE WHEN voterhistory LIKE '%2025 General%' THEN 1 ELSE 0 END) as turnout_2025

    FROM NYS_Voters_2026
    WHERE countycode IN (3, 24, 31, 41, 43)  -- NYC only
    AND status = 'A'           -- Active voters only
    AND enrollment = 'DEM'     -- Democrats only (matches Targeting Sheet)
    AND aded IS NOT NULL AND aded != ''
    GROUP BY aded
    HAVING COUNT(*) > 0  -- Exclude dissolved EDs (0 active voters)
    ORDER BY aded
    '''

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Running aggregation query...")
    df = conn.execute(query).fetchdf()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Got {len(df)} EDs, {df['total'].sum():,} active voters")

    # Convert to list of dicts
    def convert_row(row):
        result = {}
        for k, v in row.items():
            if hasattr(v, 'item'):
                result[k] = int(v.item()) if isinstance(v.item(), (int, float)) else v.item()
            elif v is None or (isinstance(v, float) and str(v) == 'nan'):
                result[k] = 0
            else:
                result[k] = int(v) if isinstance(v, (int, float)) else v
        return result

    data = [convert_row(row) for _, row in df.iterrows()]

    # Write output
    output_path = os.path.join(os.path.dirname(__file__), 'nyc-ed-summary.json')
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Writing to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    file_size = os.path.getsize(output_path) / 1024 / 1024
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Done! Output: {file_size:.1f} MB, {len(data)} EDs")

    # Verification
    print(f"\nSample ED (first):")
    sample = data[0]
    print(f"  aded: {sample['aded']}")
    print(f"  total: {sample['total']}")
    print(f"  single_prime: {sample['single_prime']}")
    print(f"  white: {sample['white']}")
    print(f"  turnout_2024: {sample['turnout_2024']}")

    conn.close()

if __name__ == '__main__':
    main()
