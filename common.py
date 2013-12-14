
import time
import datetime
import re

re_date = re.compile(r'([^\(]*)\(')

# Convert date from "Sat, 27 Sep 2008 22:05:46 +0200"
# to "2008-09-27 20:05:46" UTC
# In dates like 'Wed, 18 Sep 2013 19:13:14 +0200 (CEST)' the name of the
# timezone is simply ignored.
def convert_from_maildate(date):
  if '(' in date: # ignore timezone name
    date = re_date.match(date).group(1).strip()
  t = datetime.datetime.strptime(date[:-6], "%a, %d %b %Y %H:%M:%S")
  t = t + datetime.timedelta(hours=(-1 * int(date[-5:]) / 100))
  return datetime.datetime.strftime(t, "%Y-%m-%d %H:%M:%S")

