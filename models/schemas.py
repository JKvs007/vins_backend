from pydantic import BaseModel
from typing import Optional

class OCRResponse(BaseModel):
    plate_number: Optional[str] = None
    success: bool
    error: Optional[str] = None

class AgoraTokenRequest(BaseModel):
    caller_uid: str
    receiver_uid: str
    plate_number: str

class AgoraTokenResponse(BaseModel):
    channel_name: str
    agora_token: str
    app_id: str

class CallNotifyRequest(BaseModel):
    receiver_uid: str
    channel_name: str
    plate_number: str

class CallNotifyResponse(BaseModel):
    success: bool
    error: Optional[str] = None
