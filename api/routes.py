from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from models.schemas import OCRResponse, AgoraTokenRequest, AgoraTokenResponse
from services.ocr_service import process_image_for_ocr
from services.agora_service import generate_agora_token
from services.firebase_service import verify_firebase_token
import uuid

router = APIRouter()

@router.post("/plate/ocr", response_model=OCRResponse)
async def ocr_plate(file: UploadFile = File(...)):
    """
    Receives an image, processes it to find the number plate string.
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image.")

    content = await file.read()
    plate_number = process_image_for_ocr(content)
    
    if plate_number:
        return OCRResponse(plate_number=plate_number, success=True)
    
    return OCRResponse(success=False, error="Could not read number plate from image.")

@router.post("/call/token", response_model=AgoraTokenResponse)
async def get_agora_token(
    request: AgoraTokenRequest, 
    user_token: dict = Depends(verify_firebase_token)
):
    """
    Returns an Agora token for joining a video/audio channel.
    Requires a valid Firebase authentication token.
    """
    # Verify the user making the request matches the auth token
    if user_token.get('uid') != request.caller_uid:
        raise HTTPException(status_code=403, detail="Not authorized to generate token for this user.")

    # Generate a unique channel name if needed, or structured like call_uid1_uid2
    # The requirement specifically says channel_name is returned.
    unique_id = uuid.uuid4().hex[:8]
    channel_name = f"call_{request.caller_uid}_{request.receiver_uid}_{unique_id}"
    
    token_dict = generate_agora_token(channel_name)
    
    return AgoraTokenResponse(
        channel_name=token_dict["channel_name"],
        agora_token=token_dict["agora_token"],
        app_id=token_dict["app_id"]
    )
