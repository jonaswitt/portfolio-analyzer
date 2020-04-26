import boto3
import os, datetime
import analyzer
from jinja2 import Template

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

    # Download & parse movements
    bucket.download_file(movementsFilename, movementsPath)
    movements, holdingsHistoryBySymbol, priceHistoryBySymbol = analyzer.readMovements(movementsPath, today)

    # Calculate today's portfolio & upload
    portfolioToday = analyzer.getPortfolioAtDate(movements, holdingsHistoryBySymbol, priceHistoryBySymbol, today)
    analyzer.printPortfolio(portfolioToday)
    analyzer.writePortfolio(portfolioToday, portfolioPath)
    bucket.upload_file(portfolioPath, portfolioFilename)

    with open("template-status.html.jinja", "r") as fp:
        template = Template(fp.read())

    ses.send_email(
        Destination={
            'ToAddresses': [
                os.environ["NOTIFICATION_EMAIL_RECIPIENT"],
            ],
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': "UTF-8",
                    'Data': template.render(portfolio=portfolioToday, date=today, outCurrency=analyzer.outCurrency),
                },
            },
            'Subject': {
                'Charset': "UTF-8",
                'Data': "[{}] Portfolio Update".format(today.strftime("%Y-%m-%d")),
            },
        },
        Source=os.environ["NOTIFICATION_EMAIL_SENDER"],
    )
