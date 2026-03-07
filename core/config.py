from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "VINS API"
    FIREBASE_CREDENTIALS: str = "firebase-adminsdk.json"
    AGORA_APP_ID: str = ""
    AGORA_APP_CERTIFICATE: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
