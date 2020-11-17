# stock-analyzer

MAMA Strategy
1. Check MACD Crossover
2. Check current value
3. Check past 5 days value
4. Check close price vs alma
5. Check risk
    - check breakout candle
    - previous candle must be below alma
6. Check volume

TODO:
1. Win rate per test --> DONE
2. Run all test --> DONE
3. indicate to check risk or not --> DONE
4. Fix stoploss --> DONE
5. My own strategy - ALMA, MA20 and MACD --> DONE
6. Test one stock with both strategy --> DONE
7. Implement stoploss --> IN PROGRESS

RISK LIST:
1. is_above(compute_profit(close, alma), -4.00) --> same day risk computation
2. is_above(first_breakout(stocks, i), -4.00) --> first breakout risk computation