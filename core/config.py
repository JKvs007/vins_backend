from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "VINS API"
    FIREBASE_CREDENTIALS: str = "firebase-adminsdk.json"
    AGORA_APP_ID: str = "cac8cce2a7744e0fbad92f729a24d93a"
    AGORA_APP_CERTIFICATE: str = "fe49c6e589b347669db58f537bbb6eb8"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()