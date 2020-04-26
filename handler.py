import boto3
import os, datetime
import analyzer

s3 = boto3.resource('s3')
bucket = s3.Bucket(os.environ["STORAGE_BUCKET_NAME"])

workingDir = "/tmp"

movementsFilename = "movements.csv"
movementsPath = os.path.join(workingDir, movementsFilename)

portfolioFilename = "portfolio.csv"
portfolioPath = os.path.join(workingDir, portfolioFilename)

def handler(event, context):
    today = datetime.date.today()

    bucket.download_file(movementsFilename, movementsPath)

    movements, holdingsHistoryBySymbol, priceHistoryBySymbol = analyzer.readMovements(movementsPath, today)

    portfolioToday = analyzer.getPortfolioAtDate(movements, holdingsHistoryBySymbol, priceHistoryBySymbol, today)

    analyzer.printPortfolio(portfolioToday)

    analyzer.writePortfolio(portfolioToday, portfolioPath)

    bucket.upload_file(portfolioPath, portfolioFilename)
