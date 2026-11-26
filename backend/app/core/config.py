from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    keitaro_api_key: str = "test-key"
    keitaro_base_url: str = "https://keitaro-for-tests.etolegko.com/admin_api/v1"
    database_url: str = "postgresql+psycopg://adrobot:adrobot@localhost:5432/adrobot"
    keitaro_domain_id: int = 1813
    keitaro_group_id: int = 10332
    keitaro_source_id: int = 836
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
