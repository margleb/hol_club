import nats
from nats.aio.client import Client
from nats.js import JetStreamContext


async def connect_to_nats(servers: list[str]) -> tuple[Client, JetStreamContext]:
    nc: Client = await nats.connect(
        servers,
        allow_reconnect=False,
        connect_timeout=2,
        reconnect_time_wait=0,
        max_reconnect_attempts=1,
    )
    js: JetStreamContext = nc.jetstream()

    return nc, js
