
import logging

logger = logging.getLogger('kaltura')
logger.addHandler(logging.NullHandler())

from KalturaClient import *
from KalturaClient.Plugins.Core import *

from datetime import datetime

__client__ = None

def getClient():
    global __client__;
    return __client__;

def startSession(partner_id, user_id, secret):
    """ Use configuration to generate KS
    """
    global __client__
    config = KalturaConfiguration(partner_id)
    config.serviceUrl = "https://www.kaltura.com/"
    client = KalturaClient(config)
    ktype = KalturaSessionType.ADMIN
    expiry = 432000 # 432000 = 5 days
    privileges = "disableentitlement"

    ks = client.session.start(secret, user_id, ktype, partner_id, expiry, privileges)
    client.setKs(ks)
    logger.info("KALTURA API %s with %s partnerId:%s" % (config.serviceUrl, user_id, partner_id))
    __client__ = client
    return None


def dateString(at):
    """
    :param at: utc time
    :return:   formatted date string
    """
    if (at != None):
        return datetime.utcfromtimestamp(at).strftime('%Y-%m-%d')
    else:
        return None


def log_action(loglevel, doit, type, id, action, message):
    if logger.isEnabledFor(loglevel):
        logger.log(loglevel, '{} | {:<7} {:<10} | {:<20} {}'.format('EXEC  ' if doit else 'DRYRUN', type, id, action, message))