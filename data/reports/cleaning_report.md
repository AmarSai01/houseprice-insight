# HousePrice Insight — Data Cleaning Report

Generated (UTC): 2026-10-04 13:02:58

Raw files were read only. Processed outputs were written to `data/processed/`.

## Property Dataset

- **Raw rows:** 13,320
- **Clean rows:** 12,679
- **Rows removed (raw → clean):** 641
- **Duplicate rows removed:** 530 (exact raw duplicates: 529; post-transform duplicates: 1)
- **Range sqft conversions:** 200
- **Unit conversions:** 43
- **Invalid/unusable sqft values:** 3
- **Rows dropped for missing required fields (location/total_sqft/bhk/price):** 20
- **Outlier/error rows removed:** 91
- **Number of locations:** 1,265
- **Locations with >= 10 records:** 248
- **Sparse locations (<10 records, retained):** 1,017
- **Final columns:** location, area_type, availability, bhk, total_sqft, bath, balcony, price, price_per_sqft, society, size_raw, total_sqft_parse_status, market_area

### Missing-value treatment

- Missing before required-field filter: `{'location': 1, 'total_sqft': 3, 'bhk': 16, 'price': 0, 'bath': 73, 'balcony': 605, 'society': 5328}`
- Bath imputation: median bath within same bhk; fallback to global median bath (imputed 57 values).
- Balcony: preserve NaN; do not impute with zero
- Society: retain column for traceability/EDA; high missingness (~41% raw) so it is NOT recommended as an ML feature yet

### Sqft parse status counts

- `numeric`: 12,545
- `range_midpoint`: 200
- `unit_converted`: 43
- `invalid`: 3

### Outlier rules

- `total_sqft_lt_100` (removed/count contribution 7): Residential listings under 100 sqft after conversion are treated as errors.
- `total_sqft_gt_20000` (removed/count contribution 19): Values above 20,000 sqft are treated as land/misparsed errors for this housing model scope.
- `bhk_gt_9` (removed/count contribution 26): BHK > 9 is treated as a recording error for this dataset's residential scope.
- `bath_gt_9` (removed/count contribution 33): Bath > 9 is treated as a recording error for this dataset's residential scope.
- `bath_gt_bhk_plus_3` (removed/count contribution 7): Bathrooms exceeding BHK+3 are treated as inconsistent records.
- `price_per_sqft_lt_1000` (removed/count contribution 27): INR/sqft below 1,000 is treated as an error given Bengaluru market ranges.
- `price_per_sqft_gt_50000` (removed/count contribution 16): INR/sqft above 50,000 is treated as an error/outlier beyond plausible listing quality.
- `unrealistic_tiny_multibhk` (removed/count contribution 10): 3+ BHK with under 400 sqft is treated as inconsistent.
- `note` (removed/count contribution n/a): High absolute price alone is NOT removed if size and price/sqft are plausible.

### Safe location mapping

- Mapping applied: `{'Whitefield,': 'Whitefield'}`
- Rows affected: 0

### Sparse-location statistics (sample)

Sparse localities were **kept**. Sample of sparse localities:

- Gollahalli: count=9, median_price_per_sqft=4372.36
- Kaverappa Layout: count=9, median_price_per_sqft=5533.60
- Vishwanatha Nagenahalli: count=9, median_price_per_sqft=5558.13
- Basapura: count=9, median_price_per_sqft=4545.45
- Peenya: count=9, median_price_per_sqft=5882.35
- Jakkur Plantation: count=9, median_price_per_sqft=6399.07
- Medahalli: count=9, median_price_per_sqft=5857.14
- B Narayanapura: count=9, median_price_per_sqft=4803.92
- Mathikere: count=9, median_price_per_sqft=8666.67
- Banagiri Nagar: count=9, median_price_per_sqft=8000.00
- Richmond Town: count=9, median_price_per_sqft=10168.07
- BTM 1st Stage: count=9, median_price_per_sqft=13333.33
- Kamakshipalya: count=9, median_price_per_sqft=8141.76
- Ejipura: count=9, median_price_per_sqft=6521.74
- Vignana Nagar: count=9, median_price_per_sqft=5225.23

### Top localities by record count

- Whitefield: count=524, median_price_per_sqft=5608.92
- Sarjapur Road: count=384, median_price_per_sqft=5818.27
- Electronic City: count=288, median_price_per_sqft=4542.84
- Kanakpura Road: count=247, median_price_per_sqft=5046.03
- Thanisandra: count=232, median_price_per_sqft=5771.65
- Yelahanka: count=207, median_price_per_sqft=5061.22
- Marathahalli: count=169, median_price_per_sqft=5514.40
- Hebbal: count=161, median_price_per_sqft=7211.90
- Raja Rajeshwari Nagar: count=159, median_price_per_sqft=4239.22
- Uttarahalli: count=157, median_price_per_sqft=4119.34
- Hennur Road: count=149, median_price_per_sqft=5900.38
- Bannerghatta Road: count=148, median_price_per_sqft=5339.26
- 7th Phase JP Nagar: count=135, median_price_per_sqft=6703.91
- Electronic City Phase II: count=128, median_price_per_sqft=3000.00
- Rajaji Nagar: count=105, median_price_per_sqft=13953.49

## Market Dataset

- **Raw rows:** 528
- **Clean rows:** 528
- **Duplicates removed:** 0
- **Date range:** 2015-01-01 → 2025-12-01
- **Number of areas:** 4
- **Areas:** Devanahalli, Indiranagar, Whitefield, Yelahanka
- **Date/year/month inconsistencies repaired from date:** 0
- **Missing YoY values preserved as NaN:** 48
- **Missing avg_price_prev_year preserved as NaN:** 48
- **Invalid avg_price_per_sqft rows removed:** 0
- **Final columns:** date, year, month, area, avg_price_per_sqft, base_price, index_100, avg_price_prev_year, yoy_pct

### Monthly continuity

- **Devanahalli:** rows=132, duplicate_months=0, missing_months=0, range=2015-01-01 → 2025-12-01
- **Indiranagar:** rows=132, duplicate_months=0, missing_months=0, range=2015-01-01 → 2025-12-01
- **Whitefield:** rows=132, duplicate_months=0, missing_months=0, range=2015-01-01 → 2025-12-01
- **Yelahanka:** rows=132, duplicate_months=0, missing_months=0, range=2015-01-01 → 2025-12-01

## Market Coverage

### Market Insight Coverage

Historical Market Insights can be linked only to property localities that safely map to one of the four market areas.

- **Supported market areas:** Devanahalli, Indiranagar, Whitefield, Yelahanka
- **Property records mapped:** 776
- **Property records not mapped:** 11,903
- **Mapped property locality names:** Devanahalli, Devanahalli Road, Whitefield, Yelahanka
- **Mapping pairs (property location → market area):**
  - `Devanahalli` → `Devanahalli`
  - `Devanahalli Road` → `Devanahalli`
  - `Whitefield` → `Whitefield`
  - `Yelahanka` → `Yelahanka`

All other Bengaluru property localities remain valid for ML price estimation but will not show locality-specific historical Market Insights with the current market dataset.

## Data Quality Decisions

1. Exact duplicate property rows were removed.
2. Location cleanup was limited to trim/collapse whitespace and trailing punctuation.
3. `Whitefield,` was mapped to `Whitefield` as a punctuation-only safe fix.
4. BHK was parsed from `size` (including Bedroom / RK patterns); `size_raw` retained.
5. Range sqft values used midpoint; unit-bearing values were converted to sqft.
6. Required fields for a usable supervised row: location, total_sqft, bhk, price.
7. Society missingness did **not** cause row deletion.
8. Bath missing values were imputed by BHK-group median (fallback global median).
9. Balcony missing values were preserved as NaN.
10. `price_per_sqft` uses INR/sqft via `(price_lakhs * 100000) / total_sqft` and is analytics-only.
11. Outlier removal targeted impossible/error configurations, not merely expensive homes.
12. Sparse localities were retained for later encoding decisions.
13. Market YoY baseline gaps remain NaN (not zero-filled).
14. Market data stays monthly; no yearly aggregation was performed.

## Future ML Considerations

- **Target:** `price` (INR lakhs).
- **Do not use `price_per_sqft` as a model input** for predicting `price` (target leakage: it is derived from price and sqft).
- Candidate input features later: `location` (encoded), `area_type`, `availability`, `bhk`, `total_sqft`, `bath`, `balcony` (with missingness handling), optionally mapped `market_area`.
- Locality encoding strategy still to decide (frequency threshold / Other bucket / target encoding with care).
- Market history features should be joined carefully by mapped area and time; avoid leaking future market values into training rows if dates become available later.

## Validation Summary

- `no_nonpositive_property_price`: True
- `no_nonpositive_property_sqft`: True
- `property_numeric_ok`: True
- `property_no_duplicate_rows`: True
- `market_dates_parseable`: True
- `market_areas_valid`: True
- `market_no_duplicate_rows`: True
- `market_numeric_ok`: True
- `raw_property_hash_unchanged`: True
- `raw_market_hash_unchanged`: True
- `house_data_csv_exists`: True
- `house_data_csv_bytes`: 1663

### Raw file integrity hashes (SHA-256)

- property raw: `7b3e1361fcb64348d49eeb83d1e976738dc64bc978536df3438cf7b36f601b28`
- market raw: `c0e95178b93bb3539b08cf15a6d15cb81a7e591eac3675f444b37b2c020a85db`

