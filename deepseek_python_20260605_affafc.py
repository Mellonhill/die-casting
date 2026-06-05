import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    espacenet_consumer_key: Optional[str] = os.getenv("ESPACENET_CONSUMER_KEY")
    espacenet_consumer_secret: Optional[str] = os.getenv("ESPACENET_CONSUMER_SECRET")
    uspto_api_key: Optional[str] = os.getenv("USPTO_API_KEY")
    lens_bearer_token: Optional[str] = os.getenv("LENS_BEARER_TOKEN")
    
    cache_ttl_hours: int = 24
    cache_db_path: Path = Path("data/patent_cache.db")
    
    rate_limit_eps: float = 1.0
    rate_limit_espacenet: float = 0.5
    rate_limit_uspto: float = 2.0
    rate_limit_lens: float = 1.0
    rate_limit_wipo: float = 0.2
    rate_limit_google: float = 0.1
    
    data_dir: Path = Path("data")
    demo_data_dir: Path = Path("demo_data")
    logs_dir: Path = Path("logs")
    
    queries: dict = {
        "Zama": {
            "keywords": '"zinc alloy die casting" OR "zamak" OR "zinc pressure casting"',
            "cpc": "B22D17/* AND C22C18/*"
        },
        "Alluminio": {
            "keywords": '"aluminium die casting" OR "aluminum pressure die casting"',
            "cpc": "B22D17/* AND C22C21/*"
        },
        "Magnesio": {
            "keywords": '"magnesium die casting" OR "magnesium alloy pressure casting"',
            "cpc": "B22D17/* AND C22C23/*"
        }
    }
    
    default_year_start: int = 2010
    default_year_end: int = 2025
    nlp_max_features: int = 1000
    nlp_num_clusters: int = 8
    nlp_lda_topics: int = 10
    nlp_random_state: int = 42
    default_latitude: float = 40.0
    default_longitude: float = 10.0
    default_zoom: int = 4

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
settings.data_dir.mkdir(exist_ok=True)
settings.logs_dir.mkdir(exist_ok=True)
settings.demo_data_dir.mkdir(exist_ok=True)