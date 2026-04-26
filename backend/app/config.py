from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/scam_detector"

    # Google / Gmail
    google_client_id: str = ""
    google_client_secret: str = ""
    google_pubsub_topic: str = ""
    google_safe_browsing_api_key: str = ""

    # ML model paths
    classifier_model_path: str = "models/distilbert-scam"
    embedder_model_name: str = "all-MiniLM-L6-v2"
    chroma_persist_dir: str = "data/chroma"

    # Risk scoring thresholds
    flag_threshold: float = 0.70
    review_threshold: float = 0.50

    # Risk score weights (must sum to 1.0)
    weight_similarity: float = 0.40
    weight_classifier: float = 0.30
    weight_url: float = 0.20
    weight_headers: float = 0.10

    class Config:
        env_file = ".env"


settings = Settings()
