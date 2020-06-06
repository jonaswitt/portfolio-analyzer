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
cacheKeyPrefix = "cache/"

movementsFilename = "movements.csv"
movementsPath = os.path.join(workingDir, movementsFilename)

portfolioFilename = "portfolio.csv"
portfolioPath = os.path.join(workingDir, portfolioFilename)

limitsFilename = "limits.csv"
limitsPath = os.path.join(workingDir, limitsFilename)

def handler(event, context):
    today = datetime.date.today()

    # Download cache
    if not os.path.exists(cacheDir):
        os.mkdir(cacheDir)
    try:
        listResponse = s3Client.list_objects_v2(
            Bucket=bucketName,
            Prefix=cacheKeyPrefix,
        )
        cacheEntries = listResponse["Contents"]
        if len(cacheEntries) > 0:
            print("Downloading {} cache entries from s3://{}/{} ...".format(len(cacheEntries), bucketName, cacheKeyPrefix))
        else:
            print("No cache entries found in s3://{}/{}".format(bucketName, cacheKeyPrefix))
        for cacheEntry in cacheEntries:
            key = cacheEntry["Key"]
            if key.endswith("/"):
                continue
            localPath = os.path.join(cacheDir, os.path.basename(key))
            bucket.download_file(key, localPath)
    except Exception as ex:
        print("Could not download cache: {}".format(ex))

    # Download & parse movements
    bucket.download_file(movementsFilename, movementsPath)
    movements, holdingsHistoryBySymbol, priceHistoryBySymbol = analyzer.readMovements(movementsPath, today)

    # Calculate today's portfolio & upload
    portfolioToday = analyzer.getPortfolioAtDate(movements, holdingsHistoryBySymbol, priceHistoryBySymbol, today)
    analyzer.printPortfolio(portfolioToday)
    analyzer.writePortfolio(portfolioToday, portfolioPath)
    bucket.upload_file(portfolioPath, portfolioFilename)

    # Test limits
    limitActions = []
    try:
        bucket.download_file(limitsFilename, limitsPath)
        limits = analyzer.readLimits(limitsPath)
        limitActions = analyzer.testLimits(portfolioToday, limits)
    except Exception as ex:
        print("No limits.csv found, skipping limits test")

    # Send email
    with open("template-status.html.jinja", "r") as fp:
        template = Template(fp.read())
    formattedBody = template.render(portfolio=portfolioToday, date=today, outCurrency=analyzer.outCurrency, limitActions=limitActions)
    formattedSubject = "[{}] Portfolio Update".format(today.strftime("%Y-%m-%d"))
    emailRecipient = os.environ["NOTIFICATION_EMAIL_RECIPIENT"]

    print("Sending status email to {}...".format(emailRecipient))
    ses.send_email(
        Destination={
            'ToAddresses': [
                emailRecipient,
            ],
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': "UTF-8",
                    'Data': formattedBody,
                },
            },
            'Subject': {
                'Charset': "UTF-8",
                'Data': formattedSubject,
            },
        },
        Source=os.environ["NOTIFICATION_EMAIL_SENDER"],
    )

    # Upload cache
    try:
        print("Uploading cache to s3://{}/{} ...".format(bucketName, cacheKeyPrefix))
        for cacheFileName in os.listdir(cacheDir):
            cacheFilePath = os.path.join(cacheDir, cacheFileName)
            if not os.path.isfile(cacheFilePath):
                continue
            key = "{}{}".format(cacheKeyPrefix, cacheFileName)
            bucket.upload_file(cacheFilePath, key)
    except Exception as ex:
        print("Could not upload cache: {}".format(ex))
