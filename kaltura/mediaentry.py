from datetime import datetime

class MediaEntry:
    DEFAULT_KEYS = ['id', 'views', 'lastPlayedAt','tags', 'categoriesIds', 'categories']
    @staticmethod
    def props(entry, keys=DEFAULT_KEYS):
        hsh = vars(entry)
        return {  k : MediaEntry.getval(hsh, k) for k in keys }

    @staticmethod
    def values(entry, keys=DEFAULT_KEYS):
        hsh = vars(entry)
        return  [MediaEntry.getval(hsh, k) for k in keys ]

    @staticmethod
    def playedDate(at):
        if (at != None):
            return datetime.utcfromtimestamp(at).strftime('%Y-%m-%d')
        else:
            return None

    @staticmethod
    def getval(entryhash, prop):
        if (prop == 'lastPlayedDate'):
            return MediaEntry.playedDate(entryhash['lastPlayedAt'])
        else:
            return entryhash[prop]