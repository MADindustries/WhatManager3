import hashlib
from urllib.parse import urlparse

from torrents import bencode


def extract_domain(url):
    parsed = urlparse(url)
    return parsed.netloc


def hex_digest(value):
    return hashlib.sha1(value).hexdigest().upper()


def encode_announces(announces):
    for tier in announces:
        for announce in tier:
            if ';' in announce or ',' in announce:
                raise Exception('; or , in announce')
    result = ';'.join([','.join(tier) for tier in announces])
    return result


def hash_announces(announces):
    return hex_digest(encode_announces(announces).encode('utf-8'))


def decode_announces(announces):
    return [a.split(',') for a in announces.split(';')]


class TorrentInfo(object):
    def __init__(self, bdict):
        info = bdict[b'info']
        self.info_hash = hex_digest(bencode.bencode(info))
        if b'announce-list' in bdict:
            self.announces = [[a.decode('utf-8') for a in t] for t in bdict[b'announce-list']]
        else:
            self.announces = [[bdict[b'announce'].decode('utf-8')]]
        self.announces_hash = hash_announces(self.announces)

    @classmethod
    def from_binary(cls, data):
        bdict = bencode.bdecode(data)
        return TorrentInfo(bdict)

    @classmethod
    def from_file(cls, file_path):
        with open(file_path, 'rb') as f:
            return cls.from_binary(f.read())

