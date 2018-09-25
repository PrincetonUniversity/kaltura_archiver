from datetime import datetime

def playedDate(at):
    if (at != None):
        return datetime.utcfromtimestamp(at).strftime('%Y-%m-%d')
    else:
        return None

class MediaEntry:
    DEFAULT_KEYS = ['id', 'views', 'lastPlayedAt','tags', 'categoriesIds', 'categories']
    @staticmethod
    def props(entry, keys=DEFAULT_KEYS):
        hsh = vars(entry)
        return {  k : MediaEntry.getval(hsh, k) for k in keys }

    @staticmethod
    def getval(entryhash, prop):
        if (prop == 'lastPlayedDate'):
            return playedDate(entryhash['lastPlayedAt'])
        else:
            return entryhash[prop]

    @staticmethod
    def values(entry, keys=DEFAULT_KEYS):
        hsh = vars(entry)
        return  [MediaEntry.getval(hsh, k) for k in keys ]

    @staticmethod
    def join(sep, entry, columns):
        return (sep.join([str(v) for v in MediaEntry.values(entry, columns)]))