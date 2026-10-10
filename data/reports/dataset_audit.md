# HousePrice Insight Dataset Audit

Generated (UTC): 2026-10-04 12:56:14

Raw files were inspected only. No cleaning was applied.

## 1. Property Dataset

- **File:** `C:\Users\Amar Sai\House price prediction\data\raw\bengaluru_house_data_raw.csv`
- **File size:** 938,020 bytes
- **Rows:** 13,320
- **Columns:** 9
- **Column names:** area_type, availability, location, size, society, total_sqft, bath, balcony, price
- **Date column available:** False
- **Unique locations:** 1,305
- **Locations with >= 10 records:** 253
- **Locations with < 10 records:** 1,053
- **Duplicate rows:** 529

### Important fields

- `location`: Bengaluru locality for property listings
- `size`: BHK / bedroom style label (e.g. `2 BHK`)
- `total_sqft`: area; sometimes ranges or unit-suffixed strings
- `bath`, `balcony`: numeric-like amenities
- `price`: typically in INR lakhs in this dataset
- `area_type`, `availability`, `society`: categorical listing metadata

### Missing values

- `area_type`: 0 (0.0%)
- `availability`: 0 (0.0%)
- `location`: 1 (0.01%)
- `size`: 16 (0.12%)
- `society`: 5,502 (41.31%)
- `total_sqft`: 0 (0.0%)
- `bath`: 73 (0.55%)
- `balcony`: 609 (4.57%)
- `price`: 0 (0.0%)

### Price / size statistics

- Price (lakhs): `{'count': 13320, 'min': 8.0, 'max': 3600.0, 'mean': 112.5656265015015, 'median': 72.0, 'std': 148.97167376967403, 'p01': 18.5, 'p05': 31.5, 'p95': 324.0, 'p99': 658.0999999999949}`
- Total sqft (parsed): `{'count': 13308, 'min': 1.0, 'max': 52272.0, 'mean': 1557.2551581755336, 'median': 1275.0, 'std': 1238.7206086116823, 'p01': 485.0, 'p05': 662.0, 'p95': 3250.0, 'p99': 5000.0}`
- Price/sqft INR (derived): `{'count': 13308, 'min': 267.82981328435875, 'max': 16000000.0, 'mean': 12284.88678337491, 'median': 5442.032310486569, 'std': 225731.83152214414, 'p01': 2527.165991902834, 'p05': 3100.0, 'p95': 15526.029547553086, 'p99': 25000.0}`
- Bathrooms: `{'count': 13247, 'min': 1.0, 'max': 40.0, 'mean': 2.6926096474673513, 'median': 2.0, 'std': 1.3414580781243859, 'p01': 1.0, 'p05': 1.0, 'p95': 5.0, 'p99': 8.0}`
- BHK (parsed from size): `{'count': 13304, 'min': 1.0, 'max': 43.0, 'mean': 2.803743235117258, 'median': 3.0, 'std': 1.294974169121284, 'p01': 1.0, 'p05': 2.0, 'p95': 5.0, 'p99': 8.0}`

### Top 30 locations by record count

- Whitefield: 540
- Sarjapur  Road: 399
- Electronic City: 302
- Kanakpura Road: 273
- Thanisandra: 234
- Yelahanka: 213
- Uttarahalli: 186
- Hebbal: 177
- Marathahalli: 175
- Raja Rajeshwari Nagar: 171
- Hennur Road: 152
- Bannerghatta Road: 152
- 7th Phase JP Nagar: 149
- Haralur Road: 142
- Electronic City Phase II: 132
- Rajaji Nagar: 107
- Chandapura: 100
- Bellandur: 96
- KR Puram: 91
- Electronics City Phase 1: 88
- Hoodi: 88
- Yeshwanthpur: 85
- Begur Road: 84
- Sarjapur: 82
- Kasavanhalli: 80
- Harlur: 79
- Banashankari: 75
- Hormavu: 74
- Ramamurthy Nagar: 73
- Kengeri: 73

### Data-quality problems

- Range `total_sqft` rows: 201
- Unusual/non-numeric `total_sqft` rows: 46
- Suspicious value counts: `{'missing_location': 1, 'missing_total_sqft': 0, 'missing_price': 0, 'range_total_sqft_rows': 201, 'unusual_non_numeric_total_sqft_rows': 46, 'price_non_positive': 0, 'sqft_non_positive': 0, 'bath_gt_bhk_plus_2': 16, 'bhk_ge_10': 26, 'bath_ge_10': 33, 'sqft_lt_100': 21, 'sqft_gt_20000': 7, 'price_lakhs_gt_2000': 13, 'price_per_sqft_lt_1000': 11, 'price_per_sqft_gt_50000': 32, 'unrealistic_tiny_home': 18}`
- Potential IQR outliers: `{'price_iqr_outliers': 1276, 'sqft_iqr_outliers': 1191, 'price_per_sqft_iqr_outliers': 1287}`
- Sample range sqft values: ['2100 - 2850', '3010 - 3410', '2957 - 3450', '3067 - 8156', '1042 - 1105', '1145 - 1340', '1015 - 1540', '1520 - 1740', '1195 - 1440', '1200 - 2400', '1120 - 1145', '4400 - 6640', '3090 - 5002', '4400 - 6800', '1160 - 1195']
- Sample unusual sqft values: ['34.46Sq. Meter', '4125Perch', '1000Sq. Meter', '1100Sq. Yards', '5.31Acres', '30Acres', '716Sq. Meter', '1500Sq. Meter', '142.61Sq. Meter', '1574Sq. Yards', '361.33Sq. Yards', '117Sq. Yards', '3040Sq. Meter', '500Sq. Yards', '167Sq. Meter']

- Note: price values in this dataset are commonly expressed in INR lakhs.
- Note: price_per_sqft computed as (price_lakhs * 100000) / total_sqft for audit only.

## 2. Historical Market Dataset

- **File:** `C:\Users\Amar Sai\House price prediction\data\raw\bengaluru_market_history_raw.csv`
- **File size:** 34,175 bytes
- **Rows:** 528
- **Columns:** 9
- **Column names:** date, year, month, area, avg_price_per_sqft, base_price, index_100, avg_price_prev_year, yoy_pct
- **Unique areas:** 4
- **Min date:** 2015-01-01
- **Max date:** 2025-12-01
- **Months represented:** 132
- **Years represented:** [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
- **Duplicate rows:** 0

### Missing values

- `date`: 0 (0.0%)
- `year`: 0 (0.0%)
- `month`: 0 (0.0%)
- `area`: 0 (0.0%)
- `avg_price_per_sqft`: 0 (0.0%)
- `base_price`: 0 (0.0%)
- `index_100`: 0 (0.0%)
- `avg_price_prev_year`: 48 (9.09%)
- `yoy_pct`: 48 (9.09%)

### Price statistics

- avg_price_per_sqft: `{'count': 528, 'min': 2806.54, 'max': 16477.95, 'mean': 7053.389450757575, 'median': 6127.745, 'std': 3466.2241605486283, 'p01': 2835.1196, 'p05': 3287.3945000000003, 'p95': 14632.695, 'p99': 16173.0375}`
- yoy_pct: `{'count': 480, 'min': 1.3, 'max': 14.82, 'mean': 6.6118125, 'median': 6.48, 'std': 3.026850931553716, 'p01': 1.7538, 'p05': 2.6185, 'p95': 12.440999999999999, 'p99': 13.6021}`

### Historical completeness

- Areas with complete coverage (>=98% of global month span): 4
- Areas with near-complete coverage (>=80%): 0
- Areas with insufficient coverage (<80%): 0
- Complete areas: Devanahalli, Indiranagar, Whitefield, Yelahanka

### Records per area

- Devanahalli: 132 rows; observed_months=132, missing_months=0
- Indiranagar: 132 rows; observed_months=132, missing_months=0
- Whitefield: 132 rows; observed_months=132, missing_months=0
- Yelahanka: 132 rows; observed_months=132, missing_months=0

### Data-quality problems

- Sparse area set compared with property localities (market file is area-index style).
- Early YoY values may be missing until a prior-year baseline exists.
- This is area-level historical price index data, not property-level transactions.

## 3. Locality Overlap

Normalization was used for analysis only (lowercase, punctuation strip, basic Bangalore/Bengaluru and layout/road cleanup). Raw files were not modified.

- **Exact matches:** 3
  - Devanahalli, Whitefield, Yelahanka
- **Normalized match groups:** 3
- Example normalized pairs:
  - property `Devanahalli` ↔ market `Devanahalli` (norm: `devanahalli`)
  - property `Devanahalli Road` ↔ market `Devanahalli` (norm: `devanahalli`)
  - property `Whitefield` ↔ market `Whitefield` (norm: `whitefield`)
  - property `Whitefield,` ↔ market `Whitefield` (norm: `whitefield`)
  - property `Yelahanka` ↔ market `Yelahanka` (norm: `yelahanka`)
- **Property locations with no market history (normalized):** 1,289
- **Market areas with no property records (normalized):** 1
- **Property rows whose locality has market overlap:** 803 / 13,319
- Market-only areas: Indiranagar

### Important implication for UI

Market Insights should only be offered for localities that map to market areas after normalization. Most property localities will not have dedicated historical market series in the current market file.

## 4. Recommended Cleaning

Do **not** apply these now. Recommended later:

1. Drop or impute rows with missing critical fields (`location`, `total_sqft`, `price`).
2. Parse `total_sqft` ranges to midpoint; handle unit-suffixed values separately.
3. Extract numeric BHK from `size`; standardize bedroom labels.
4. Convert `price` to a clear INR unit and compute `price_per_sqft`.
5. Remove impossible combinations (e.g., baths >> BHK, tiny sqft with high BHK).
6. Cap or filter extreme price/sqft outliers using transparent rules.
7. Deduplicate exact duplicate rows.
8. Create a locality mapping table between property `location` and market `area`.
9. Keep sparse localities labeled; optionally group rare localities as `Other`.
10. Leave market raw history intact; fill analysis gaps only in processed outputs.

## 5. ML Readiness

The property dataset is **suitable for ML after cleaning**. It has enough rows (13,320) and useful features (location, size/BHK, sqft, bath, balcony, area_type). However, raw quality issues (range sqft strings, missing society/balcony, sparse localities, and likely listing-era rather than verified transaction prices) mean a cleaned processed dataset is required before training.

## 6. Market Insights Readiness

Safe historical market features we can build from the market dataset:

- Average price per sqft over time by area
- Year/month trend charts for areas with sufficient coverage
- YoY % change where `yoy_pct` / prior-year baseline exists
- Index-style comparison using `index_100` / `base_price`
- Area selector limited to market areas (and property localities that map to them)

Not safe yet:

- City-wide Market Insights for every property locality
- Claiming transaction-level truth from listing/index history
- Fine-grained street-level trends

## 7. Limitations

- Property data appears to be historical listing-style data, not confirmed sale deeds.
- Property dataset has no listing/sale date column in the raw file.
- Market history covers 2015-01-01 to 2025-12-01 across 4 areas only.
- Locality naming is inconsistent between sources; overlap is limited without a mapping layer.
- `total_sqft` is dirty (ranges / non-numeric forms), affecting price-per-sqft quality.
- High missingness in `society` (and some balcony values) limits those features.
- Sparse localities (<10 rows) will be unreliable for locality-specific learning.
- Existing app sample file `data/house_data.csv` was left untouched and unused here.

