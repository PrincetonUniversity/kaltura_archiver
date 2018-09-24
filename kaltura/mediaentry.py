class MediaEntry:
    DEFAULT_KEYS = ['id', 'views', 'lastPlayedAt','tags', 'categoriesIds', 'categories']
    @staticmethod
    def props(i, keys=DEFAULT_KEYS):
        hsh = vars(i)
        return {  k : hsh[k] for k in keys }

    @staticmethod
    def values(i, keys=DEFAULT_KEYS):
        hsh = vars(i)
        return  [hsh[k] for k in keys ]
