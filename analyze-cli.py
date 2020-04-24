import argparse, sys
from analyzer import *

parser = argparse.ArgumentParser()
parser.add_argument('-m', dest='movementsPath', help='movements input file', required=True, type=str)
parser.add_argument('-l', dest='limitsPath', help='limits input file', required=False, type=str)
parser.add_argument('-o', dest='portfolioPath', help='portfolio output file', required=False, type=str)
args = parser.parse_args(sys.argv[1:])

today = datetime.date.today()

movements, holdingsHistoryBySymbol, priceHistoryBySymbol = readMovements(args.movementsPath, today)

portfolioToday = getPortfolioAtDate(movements, holdingsHistoryBySymbol, priceHistoryBySymbol, today)

print("Today:")
printPortfolio(portfolioToday)

print("One week ago:")
printPortfolio(getPortfolioAtDate(movements, holdingsHistoryBySymbol, priceHistoryBySymbol, today - datetime.timedelta(7)))

if args.portfolioPath:
    writePortfolio(portfolioToday, args.portfolioPath)

if args.limitsPath:
    limits = pd.read_csv(args.limitsPath, index_col="Symbol")

    if limits["TargetWeightInvestable"].sum() != 1:
        print("Warning: sum of TargetWeightInvestable is {}, redistributing".format(limits["TargetWeightInvestable"].sum()))
        limits["TargetWeightInvestable"] = limits["TargetWeightInvestable"] / limits["TargetWeightInvestable"].sum()

    testLimits(portfolioToday, limits)

