# FinVerifyBench — Dataset Statistics

**Total samples:** 500  

**Splits:** dev=75, test=75, train=350  


## Error Category Distribution

| Category | Count | % |
|----------|-------|---|
| scale_error | 170 | 34.0% |
| ratio_error | 165 | 33.0% |
| sign_error | 95 | 19.0% |
| percentage_error | 75 | 15.0% |
| aggregation_error | 75 | 15.0% |
| arithmetic_error | 70 | 14.0% |
| magnitude_error | 40 | 8.0% |
| unit_conversion | 30 | 6.0% |
| rounding_error | 10 | 2.0% |
| context_confusion | 5 | 1.0% |

## Difficulty Distribution

| Difficulty | Count | % |
|------------|-------|---|
| easy | 230 | 46.0% |
| medium | 185 | 37.0% |
| hard | 85 | 17.0% |

## Reasoning Type Distribution

| Reasoning Type | Count | % |
|----------------|-------|---|
| ratio_calculation | 140 | 28.0% |
| margin_calculation | 100 | 20.0% |
| yoy_change | 85 | 17.0% |
| multi_step_arithmetic | 80 | 16.0% |
| single_lookup | 70 | 14.0% |
| aggregation | 60 | 12.0% |
| percentage_change | 55 | 11.0% |
| unit_conversion | 40 | 8.0% |
| growth_rate | 20 | 4.0% |

## Ground-Truth Analysis

- Positive: 405 (81.0%)
- Negative: 95 (19.0%)
- Log10 range: [-0.7, 8.95]

## Balance (χ²)

- Error category χ²: 406.84
- Difficulty χ²: 66.10