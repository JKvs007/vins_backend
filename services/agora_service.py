import time
from agora_token_builder import RtcTokenBuilder
from core.config import settings


def generate_agora_token(channel_name: str, uid: int = 0) -> dict:
    expiration_time_in_seconds = 3600 * 24
    current_timestamp = int(time.time())
    privilege_expired_ts = current_timestamp + expiration_time_in_seconds

    token = RtcTokenBuilder.buildTokenWithUid(
        settings.AGORA_APP_ID,
        settings.AGORA_APP_CERTIFICATE,
        channel_name,
        uid,
        1,
        privilege_expired_ts
    )

    return {
        "channel_name": channel_name,
        "agora_token": token,
        "app_id": settings.AGORA_APP_ID
    }