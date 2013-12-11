
import time
import datetime

# Convert date from "Sat, 27 Sep 2008 22:05:46 +0200"
# to "2008-09-27 20:05:46" UTC
def convert_from_maildate(date):
  t = datetime.datetime.strptime(date[:-6], "%a, %d %b %Y %H:%M:%S")
  t = t + datetime.timedelta(hours=(-1 * int(date[-5:]) / 100))
  return datetime.datetime.strftime(t, "%Y-%m-%d %H:%M:%S")

