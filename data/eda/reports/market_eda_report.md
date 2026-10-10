# Market Dataset EDA Report

Generated (UTC): 2026-10-04 13:09:29
Source: `C:\Users\Amar Sai\House price prediction\data\processed\bengaluru_market_history_clean.csv`

This dataset is for **Market Insights only**. It must not be used to train the property-level price model.

## Overview

- Rows: **528**
- Columns: date, year, month, area, avg_price_per_sqft, base_price, index_100, avg_price_prev_year, yoy_pct
- Areas: **Devanahalli, Indiranagar, Whitefield, Yelahanka**
- Date range: **2015-01-01 → 2025-12-01**
- Unique months: **132**
- Duplicate rows: **0**

### Missing values
- `date`: 0 (0.00%)
- `year`: 0 (0.00%)
- `month`: 0 (0.00%)
- `area`: 0 (0.00%)
- `avg_price_per_sqft`: 0 (0.00%)
- `base_price`: 0 (0.00%)
- `index_100`: 0 (0.00%)
- `avg_price_prev_year`: 48 (9.09%)
- `yoy_pct`: 48 (9.09%)

Missing `yoy_pct` / `avg_price_prev_year` are expected in the first year of each series.

## Completeness by area

- **Devanahalli**: rows=132, observed_months=132, missing_months=0, range=2015-01-01 → 2025-12-01
- **Indiranagar**: rows=132, observed_months=132, missing_months=0, range=2015-01-01 → 2025-12-01
- **Whitefield**: rows=132, observed_months=132, missing_months=0, range=2015-01-01 → 2025-12-01
- **Yelahanka**: rows=132, observed_months=132, missing_months=0, range=2015-01-01 → 2025-12-01

## Price trends

### Yearly mean avg_price_per_sqft
```
area  Devanahalli  Indiranagar  Whitefield  Yelahanka
year                                                 
2015       2836.1       8251.1      4990.2     3459.2
2016       3026.0       8838.1      5370.6     3590.6
2017       3398.5       9584.6      5775.3     3715.7
2018       3802.7      10331.4      6209.9     3857.8
2019       4270.5      11127.5      6689.1     4026.0
2020       4786.4      11914.4      7169.2     4215.5
2021       5350.8      12771.9      7681.7     4390.0
2022       5990.4      13551.7      8112.2     4530.3
2023       6465.4      14383.9      8410.8     4694.5
2024       6763.9      15244.0      8701.9     4847.8
2025       7058.2      16138.5      9010.4     5014.7
```

## YoY growth

```
             count  mean  median   min    max
area                                         
Devanahalli    120  9.60   11.28  2.31  14.82
Indiranagar    120  6.95    7.07  2.59   9.98
Whitefield     120  6.11    6.91  1.30   9.22
Yelahanka      120  3.79    3.76  1.31   6.32
```

## Area comparisons (all months)
```
                 mean    median      min       max
area                                              
Devanahalli   4886.25   4799.90  2806.54   7208.45
Indiranagar  12012.46  11894.38  7979.16  16477.95
Whitefield    7101.93   7181.08  4815.77   9202.47
Yelahanka     4212.92   4227.33  3368.87   5110.89
```

## Decisions that affect product features

### Observations
- Four areas have complete monthly history from 2015-01 through 2025-12.
- Indiranagar is consistently among the higher INR/sqft markets.
- Devanahalli is comparatively lower on a price/sqft basis.
- YoY can be negative in some periods; zero-filling would be misleading.

### Limitations
- Area-level index/history, not property-level transactions.
- Only 4 Bengaluru areas are covered.
- Cannot provide Market Insights for most property localities.

### Product implication
- Market Insights UI should be enabled only for localities mapped to these four areas.
- Do **not** join this dataset into property-model training rows in the current phase.

## Figures

- `figures/market_avg_price_per_sqft_over_time.svg`
- `figures/market_latest_year_avg_ppsft.svg`
