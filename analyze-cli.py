import argparse, sys, datetime
import analyzer

parser = argparse.ArgumentParser()
parser.add_argument('-m', dest='movementsPath', help='movements input file', required=True, type=str)
parser.add_argument('-l', dest='limitsPath', help='limits input file', required=False, type=str)
parser.add_argument('-o', dest='portfolioPath', help='portfolio output file', required=False, type=str)
args = parser.parse_args(sys.argv[1:])

today = datetime.date.today()

movements, holdingsHistoryBySymbol, priceHistoryBySymbol = analyzer.readMovements(args.movementsPath, today)

portfolioToday = analyzer.getPortfolioAtDate(movements, holdingsHistoryBySymbol, priceHistoryBySymbol, today)

print("Today:")
analyzer.printPortfolio(portfolioToday)

print("One week ago:")
analyzer.printPortfolio(analyzer.getPortfolioAtDate(movements, holdingsHistoryBySymbol, priceHistoryBySymbol, today - datetime.timedelta(7)))

if args.portfolioPath:
    analyzer.writePortfolio(portfolioToday, args.portfolioPath)

if args.limitsPath:
    limits = analyzer.readLimits(args.limitsPath)

    if limits["TargetWeightInvestable"].sum() != 1:
        print("Warning: sum of TargetWeightInvestable is {}, redistributing".format(limits["TargetWeightInvestable"].sum()))
        limits["TargetWeightInvestable"] = limits["TargetWeightInvestable"] / limits["TargetWeightInvestable"].sum()

    analyzer.testLimits(portfolioToday, limits)

