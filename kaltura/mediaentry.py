from datetime import datetime
import api

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
            return api.dateString(entryhash['lastPlayedAt'])
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


class FlavorAssetStatus:
    """
    based on KalturaFlavorAssetStatus
    """
    _STRINGS = [
    "ERROR",
    "QUEUED", 
    "CONVERTING", 
    "READY", 
    "DELETED", 
    "NOT_APPLICABLE", 
    "TEMP", 
    "WAIT_FOR_CONVERT", 
    "IMPORTING", 
    "VALIDATING", 
    "EXPORTING" 
    ]
    @staticmethod
    def str(status):
        return FlavorAssetStatus._STRINGS[status.value + 1]
