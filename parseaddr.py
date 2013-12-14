# see RFC 5322
# probably doesn't work on quoted strings and comments
# doesnt work on ',' or ';' in display names
# Most functions raise a ParserException when they encounter something strange.

import sys
import re

class ParserException(Exception):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)

# regular expression for mailbox with display name and angle brackets
re_mbox = re.compile(r'(.*)\<([^\s]+)\>\s*')
# regular expression for mailbox with simple mail address
re_addr = re.compile(r'\s*([^\s]+)\s*')
# regular expression for group of mailboxes
re_grp = re.compile(r'(.*):(.*);\s*')
# regular expression for one element in a list of addresses
re_addrlist_elem = re.compile(r'([^,]*:[^;]*;[^,]*|[^,]+)')

# Returns a tuple (display name, addr)
# NOTE: Fails if the mbox is empty
def parse_mailbox(mbox):
  mo = re_mbox.match(mbox)
  if not mo:
    mo = re_addr.match(mbox)
    if not mo or len(mo.group()) != len(mbox):
      raise ParserException("Couldnt match  %s  as mailbox.\n" % mbox)
    return (None, mo.group(1))
  
  if len(mo.group()) != len(mbox):
    raise ParserException("Couldnt match  %s  as mailbox.\n" % mbox)
  return (mo.group(1).strip(), mo.group(2))

# Returns a list of mailboxes.
# List may be empty.
# Does not fail on empty mailboxes.
def parse_mboxlist(mbl):
  return map(parse_mailbox
      , filter(lambda x1: len(x1) # filter empty mailboxes
          , map(lambda x2: x2.strip() # strip leading and trailing whitespaces
              , mbl.split(',')))) # split at mailbox separator ','

# Parses a mailbox group.
# Returns a tuple (display name, list of mailboxes)
def parse_group(grp):
  mo = re_grp.match(grp)
  if not mo or len(mo.group()) != len(grp):
    raise ParserException("Couldnt match  %s  as mailbox group.\n" % grp)
  return (mo.group(1).strip(), parse_mboxlist(mo.group(2)))

# Parses an address (mailbox or group of mailboxes)
def parse_address(address):
  if ';' in address: return parse_group(address)
  else: return parse_mailbox(address)

# Parses a list of addresses.
def parse_address_list(addresslist):
  addrlist = addresslist
  res = []
  while addrlist:
    mo = re_addrlist_elem.match(addrlist)
    if not mo:
      raise ParserException("Couldnt match  %s  as address list\n" % addrlist)
    res.append(parse_address(addrlist[:mo.end()]))
    if len(addrlist) > mo.end() and addrlist[mo.end()] == ',':
      addrlist = addrlist[mo.end()+1:].strip()
      if not addrlist or addrlist.startswith(','):
        raise ParserException("Empty mailbox name in address list: %s\n" % addresslist)
    else: break
  return res

# Returns a list of addrs (ie ['someone@s1.net', 'foo@example.com'] )
# List may be empty.
# Works recursevly.
def extract_addresses(parsed):
  if type(parsed) == tuple:
    # its a group
    if type(parsed[1]) == list: return extract_addresses(parsed[1])
    # its a mailbox
    else: return [parsed[1]]
  # its a list of something
  elif type(parsed) == list:
    l = map(extract_addresses, parsed) # extract addresses from list
    return [item for sublist in l for item in sublist] # flatten list
  else: raise ParserException("Unexpected type in address tree.")

