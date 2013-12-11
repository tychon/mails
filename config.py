
# URL to your mail database
couchdb_url = 'http://localhost:5984/mail/'

# Authentication data to be sent to couchdb.
# Sent in clear text! Use SSL! or do it only on localhost.
couchdb_auth = None
# example:
# couchdb_auth = ('username', '1234')

# Where mail_upload puts mails that couldn't be uploaded to CouchDB.
# They will have a 21 chars file name:
#   10 chars beginning of hash, underscore, 10 chars hex randomness.
# Be sure this directory exists and is writable!
backupdir = '~/.mail_backup/'

# File to write error log to
# No expansion of '~' supported here!
# Be sure the directory of the given file / the file is writable!
errorlog = 'error.log'

