from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from models.schemas import OCRResponse, AgoraTokenRequest, AgoraTokenResponse, CallNotifyRequest, CallNotifyResponse
from services.ocr_service import process_image_for_ocr
from services.agora_service import generate_agora_token
from services.firebase_service import verify_firebase_token
import uuid
import logging
import firebase_admin
from firebase_admin import messaging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/plate/ocr", response_model=OCRResponse)
async def ocr_plate(file: UploadFile = File(...)):
    """
    Receives an image, processes it to find the number plate string.
    """
    logger.info(f"OCR request received for file: {file.filename}, content_type: {file.content_type}")
    
    if not file.content_type or not file.content_type.startswith("image/"):
        logger.warning(f"Invalid content type: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image.")

    try:
        content = await file.read()
        logger.info(f"Read {len(content)} bytes from file")

        if not content:
            logger.error("Empty file uploaded")
            raise HTTPException(status_code=400, detail="Empty file uploaded.")

        logger.info("Starting OCR processing")
        plate_number = process_image_for_ocr(content)

        if plate_number:
            logger.info(f"OCR successful: '{plate_number}'")
            return OCRResponse(
                plate_number=plate_number,
                success=True,
                error=None
            )

        logger.warning("OCR processing returned no result")
        return OCRResponse(
            plate_number=None,
            success=False,
            error="Could not read number plate from image."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@router.post("/call/token", response_model=AgoraTokenResponse)
async def get_agora_token(
    request: AgoraTokenRequest,
    user_token: dict = Depends(verify_firebase_token)
):
    """
    Returns an Agora token for joining a video/audio channel.
    Requires a valid Firebase authentication token.
    """
    if user_token.get("uid") != request.caller_uid:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to generate token for this user."
        )

    try:
        unique_id = uuid.uuid4().hex[:8]
        channel_name = f"call_{request.caller_uid}_{request.receiver_uid}_{unique_id}"

        token_dict = generate_agora_token(channel_name)

        return AgoraTokenResponse(
            channel_name=token_dict["channel_name"],
            agora_token=token_dict["agora_token"],
            app_id=token_dict["app_id"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agora token generation failed: {str(e)}"
        )


@router.post("/call/notify", response_model=CallNotifyResponse)
async def notify_call(request: CallNotifyRequest):
    """
    Sends FCM notification to receiver for incoming call.
    """
    logger.info(f"Call notify request: {request.receiver_uid}, {request.channel_name}")
    
    try:
        # Get receiver's FCM token from Firestore
        firestore = firebase_admin.firestore.client()
        user_doc = firestore.collection('users').document(request.receiver_uid).get()
        
        if not user_doc.exists:
            logger.error(f"Receiver user not found: {request.receiver_uid}")
            return CallNotifyResponse(
                success=False,
                error="Receiver user not found"
            )
        
        user_data = user_doc.to_dict()
        fcm_token = user_data.get('fcm_token')
        
        if not fcm_token:
            logger.error(f"FCM token not found for user: {request.receiver_uid}")
            return CallNotifyResponse(
                success=False,
                error="Receiver FCM token not found"
            )
        
        # Send FCM notification
        message = messaging.Message(
            token=fcm_token,
            data={
                'type': 'incoming_call',
                'channelName': request.channel_name,
                'plateNumber': request.plate_number,
            },
            notification=messaging.Notification(
                title='Incoming Call',
                body=f'Incoming call from {request.plate_number}',
            ),
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    priority='high',
                    sound='default',
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        contentAvailable=True,
                        sound='default',
                        badge=1,
                    ),
                ),
            ),
        )
        
        response = messaging.send(message)
        logger.info(f"FCM notification sent: {response}")
        
        return CallNotifyResponse(success=True)
        
    except Exception as e:
        logger.error(f"Failed to send FCM notification: {e}", exc_info=True)
        return CallNotifyResponse(
            success=False,
            error=f"Failed to send notification: {str(e)}"
        )