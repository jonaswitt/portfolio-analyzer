import boto3
import os, datetime
import analyzer
from jinja2 import Template

s3 = boto3.resource('s3')
s3Client = boto3.client('s3')
bucketName = os.environ["STORAGE_BUCKET_NAME"]
bucket = s3.Bucket(bucketName)

ses = boto3.client('ses')

workingDir = os.environ["TMP_DIR"]
cacheDir = os.environ["CACHE_DIR"]

movementsFilename = "movements.csv"
movementsPath = os.path.join(workingDir, movementsFilename)

portfolioFilename = "portfolio.csv"
portfolioPath = os.path.join(workingDir, portfolioFilename)

def handler(event, context):
    today = datetime.date.today()

    if not os.path.exists(cacheDir):
        os.mkdir(cacheDir)
    try:
        listResponse = s3Client.list_objects_v2(
            Bucket=bucketName,
            Prefix="cache/",
        )
        for cacheEntry in listResponse["Contents"]:
            key = cacheEntry["Key"]
            if key.endswith("/"):
                continue
            localPath = os.path.join(cacheDir, os.path.basename(key))
            print("Downloading {} to {}".format(key, localPath))
            bucket.download_file(key, localPath)
    except Exception as ex:
        print(ex)

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
