import yfinance as yf
import pandas as pd
import numpy as np
import datetime, os, os.path
import argparse, sys
import json
import math
from functools import reduce

parser = argparse.ArgumentParser()
parser.add_argument('-m', dest='movementsPath', help='movements input file', required=True, type=str)
parser.add_argument('-l', dest='limitsPath', help='limits input file', required=False, type=str)
parser.add_argument('-o', dest='portfolioPath', help='portfolio output file', required=False, type=str)
args = parser.parse_args(sys.argv[1:])

def getMinCash(total):
    return np.fmax(2000, total * 0.05)

cacheDir = ".cache"
if not os.path.exists(cacheDir):
    os.mkdir(cacheDir)

def getPriceHistory(symbol, start, end):
    expectedFirstDate = start
    expectedLastDate = end
    if symbol.endswith(".DE") or symbol.endswith(".PA") or symbol.endswith(".AS"): # exchanges trading on weekdays only
        while expectedFirstDate.weekday() == 5 or expectedFirstDate.weekday() == 6:
            expectedFirstDate = expectedFirstDate + datetime.timedelta(1, 0)
        while expectedLastDate.weekday() == 5 or expectedLastDate.weekday() == 6:
            expectedLastDate = expectedLastDate - datetime.timedelta(1, 0)

    histFile = os.path.join(cacheDir, "{}.csv".format(symbol))
    histories = []
    oldHistory = None
    if os.path.exists(histFile):
        oldHistory = pd.read_csv(histFile, index_col="Date", parse_dates=True)
        histories.append(oldHistory)

    ticker = yf.Ticker(symbol)
    updated = False
    if oldHistory is None:
        newHistory = ticker.history(start=start, end=end + datetime.timedelta(1))
        print("Downloaded price history for {} (requested: {} to {}, received: {} to {})".format(symbol, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), newHistory.index[0].strftime("%Y-%m-%d"), newHistory.index[-1].strftime("%Y-%m-%d")))
        histories.append(newHistory)
        updated = True
    else:
        if oldHistory.index[0] > expectedFirstDate:
            newEnd = oldHistory.index[0] - datetime.timedelta(1)
            newHistory = ticker.history(start=start, end=newEnd + datetime.timedelta(1))
            print("Downloaded early price history for {} (requested: {} to {}, received: {} to {})".format(symbol, start.strftime("%Y-%m-%d"), newEnd.strftime("%Y-%m-%d"), newHistory.index[0].strftime("%Y-%m-%d"), newHistory.index[-1].strftime("%Y-%m-%d")))
            histories.append(newHistory)
            updated = True

        if oldHistory.index[-1] < expectedLastDate:
            newStart = oldHistory.index[-1] + datetime.timedelta(1)
            newHistory = ticker.history(start=newStart, end=end + datetime.timedelta(1))
            print("Downloaded recent price history for {} (requested: {} to {}, received: {} to {})".format(symbol, newStart.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), newHistory.index[0].strftime("%Y-%m-%d"), newHistory.index[-1].strftime("%Y-%m-%d")))
            histories.append(newHistory)
            updated = True

    history = pd.concat(histories).sort_index().drop_duplicates()
    if updated:
        history.to_csv(histFile)
    return history

def getInfo(symbol):
    infoFile = os.path.join(cacheDir, "{}.json".format(symbol))
    if os.path.exists(infoFile):
        with open(infoFile, "r") as fp:
            return json.loads(fp.read())

    ticker = yf.Ticker(symbol)
    print("Getting symbol info for {}...".format(symbol))
    info = ticker.info
    with open(infoFile, "w") as fp:
        return fp.write(json.dumps(info))

    return info

currencies = ["EUR", "USD"]
outCurrency = "EUR"

now = datetime.date.today()
movements = pd.read_csv(args.movementsPath, index_col="Date", parse_dates=True, comment="#", skip_blank_lines=True)
timeRange = pd.date_range(movements.index.min(), now)

allSymbols = movements["Symbol"].unique()

holdingsHistoryBySymbol = {}
for symbol in allSymbols:
    holdingsHistory = movements[movements["Symbol"] == symbol]["Change"]
    holdingsHistory = holdingsHistory.groupby(holdingsHistory.index).sum()
    holdingsHistory = holdingsHistory.reindex(timeRange, fill_value=0).sort_index().cumsum()
    holdingsHistoryBySymbol[symbol] = holdingsHistory

priceHistoryBySymbol = {}
valueHistoryBySymbol = {}
for symbol in allSymbols:
    if symbol in currencies:
        priceHistory = pd.Series(np.ones(len(timeRange)), index=timeRange)
    else:
        priceHistory = getPriceHistory(symbol, holdingsHistory.index[0], now)["Close"]
    priceHistoryBySymbol[symbol] = priceHistory
    holdingsHistory = holdingsHistoryBySymbol[symbol]
    valueHistory = (priceHistory * holdingsHistory).ffill()
    valueHistoryBySymbol[symbol] = valueHistory

valueHistoryTotal = reduce(lambda a, b: a + b, [valueHistoryBySymbol[s] for s in allSymbols])
valueHistoryTotalInvested = reduce(lambda a, b: a + b, [valueHistoryBySymbol[s] for s in allSymbols if s not in currencies])
valueHistoryTotalInvestable = np.fmax(0, valueHistoryTotal - getMinCash(valueHistoryTotal))

def getPortfolioAtDate(date):
    portfolio = pd.DataFrame({}, index=allSymbols)
    portfolio.index.name = "Symbol"

    for symbol in allSymbols:
        holdingsHistory = holdingsHistoryBySymbol[symbol]
        priceHistory = priceHistoryBySymbol[symbol]

        fx = pd.Series(np.ones(len(timeRange)), index=timeRange)
        if symbol in currencies:
            portfolio.loc[symbol, "Name"] = "{} (Cash)".format(symbol)
            portfolio.loc[symbol, "Currency"] = symbol
        else:
            info = getInfo(symbol)
            if "longName" in info:
                portfolio.loc[symbol, "Name"] = info["longName"]
            elif "shortName" in info:
                portfolio.loc[symbol, "Name"] = info["shortName"]
            portfolio.loc[symbol, "Currency"] = info["currency"]
            if info["currency"] != outCurrency:
                if info["currency"] == "USD":
                    fxSymbol = "{}=X".format(outCurrency)
                else:
                    fxSymbol = "{}{}=X".format(info["currency"], outCurrency)
                fx = getPriceHistory(fxSymbol, holdingsHistory.index.min(), now)["Close"]

        portfolio.loc[symbol, "Holdings"] = holdingsHistory.loc[date]

        priceHistory = priceHistory.reindex(priceHistory.index.union([date])).ffill() * fx

        portfolio.loc[symbol, "Price"] = priceHistory.loc[date]

    portfolio["MarketValue"] = (portfolio["Holdings"] * portfolio["Price"]).round(2)
    total = portfolio["MarketValue"].sum()
    portfolio["RelativeWeight"] = portfolio["MarketValue"] / total

    invested_portfolio = portfolio[[s not in currencies for s in portfolio.index.values]]
    totalInvested = invested_portfolio["MarketValue"].sum()
    portfolio["RelativeWeightInvested"] = invested_portfolio["MarketValue"] / totalInvested

    totalInvestable = max(0, total - getMinCash(total))
    portfolio["RelativeWeightInvestable"] = invested_portfolio["MarketValue"] / totalInvestable

    return portfolio

def printPortfolio(portfolio):
    print(portfolio.sort_values("MarketValue", ascending=False))
    print()

    total = portfolio["MarketValue"].sum()
    totalInvested = portfolio[[s not in currencies for s in portfolio.index.values]]["MarketValue"].sum()
    print("Portfolio total: {:,.2f}".format(total))
    investable = max(0, total - getMinCash(total))
    print("Portfolio investable: {:,.2f} ({:.1f}%)".format(investable, investable / total * 100))
    print("Portfolio invested: {:,.2f} ({:.1f}%)".format(totalInvested, totalInvested / total * 100))
    print()

def writePortfolio(portfolio, portfolioPath):
    for column in [col for col in portfolio.columns if col.startswith("Relative")]:
        portfolio[column] = portfolio[column].round(3)

    portfolio.to_csv(portfolioPath)

if args.portfolioPath:
    portfolio = getPortfolioAtDate(now)
    writePortfolio(portfolio, args.portfolioPath)

print("Today:")
printPortfolio(getPortfolioAtDate(now))

print("One week ago:")
printPortfolio(getPortfolioAtDate(now - datetime.timedelta(7)))

def getFees(symbol, orderVolume):
    if symbol == "GC=F":
        # Degussa
        return orderVolume * 0.03
    # Diba Direkthandel, adjust as needed
    return min(4.9 + orderVolume * 0.25 / 100, 69.9)

def testLimits(portfolio, limits):
    total = portfolio["MarketValue"].sum()
    investable = max(0, total - getMinCash(total))

    for symbol, row in limits.iterrows():
        targetWeight = row["TargetWeightInvestable"]
        targetAmount = investable * targetWeight

        newTargetWeight = None
        minMarketValue = row["MinMarketValue"]
        maxMarketValue = row["MaxMarketValue"]
        if minMarketValue and not np.isnan(minMarketValue) and targetAmount < minMarketValue:
            newTargetWeight = minMarketValue / investable
            print("{} MinMarketValue of {:.2f} not reached by {:.2f}, adjusting TargetWeightInvestable to {:.3f}".format(symbol, minMarketValue, targetAmount, newTargetWeight))
        elif maxMarketValue and not np.isnan(maxMarketValue) and targetAmount > maxMarketValue:
            newTargetWeight = maxMarketValue / investable
            print("{} MaxMarketValue of {:.2f} exceeded by {:.2f}, adjusting TargetWeightInvestable to {:.3f}".format(symbol, maxMarketValue, targetAmount, newTargetWeight))

        if newTargetWeight is not None:
            limits.loc[symbol, "TargetWeightInvestable"] = newTargetWeight
            otherRowIndexer = limits.index.values != symbol
            limits.loc[otherRowIndexer, "TargetWeightInvestable"] = limits.loc[otherRowIndexer, "TargetWeightInvestable"] / (limits.loc[otherRowIndexer, "TargetWeightInvestable"].sum() - newTargetWeight)

    print(limits)

    for symbol, row in limits.iterrows():
        name = portfolio.loc[symbol, "Name"]
        targetWeight = row["TargetWeightInvestable"]
        targetAmount = investable * targetWeight
        price = portfolio.loc[symbol, "Price"]
        holdings = portfolio.loc[symbol, "Holdings"]
        targetHoldings = math.floor(targetAmount / price)

        print()
        print("{} ({})".format(symbol, name))
        print("Current holdings: {} @ {} {} = {:.2f} {} ({:.1f}%)".format(holdings, price, outCurrency, holdings * price, outCurrency, holdings * price / investable * 100))
        print("Target holdings: {} ({:.1f}) @ {} {} = {:.2f} {} ({:.1f}%, target {:.1f})".format(targetHoldings, targetAmount / price, price, outCurrency, targetHoldings * price, outCurrency, targetHoldings * price / investable * 100, targetWeight * 100))

        if targetHoldings != holdings:
            amt = abs(targetHoldings - holdings)
            volume = amt * price
            fees = getFees(symbol, volume)
            print("Action: {} {} @ {} {} = {:.2f} {} (order fees ~ {:.2f} {} = {:.2f}%)".format(
                "BUY" if targetHoldings > holdings else "SELL", amt,
                price, outCurrency, volume, outCurrency, fees, outCurrency, fees / volume * 100))

if args.limitsPath:
    limits = pd.read_csv(args.limitsPath, index_col="Symbol")

    if limits["TargetWeightInvestable"].sum() != 1:
        print("Warning: sum of TargetWeightInvestable is {}, redistributing".format(limits["TargetWeightInvestable"].sum()))
        limits["TargetWeightInvestable"] = limits["TargetWeightInvestable"] / limits["TargetWeightInvestable"].sum()

    portfolio = getPortfolioAtDate(now)
    testLimits(portfolio, limits)

