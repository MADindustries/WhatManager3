import asyncio
import os
from torrent_client_backends.transmission import TorrentClient

client = TorrentClient('http://localhost:9091/transmission/rpc')

loop = asyncio.get_event_loop()
res = loop.run_until_complete(client.get_torrents(['1896a1693a8de4b6f0e5a3963e4b2aa6f6ae01e3']))
print(res)
