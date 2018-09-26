
import logging

from KalturaClient import *
from KalturaClient.Plugins.Core import *

from datetime import datetime

__client__ = None

def getClient():
    global __client__;
    return __client__;

def startsession(partner_id, user_id, secret):
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
    logging.info("Kaltura/Api: connected to %s with %s partnerId:%s" % (config.serviceUrl, user_id, partner_id))
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

