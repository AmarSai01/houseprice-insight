# Property Dataset EDA Report

Generated (UTC): 2026-10-04 13:09:28
Source: `C:\Users\Amar Sai\House price prediction\data\processed\bengaluru_property_clean.csv`

## Dataset overview

- Shape: **12,679 rows × 13 columns**
- Columns: location, area_type, availability, bhk, total_sqft, bath, balcony, price, price_per_sqft, society, size_raw, total_sqft_parse_status, market_area
- Duplicate rows: **0**

### Missing values

- `location`: 0 (0.00%)
- `area_type`: 0 (0.00%)
- `availability`: 0 (0.00%)
- `bhk`: 0 (0.00%)
- `total_sqft`: 0 (0.00%)
- `bath`: 0 (0.00%)
- `balcony`: 557 (4.39%)
- `price`: 0 (0.00%)
- `price_per_sqft`: 0 (0.00%)
- `society`: 5,246 (41.38%)
- `size_raw`: 0 (0.00%)
- `total_sqft_parse_status`: 0 (0.00%)
- `market_area`: 11,903 (93.88%)

## Numerical distributions

- `price`: count=12,679, min=8.00, median=72.04, mean=112.46, max=2912.00
- `total_sqft`: count=12,679, min=250.00, median=1280.00, mean=1542.72, max=14000.00
- `bhk`: count=12,679, min=1.00, median=3.00, mean=2.79, max=9.00
- `bath`: count=12,679, min=1.00, median=2.00, mean=2.68, max=9.00
- `balcony`: count=12,122, min=0.00, median=2.00, mean=1.58, max=3.00
- `price_per_sqft`: count=12,679, min=1166.67, median=5479.45, mean=6697.13, max=50000.00

Target note: `price` is in **INR lakhs**.
`price_per_sqft` is analytics-only and must not be used as an ML input feature.

## Relationships with price

### Correlations (numerical)

```
            price  total_sqft    bhk   bath  balcony
price       1.000       0.753  0.422  0.486    0.120
total_sqft  0.753       1.000  0.469  0.545    0.199
bhk         0.422       0.469  1.000  0.880    0.207
bath        0.486       0.545  0.880  1.000    0.225
balcony     0.120       0.199  0.207  0.225    1.000
```

Observations:
- price ↔ total_sqft correlation: **0.753**
- price ↔ bhk correlation: **0.422**
- price ↔ bath correlation: **0.486**
- Size-related features (`total_sqft`, `bhk`, `bath`) are positively associated with price.

## Categorical coverage

### Area type counts
- Super built-up  Area: 8,297
- Built-up  Area: 2,384
- Plot  Area: 1,912
- Carpet  Area: 86

### Availability
- Unique availability values: **80**
- Share `Ready To Move`: **79.6%**
- Remaining values are mostly future possession dates, creating high cardinality noise.
- **ML decision:** prefer a binary `is_ready_to_move` flag rather than one-hot encoding all dates.

### Location frequency
- Unique locations: **1,265**
- Locations with >= 10 rows: **248**
- Locations with < 10 rows: **1,017**

Top localities by record count:
- Whitefield: 524
- Sarjapur Road: 384
- Electronic City: 288
- Kanakpura Road: 247
- Thanisandra: 232
- Yelahanka: 207
- Marathahalli: 169
- Hebbal: 161
- Raja Rajeshwari Nagar: 159
- Uttarahalli: 157
- Hennur Road: 149
- Bannerghatta Road: 148
- 7th Phase JP Nagar: 135
- Electronic City Phase II: 128
- Rajaji Nagar: 105
- Haralur Road: 103
- Bellandur: 94
- KR Puram: 90
- Electronics City Phase 1: 88
- Hoodi: 88

**ML decision:** group rare locations into `Other` using a train-only frequency threshold (recommended: locations with fewer than 10 training rows).

## Price statistics by group

### By area_type
```
                      count  median    mean
area_type                                  
Plot  Area             1912  140.00  205.19
Built-up  Area         2384   70.00  103.94
Carpet  Area             86   70.00   90.19
Super built-up  Area   8297   65.11   93.76
```

### By BHK
```
     count  median    mean
bhk                       
1.0    627   34.38   42.66
2.0   5240   54.00   59.87
3.0   4641   90.00  112.22
4.0   1383  204.00  266.98
5.0    344  172.50  279.29
6.0    220  160.00  216.65
7.0     98  150.00  245.63
8.0     82  160.00  209.17
9.0     44  187.50  235.11
```

### Median price/sqft by locality (n ≥ 30, analytics only)

- Rajaji Nagar: n=105, median INR/sqft=13953
- Malleshwaram: n=56, median INR/sqft=12500
- Indira Nagar: n=42, median INR/sqft=11579
- Frazer Town: n=36, median INR/sqft=9964
- Basavangudi: n=31, median INR/sqft=9810
- Hosakerehalli: n=36, median INR/sqft=9514
- Hebbal Kempapura: n=33, median INR/sqft=9231
- Koramangala: n=70, median INR/sqft=9062
- Kumaraswami Layout: n=30, median INR/sqft=8063
- R.T. Nagar: n=35, median INR/sqft=7727
- Kundalahalli: n=46, median INR/sqft=7442
- Thigalarapalya: n=48, median INR/sqft=7351
- Hebbal: n=161, median INR/sqft=7212
- Nagarbhavi: n=60, median INR/sqft=6933
- 7th Phase JP Nagar: n=135, median INR/sqft=6704

## Remaining suspicious values

- `price_gt_1000_lakhs`: 37
- `total_sqft_gt_10000`: 11
- `bath_gt_bhk_plus_2`: 7
- `balcony_missing`: 557
- `society_missing`: 5246

These are residual edge cases after cleaning. They should not dominate training, but tree models can tolerate some remaining long-tail values.

## Decisions that affect ML

### Observations
- `total_sqft` is the strongest continuous driver of `price`.
- `bhk` and `bath` are useful but correlated with size.
- `area_type` has low cardinality and clear median-price differences.
- `location` matters but is high-cardinality and sparse in the long tail.
- `availability` is mostly binary in practice (`Ready To Move` vs future dates).
- `society` remains too incomplete for a default feature.
- `balcony` is useful but has missing values that need imputation inside the train pipeline.

### Limitations
- Listing-style historical data, not verified sale deeds.
- No property transaction date in this dataset.
- Locality names are unevenly represented.
- Market-history dataset is separate and must not be mixed into property training rows.

### Recommended final feature set
- `area_type`
- `location` (rare → `Other`)
- `total_sqft`
- `bhk`
- `bath`
- `balcony` (median impute in pipeline)
- `is_ready_to_move` derived from `availability`

### Explicit exclusions
- `price` (target)
- `price_per_sqft` (target leakage)
- `society` (high missingness / weak reliability)
- raw high-cardinality `availability` date strings

## Figures

- `figures/area_type_distribution.svg`
- `figures/bathroom_distribution.svg`
- `figures/bhk_distribution.svg`
- `figures/price_distribution.svg`
- `figures/price_per_sqft_distribution.svg`
- `figures/price_vs_bath.svg`
- `figures/price_vs_bhk.svg`
- `figures/price_vs_total_sqft.svg`
- `figures/top_localities_median_ppsft.svg`
- `figures/top_locations_by_count.svg`
- `figures/total_sqft_distribution.svg`
