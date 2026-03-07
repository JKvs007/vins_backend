import time
from agora_token_builder import RtcTokenBuilder
from core.config import settings
import uuid

def generate_agora_token(channel_name: str, uid: int = 0) -> dict:
    """
    Generates a temporary Agora token for joining a video/audio call.
    Uses Agora RTC Token Builder.
    """
    # 24 hours expiration
    expiration_time_in_seconds = 3600 * 24 
    current_time_stamp = int(time.time())
    privilege_expired_ts = current_time_stamp + expiration_time_in_seconds

    token = RtcTokenBuilder.buildTokenWithUid(
        settings.AGORA_APP_ID, 
        settings.AGORA_APP_CERTIFICATE, 
        channel_name, 
        uid, 
        Role_Attendee, 
        privilege_expired_ts
    )
    
    return {
        "channel_name": channel_name,
        "agora_token": token,
        "app_id": settings.AGORA_APP_ID
    }
