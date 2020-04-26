import boto3
import os, datetime
import analyzer

s3 = boto3.resource('s3')
bucket = s3.Bucket(os.environ["STORAGE_BUCKET_NAME"])

ses = boto3.client('ses')

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

    ses.send_email(
        Destination={
            'ToAddresses': [
                os.environ["NOTIFICATION_EMAIL"],
            ],
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': "UTF-8",
                    'Data': "<html><body><h1>Portfolio Today</h1><pre>{}</pre></body></html>".format(portfolioToday.to_string()),
                },
            },
            'Subject': {
                'Charset': "UTF-8",
                'Data': "Portfolio Analyzer Update",
            },
        },
        Source=os.environ["NOTIFICATION_EMAIL"],
    )
