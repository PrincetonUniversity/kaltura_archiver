import api

from KalturaClient.Plugins.Core import KalturaMediaEntry

class MediaEntry:
    def __init__(self, entry):
        self.entry = entry

    def getTotalSize(self):
        size = 0
        for f in FlavorAssetIterator(self.entry):
            if (f.getSize()):
                size += f.getSize()
        return size

    def getLastPlayedDate(self):
        return api.dateString(self.entry.getLastPlayedAt())




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
