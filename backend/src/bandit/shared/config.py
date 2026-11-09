"""Configuración tipada, cargada desde el entorno."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./var/bandit.db"

    session_ttl_hours: int = Field(default=12, ge=1)
    camera_encryption_key: str = ""
    cookie_secure: bool = False
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    # Solo para pruebas: crea la cuenta admin/admin. Apágalo en un local real.
    demo_admin: bool = False

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    # Opcional: otro modelo solo para extraer el directorio, por ejemplo uno menos saturado.
    gemini_directory_model: str = ""
    gemini_media_resolution: str = "high"
    gemini_max_concurrency: int = Field(default=4, ge=1)
    analysis_min_interval_seconds: float = Field(default=10, gt=0)
    analysis_daily_call_limit: int = Field(default=4320, ge=0)
    analysis_motion_threshold: float = Field(default=0.02, ge=0, le=1)
    analysis_confirmation_frames: int = Field(default=2, ge=1)
    analysis_cooldown_seconds: float = Field(default=120, ge=0)

    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_template_name: str = "bandit_incidente"
    whatsapp_template_language: str = "es"
    whatsapp_api_version: str = "v23.0"

    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@example.com"

    directory_scrape_interval_hours: int = Field(default=24, ge=1)
    revalidate_secret: str = ""
    frontend_internal_url: str = "http://frontend:3000"
    media_root: str = "./var/media"

    evidence_retention_days: int = Field(default=7, ge=1)
    ffmpeg_path: str = "ffmpeg"
    video_fps: int = Field(default=8, ge=1, le=30)
    video_width: int = Field(default=960, ge=160)

    # Nube de Imou: solo para cámaras registradas como imou://
    imou_app_id: str = ""
    imou_app_secret: str = ""
    imou_api_url: str = "https://openapi-or.easy4ip.com/openapi"

    # OpenStreetMap: geocodificación, CAI cercanos y mosaicos del mapa. Sus políticas de uso
    # piden un User-Agent que identifique la aplicación.
    osm_user_agent: str = "Bandit/1.0 (vigilancia para bares y restaurantes)"


@lru_cache
def get_settings() -> Settings:
    return Settings()
