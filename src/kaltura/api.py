from KalturaClient import *
from KalturaClient.Plugins.Core import *
from KalturaClient.Base import IKalturaLogger

from datetime import datetime

import logging

logger = logging.getLogger('kaltura')
logger.addHandler(logging.NullHandler())

class KalturaLogger(IKalturaLogger):
    def log(self, msg):
        logger.debug("API: " + msg)

__restart__ = 0
__client__ = None
__params__ = {
    'url': "https://www.kaltura.com/",
    'secret' : None,
    'user_id' : None,
    'partner_id' : None,
    'ktype' : KalturaSessionType.ADMIN,
    'expiry' : 432000, # 432000 = 5 days,
    'privileges' : "disableentitlement"
}

def getClient():
    """
    restart Kaltura session after 10000 calls
    :return: KalturaClient
    """
    global __client__, __params__, __restart__
    __restart__ -= 1
    if (__restart__ <= 1):
        __client__.setKs(None)
        ks = __client__.session.start(__params__['secret'], __params__['user_id'], __params__['ktype'],
                                  __params__['partner_id'], __params__['expiry'], __params__['privileges'])
        __client__.setKs(ks)
        __restart__ = 10000
        logger.info("KALTURA {} | {} partnerId: {} | session-key: {} ".
                    format(__client__.getConfig().serviceUrl, __params__['user_id'], __params__['partner_id'], __client__.getKs()))

    return __client__;


def startSession(partner_id, user_id, secret):
    """ Use configuration to generate KS
    """
    global __client__, __params__
    __params__['partner_id'] = partner_id
    __params__['user_id'] = user_id
    __params__['secret'] = secret

    if __client__ == None:
        config = KalturaConfiguration(__params__['partner_id'], logger=KalturaLogger())
        config.serviceUrl = __params__['url']
        __client__  = KalturaClient(config)
        # trigger session start
        getClient()

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