#####################
# Important settings!
#####################
# Set these right to prevent loosing data!

# File to write error log to
# No expansion of '~' supported here!
# Be sure the directory of the given file / the file is writable!
errorlog = 'error.log'

# Where mail_upload puts mails that couldn't be uploaded to CouchDB.
# They will have a 21 chars file name:
#   10 chars beginning of hash, underscore, 10 chars hex randomness.
# Be sure this directory exists and is writable!
# '~' expansion allowed
backupdir = '~/.mail_backup/'

# URL to your mail database
# SSL is supported, but certificates are not verified.
# Don't forget a trailing slash.
couchdb_url = 'http://localhost:5984/mail/'

# The the document id of your design document with the views for searching.
# Don't forget a trailing slash.
design_doc = '_design/post/'

### If you want to disable one of the following features, do not comment the
# variables out, but set them to None.

# Authentication data to be sent to couchdb.
# Sent in clear text! Use SSL! or do it only on trusted connections.
couchdb_auth = None
# example:
# couchdb_auth = ('username', '1234')

# Path to file with rules for autolabelling.
# Check its sanity! (see README section Labelling)
autolabels = 'autolabels'

muttrc = None
temp_mailbox = 'tmpbox'
sent_mailbox = None

