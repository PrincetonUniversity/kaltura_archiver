from datetime import datetime
import api

def playedDate(at):
    if (at != None):
        return datetime.utcfromtimestamp(at).strftime('%Y-%m-%d')
    else:
        return None

class MediaEntry:
    DEFAULT_KEYS = ['id', 'views', 'lastPlayedAt','tags', 'categoriesIds', 'categories']

    @staticmethod
    def getSourceFlavor(entry):
        flavorassetswparamslist = api.getClient().flavorAsset.getFlavorAssetsWithParams(entry.id)

        for flavorassetwparams in flavorassetswparamslist:
            flavorasset = flavorassetwparams.getFlavorAsset()

            if ( flavorasset is not None and flavorasset.getIsOriginal()):
                return flavorasset

        # If the original wasn't found
        return None

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



class FlavorAssetIterator:
    def __init__(self, entry):
        self.entry = entry
        self.flavorassetswparamslist = iter(api.getClient().flavorAsset.getFlavorAssetsWithParams(self.entry.id))

    def __iter__(self):
        return self

    def next(self):
        nxt = next(self.flavorassetswparamslist)
        if (nxt.getFlavorAsset() != None):
            return nxt.getFlavorAsset();
        return self.next()

