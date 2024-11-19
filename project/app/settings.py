from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_SECRET_KEY: str
    STRIPE_ENDPOINT_SECRET: str
    DATABASE_URL: str
    SERVER_URL: str
    SECRET_KEY: str

    model_config = SettingsConfigDict(env_file=".env")
