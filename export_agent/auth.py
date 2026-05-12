import os

from vaultspeed_sdk.client import Client, TaskConfig, UnauthorizedException, UserPasswordAuthentication
from vaultspeed_sdk.system import System


def authenticate() -> tuple[Client, System]:
    url = os.environ["VS_URL"]
    username = os.environ["VS_USER"]
    password = os.environ["VS_PASSWORD"]

    auth = UserPasswordAuthentication(
        api_url=url,
        username=username,
        password=password,
    )
    client = Client(
        base_url=url,
        auth=auth,
        retries=2,
        timeout=120,
        caller="export_agent",
        task_config=TaskConfig(
            polling_interval=10,
            timeout=0,
            queue_timeout=600,
            show_progress=True,
        ),
    )
    system = System(client=client)
    return client, system
