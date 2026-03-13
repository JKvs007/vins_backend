import time
from agora_token_builder import RtcTokenBuilder
from config import settings


def generate_agora_token(channel_name: str, uid: int = 0) -> dict:
    if not settings.AGORA_APP_ID or not settings.AGORA_APP_CERTIFICATE:
        raise ValueError(
            "Agora configuration missing. Set AGORA_APP_ID and AGORA_APP_CERTIFICATE."
        )

    expiration_time_in_seconds = 3600 * 24
    current_timestamp = int(time.time())
    privilege_expired_ts = current_timestamp + expiration_time_in_seconds

    token = RtcTokenBuilder.buildTokenWithUid(
        settings.AGORA_APP_ID,
        settings.AGORA_APP_CERTIFICATE,
        channel_name,
        uid,
        1,
        privilege_expired_ts,
    )

    if not token:
      raise ValueError("Agora token builder returned an empty token.")

    return {
        "channel_name": channel_name,
        "agora_token": token,
        "app_id": settings.AGORA_APP_ID,
    }