"""Configuration globale de l'application CSBOT via Pydantic Settings."""

from typing import List, Optional
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # --- TELEGRAM BOT CONFIG ---
    BOT_TOKEN: str = Field(default="", description="Jeton API du bot Telegram")
    COPRO_CHAT_ID: int = Field(default=0, description="ID du groupe Telegram de la copropriété")
    CS_GROUP_ID: int = Field(default=0, description="ID du groupe privé du Conseil Syndical")
    ADMIN_IDS: List[int] = Field(default_factory=list, description="Liste des IDs Telegram des super-admins")

    # --- DATABASE CONFIG (MariaDB / MySQL) ---
    DB_USER: str = Field(default="root")
    DB_PASSWORD: str = Field(default="")
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=3306)
    DB_NAME: str = Field(default="csbot")
    CUSTOM_DATABASE_URL: Optional[str] = Field(default=None, alias="DATABASE_URL")

    @computed_field
    @property
    def database_url(self) -> str:
        if self.CUSTOM_DATABASE_URL:
            return self.CUSTOM_DATABASE_URL
        return f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    # --- CPTCOPRO INTEGRATION (Lecture des finances & lots) ---
    CPTCOPRO_DB_USER: Optional[str] = Field(default=None)
    CPTCOPRO_DB_PASSWORD: Optional[str] = Field(default=None)
    CPTCOPRO_DB_HOST: Optional[str] = Field(default=None)
    CPTCOPRO_DB_PORT: int = Field(default=3306)
    CPTCOPRO_DB_NAME: Optional[str] = Field(default=None)

    @computed_field
    @property
    def cptcopro_database_url(self) -> Optional[str]:
        if not self.CPTCOPRO_DB_NAME:
            return None
        user = self.CPTCOPRO_DB_USER or self.DB_USER
        password = self.CPTCOPRO_DB_PASSWORD or self.DB_PASSWORD
        host = self.CPTCOPRO_DB_HOST or self.DB_HOST
        port = self.CPTCOPRO_DB_PORT or self.DB_PORT
        return f"mysql+asyncmy://{user}:{password}@{host}:{port}/{self.CPTCOPRO_DB_NAME}?charset=utf8mb4"

    # --- IA / LLM PROVIDERS ---
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Clé API Google Gemini")
    MISTRAL_API_KEY: Optional[str] = Field(default=None, description="Clé API Mistral AI")
    DEFAULT_LLM_PROVIDER: str = Field(default="gemini", description="Fournisseur par défaut: gemini ou mistral")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash")
    MISTRAL_MODEL: str = Field(default="mistral-medium-latest")

    # --- N8N INTEGRATION ---
    N8N_WEBHOOK_URL: Optional[str] = Field(default=None, description="URL du Webhook n8n pour les requêtes complexes / tickets")
    N8N_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Secret partagé avec n8n pour authentifier les alertes entrantes")
    WEBHOOK_SERVER_HOST: str = Field(default="0.0.0.0")
    WEBHOOK_SERVER_PORT: int = Field(default=8088)

    # --- PROCEDURES & CONTACTS D'URGENCE ---
    EMERGENCY_ASCENSEUR_PHONE: str = Field(default="08 00 00 00 00", description="Numéro astreinte 24/7 ascensoriste")
    EMERGENCY_CHAUFFAGE_PHONE: str = Field(default="08 00 00 00 00", description="Numéro astreinte chauffagiste")
    EMERGENCY_PLOMBERIE_PHONE: str = Field(default="08 00 00 00 00", description="Numéro astreinte plomberie d'urgence")
    WATER_VALVE_LOCATION: str = Field(default="Au sous-sol, à gauche de la porte coupe-feu.")
    GAS_VALVE_LOCATION: str = Field(default="Dans le coffret extérieur jaune sur le trottoir.")
    ELECTRIC_ROOM_LOCATION: str = Field(default="Local TGBT au rez-de-chaussée près du local vélos.")

    # --- ENCOMBRANTS ---
    ENCOMBRANTS_SCHEDULE: str = Field(default="1er mardi de chaque mois", description="Jour de ramassage des encombrants")


settings = Settings()

