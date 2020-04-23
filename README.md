# Portfolio Analyzer

This tool will load a stock portfolio from a list of movements (ticker symbol, date, amount added), and displays the
current total portfolio value based on latest stock prices, incl. the relative weights of each stock in
the portfolio.

Optionally, it will load a limits file with target weights for each stock, and calculates how many of each stock to
buy/sell in order to achieve the target weights. It will also display approximate order fees (absolute/relative), so
you can decide whether it's worth rebalancing and avoid trading small amounts.

At the moment, this tool supports [Yahoo Finance](https://finance.yahoo.com/) ticker symbol only. It has limited 
support for currency conversion/loading ticker prices in other currencies.

## Use

Requires Python 3.7 (or higher).
Run `pip install -r requirements.txt` to install dependencies (using [Virtualenv](https://virtualenv.pypa.io/) may be helpful).

```
python analyze.py --help
usage: analyze.py [-h] -m MOVEMENTSPATH [-l LIMITSPATH] [-o PORTFOLIOPATH]

optional arguments:
  -h, --help        show this help message and exit
  -m MOVEMENTSPATH  movements input file
  -l LIMITSPATH     limits input file
  -o PORTFOLIOPATH  portfolio output file
```

## Example

```
$ python analyze.py -m example/movements.csv -l example/limits.csv -o example/portfolio.csv
Today:
                                                      Name Currency  Holdings   Price  MarketValue  RelativeWeight  RelativeWeightInvested  RelativeWeightInvestable
Symbol
EXHD.DE  iShares eb.rexx Government Germany 5.5-10.5yr ...      EUR      50.0  145.94       7297.0        0.468035                0.500113                  0.536911
X010.DE                      ComStage MSCI World UCITS ETF      EUR     110.0   51.77       5694.7        0.365263                0.390297                  0.419014
IQQE.DE               iShares MSCI EM UCITS ETF USD (Dist)      EUR      50.0   31.98       1599.0        0.102561                0.109590                  0.117654
EUR                                             EUR (Cash)      EUR    1000.0    1.00       1000.0        0.064141                     NaN                       NaN

Portfolio total: 15,590.70
Portfolio investable: 13,590.70 (87.2%)
Portfolio invested: 14,590.70 (93.6%)

One week ago:
                                                      Name Currency  Holdings   Price  MarketValue  RelativeWeight  RelativeWeightInvested  RelativeWeightInvestable
Symbol
EXHD.DE  iShares eb.rexx Government Germany 5.5-10.5yr ...      EUR      50.0  146.56       7328.0        0.460192                0.491028                  0.526293
X010.DE                      ComStage MSCI World UCITS ETF      EUR     110.0   55.63       6119.3        0.384286                0.410036                  0.439485
IQQE.DE               iShares MSCI EM UCITS ETF USD (Dist)      EUR      50.0   29.53       1476.5        0.092723                0.098936                  0.106041
EUR                                             EUR (Cash)      EUR    1000.0    1.00       1000.0        0.062799                     NaN                       NaN

Portfolio total: 15,923.80
Portfolio investable: 13,923.80 (87.4%)
Portfolio invested: 14,923.80 (93.7%)

         TargetWeightInvestable  MaxMarketValue  MinMarketValue
Symbol
X010.DE                     0.4             NaN             NaN
IQQE.DE                     0.2             NaN             NaN
EXHD.DE                     0.4             NaN             NaN

X010.DE (ComStage MSCI World UCITS ETF)
Current holdings: 110.0 @ 51.77 EUR = 5694.70 EUR (41.9%)
Target holdings: 105 (105.0) @ 51.77 EUR = 5435.85 EUR (40.0%, target 40.0)
Action: SELL 5.0 @ 51.77 EUR = 258.85 EUR (order fees ~ 5.55 EUR = 2.14%)

IQQE.DE (iShares MSCI EM UCITS ETF USD (Dist))
Current holdings: 50.0 @ 31.98 EUR = 1599.00 EUR (11.8%)
Target holdings: 84 (85.0) @ 31.98 EUR = 2686.32 EUR (19.8%, target 20.0)
Action: BUY 34.0 @ 31.98 EUR = 1087.32 EUR (order fees ~ 7.62 EUR = 0.70%)

EXHD.DE (iShares eb.rexx Government Germany 5.5-10.5yr UCITS ETF (DE))
Current holdings: 50.0 @ 145.94 EUR = 7297.00 EUR (53.7%)
Target holdings: 37 (37.3) @ 145.94 EUR = 5399.78 EUR (39.7%, target 40.0)
Action: SELL 13.0 @ 145.94 EUR = 1897.22 EUR (order fees ~ 9.64 EUR = 0.51%)
```

## Development Goals

See Github issues 🚀
