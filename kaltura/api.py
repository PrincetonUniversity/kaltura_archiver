
import logging

logger = logging.getLogger('kaltura')
logger.addHandler(logging.NullHandler())

from KalturaClient import *
from KalturaClient.Plugins.Core import *

from datetime import datetime

__client__ = None
__params__ = {
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
        _start_session(__client__, __params__)
    return __client__;


def startSession(partner_id, user_id, secret):
    """ Use configuration to generate KS
    """
    global __client__, __params__
    config = KalturaConfiguration(partner_id)
    config.serviceUrl = "https://www.kaltura.com/"
    client = KalturaClient(config)

    __params__['partner_id'] = partner_id
    __params__['user_id'] = user_id
    __params__['secret'] = secret

    _start_session(client, __params__)
    __client__ = client
    return None

def _start_session(client, params):
    logger.info("KALTURA SESSION %s with %s partnerId:%s" % (client.getConfig().serviceUrl, params['user_id'], params['partner_id']))
    ks = client.session.start(params['secret'], params['user_id'], params['ktype'],
                              params['partner_id'], params['expiry'], params['privileges'])
    client.setKs(ks)

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