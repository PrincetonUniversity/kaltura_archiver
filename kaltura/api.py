
import logging

logger = logging.getLogger('kaltura')
logger.addHandler(logging.NullHandler())

from KalturaClient import *
from KalturaClient.Plugins.Core import *

from datetime import datetime

class KalturaLogger(IKalturaLogger):
    def log(self, msg):
        logger.debug("API: " + msg)

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

def getClient(reload=False):
    global __client__, __params__
    if (reload):
        config = KalturaConfiguration(__params__['partner_id'], logger=KalturaLogger())
        config.serviceUrl = __params__['url']
        client = KalturaClient(config)
        logger.info("KALTURA SESSION %s with %s partnerId:%s" % (client.getConfig().serviceUrl, __params__['user_id'], __params__['partner_id']))
        ks = client.session.start(__params__['secret'], __params__['user_id'], __params__['ktype'],
                              __params__['partner_id'], __params__['expiry'], __params__['privileges'])
        client.setKs(ks)
        __client__ = client
    return __client__;


def startSession(partner_id, user_id, secret):
    """ Use configuration to generate KS
    """
    global __client__, __params__
    __params__['partner_id'] = partner_id
    __params__['user_id'] = user_id
    __params__['secret'] = secret
    c = getClient(reload=True)
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