import time
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from urllib.parse import quote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from config import settings
from data.cache import cache
from data.models import Patent, Applicant

class BaseFetcher(ABC):
    def __init__(self):
        self.session = self._create_session()
        self.rate_limit_delay = 1.0 / getattr(settings, f"rate_limit_{self.source_name.lower()}", settings.rate_limit_eps)
    
    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        return session
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        pass
    
    @abstractmethod
    def build_query(self, material: str, year_start: int, year_end: int, **kwargs) -> str:
        pass
    
    @abstractmethod
    def fetch_patents(self, material: str, year_start: int, year_end: int, **kwargs) -> List[Dict[str, Any]]:
        pass
    
    def _rate_limit(self):
        time.sleep(self.rate_limit_delay)
    
    def _to_patent_model(self, raw: Dict[str, Any], material: str) -> Patent:
        return Patent(
            id=raw.get("id", ""),
            title=raw.get("title", ""),
            abstract=raw.get("abstract", ""),
            filing_date=self._parse_date(raw.get("filing_date")),
            publication_date=self._parse_date(raw.get("publication_date")),
            grant_date=self._parse_date(raw.get("grant_date")),
            expiry_date=self._parse_date(raw.get("expiry_date")),
            inventors=raw.get("inventors", []),
            applicants=[Applicant(name=a) for a in raw.get("applicants", [])],
            assignees=[Applicant(name=a) for a in raw.get("assignees", [])],
            ipc_classes=raw.get("ipc_classes", []),
            cpc_classes=raw.get("cpc_classes", []),
            status=raw.get("status", "unknown"),
            country_code=raw.get("country_code", "EP"),
            material_category=material,
            data_source=self.source_name,
        )
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y", "%Y"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

class EspacenetFetcher(BaseFetcher):
    source_name = "espacenet"
    def __init__(self):
        super().__init__()
        self.consumer_key = settings.espacenet_consumer_key
        self.consumer_secret = settings.espacenet_consumer_secret
        self.token = None
        self.token_expiry = 0
    
    def _get_token(self) -> Optional[str]:
        if self.token and time.time() < self.token_expiry - 60:
            return self.token
        if not self.consumer_key or not self.consumer_secret:
            return None
        try:
            auth_url = "https://ops.epo.org/3.2/auth/token"
            data = {"grant_type": "client_credentials", "client_id": self.consumer_key, "client_secret": self.consumer_secret}
            resp = self.session.post(auth_url, data=data)
            if resp.status_code == 200:
                token_data = resp.json()
                self.token = token_data["access_token"]
                self.token_expiry = time.time() + token_data["expires_in"]
                return self.token
        except Exception as e:
            logger.error(f"Espacenet auth error: {e}")
        return None
    
    def build_query(self, material: str, year_start: int, year_end: int, **kwargs) -> str:
        q = settings.queries[material]["keywords"]
        cpc = settings.queries[material]["cpc"]
        return f"({q}) AND (cpc={cpc}) AND (pd between {year_start} and {year_end})"
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_patents(self, material: str, year_start: int, year_end: int, **kwargs) -> List[Dict[str, Any]]:
        self._rate_limit()
        token = self._get_token()
        if not token:
            return []
        query = self.build_query(material, year_start, year_end)
        url = "https://ops.epo.org/3.2/rest-services/published-data/search"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        params = {"q": query, "Range": "1-100"}
        try:
            resp = self.session.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return self._parse_response(data, material)
        except Exception as e:
            logger.error(f"Espacenet fetch error: {e}")
        return []
    
    def _parse_response(self, data: Dict, material: str) -> List[Dict[str, Any]]:
        results = []
        docs = data.get("ops:world-patent-data", {}).get("exchange-documents", [])
        for doc in docs:
            biblio = doc.get("bibliographic-data", {})
            patent = {
                "id": biblio.get("publication-reference", {}).get("document-number", ""),
                "title": biblio.get("invention-title", {}).get("$", ""),
                "abstract": doc.get("abstract", {}).get("$", ""),
                "filing_date": biblio.get("application-reference", {}).get("date", ""),
                "publication_date": biblio.get("publication-reference", {}).get("date", ""),
                "inventors": [inv.get("inventor-name", {}).get("$", "") for inv in biblio.get("inventors", [])],
                "applicants": [app.get("applicant-name", {}).get("$", "") for app in biblio.get("applicants", [])],
                "cpc_classes": [cls.get("text", "") for cls in biblio.get("classifications-cpc", [])],
                "status": "granted" if biblio.get("grant-date") else "pending",
            }
            results.append(patent)
        return results

class USPTOFetcher(BaseFetcher):
    source_name = "uspto"
    def build_query(self, material: str, year_start: int, year_end: int, **kwargs) -> str:
        kw = settings.queries[material]["keywords"]
        return f'(_text_any:"{kw}") AND (_gte:"filing_date:{year_start}" AND _lte:"filing_date:{year_end}")'
    
    def fetch_patents(self, material: str, year_start: int, year_end: int, **kwargs) -> List[Dict[str, Any]]:
        self._rate_limit()
        api_key = settings.uspto_api_key
        if not api_key:
            return []
        url = "https://api.patentsview.org/patents/query"
        headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
        query_body = {
            "q": self.build_query(material, year_start, year_end),
            "f": ["patent_id", "patent_title", "patent_abstract", "filing_date", "grant_date", "inventor_name", "assignee_organization", "cpc_subgroup_id"],
            "s": [{"patent_id": "asc"}],
            "o": {"per_page": 100}
        }
        try:
            resp = self.session.post(url, json=query_body, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return self._parse_response(data, material)
        except Exception as e:
            logger.error(f"USPTO error: {e}")
        return []
    
    def _parse_response(self, data: Dict, material: str) -> List[Dict[str, Any]]:
        results = []
        for pat in data.get("patents", []):
            patent = {
                "id": pat.get("patent_id", ""),
                "title": pat.get("patent_title", ""),
                "abstract": pat.get("patent_abstract", ""),
                "filing_date": pat.get("filing_date", ""),
                "grant_date": pat.get("grant_date", ""),
                "inventors": [inv.get("inventor_name", "") for inv in pat.get("inventors", [])],
                "applicants": [ass.get("assignee_organization", "") for ass in pat.get("assignees", [])],
                "cpc_classes": [cpc.get("cpc_subgroup_id", "") for cpc in pat.get("cpc_subgroups", [])],
                "country_code": "US",
                "status": "granted" if pat.get("grant_date") else "pending",
            }
            results.append(patent)
        return results

class LensFetcher(BaseFetcher):
    source_name = "lens"
    def build_query(self, material: str, year_start: int, year_end: int, **kwargs) -> str:
        kw = settings.queries[material]["keywords"]
        return f'({kw}) AND (date_published:[{year_start}-01-01 TO {year_end}-12-31])'
    
    def fetch_patents(self, material: str, year_start: int, year_end: int, **kwargs) -> List[Dict[str, Any]]:
        self._rate_limit()
        token = settings.lens_bearer_token
        if not token:
            return []
        url = "https://api.lens.org/patent/search"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"query": {"boolean": {"operator": "AND", "operands": [{"term": self.build_query(material, year_start, year_end)}]}}, "size": 100}
        try:
            resp = self.session.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return self._parse_response(data, material)
        except Exception as e:
            logger.error(f"Lens error: {e}")
        return []
    
    def _parse_response(self, data: Dict, material: str) -> List[Dict[str, Any]]:
        results = []
        for doc in data.get("data", []):
            patent = {
                "id": doc.get("patent_number", ""),
                "title": doc.get("title", ""),
                "abstract": doc.get("abstract", ""),
                "filing_date": doc.get("filing_date", ""),
                "publication_date": doc.get("publication_date", ""),
                "inventors": [inv["name"] for inv in doc.get("inventors", [])],
                "applicants": [app["name"] for app in doc.get("applicants", [])],
                "cpc_classes": [cpc["code"] for cpc in doc.get("cpc_classifications", [])],
                "country_code": doc.get("jurisdiction", ""),
                "status": doc.get("legal_status", "unknown"),
            }
            results.append(patent)
        return results

class WIPOFetcher(BaseFetcher):
    source_name = "wipo"
    def build_query(self, material: str, year_start: int, year_end: int, **kwargs) -> str:
        kw = settings.queries[material]["keywords"]
        return f'EN_ALL:"{kw}" AND DP:({year_start}-{year_end})'
    def fetch_patents(self, material: str, year_start: int, year_end: int, **kwargs) -> List[Dict[str, Any]]:
        logger.info("WIPO fetcher: API pubblica limitata, restituisce vuoto")
        return []

class GooglePatentsScraper(BaseFetcher):
    source_name = "google"
    def build_query(self, material: str, year_start: int, year_end: int, **kwargs) -> str:
        kw = settings.queries[material]["keywords"]
        return f"{kw} after:{year_start} before:{year_end}"
    
    def fetch_patents(self, material: str, year_start: int, year_end: int, **kwargs) -> List[Dict[str, Any]]:
        self._rate_limit()
        query = self.build_query(material, year_start, year_end)
        url = f"https://patents.google.com/?q={quote(query)}&num=50"
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=30000)
                page.wait_for_selector("article", timeout=10000)
                elements = page.query_selector_all("article")
                patents = []
                for el in elements[:30]:
                    title_el = el.query_selector("h3")
                    title = title_el.inner_text() if title_el else ""
                    patent_id_el = el.query_selector("span.patent-number")
                    patent_id = patent_id_el.inner_text() if patent_id_el else ""
                    abstract_el = el.query_selector("div.abstract")
                    abstract = abstract_el.inner_text() if abstract_el else ""
                    patents.append({
                        "id": patent_id, "title": title, "abstract": abstract,
                        "filing_date": None, "inventors": [], "applicants": [],
                        "status": "unknown", "country_code": "US",
                    })
                browser.close()
                return patents
        except Exception as e:
            logger.error(f"Google scraping error: {e}")
            return []

class CompositePatentFetcher:
    def __init__(self):
        self.fetchers = [EspacenetFetcher(), USPTOFetcher(), LensFetcher(), WIPOFetcher(), GooglePatentsScraper()]
        self.cache = cache
    
    def _get_cache_key(self, material: str, year_start: int, year_end: int, **kwargs) -> str:
        return f"{material}_{year_start}_{year_end}_{hash(str(kwargs))}"
    
    def fetch_patents(self, material: str, year_start: int, year_end: int, force_refresh: bool = False, **kwargs) -> List[Patent]:
        cache_key = self._get_cache_key(material, year_start, year_end, **kwargs)
        if not force_refresh:
            cached = self.cache.get_api_result(cache_key)
            if cached:
                return [Patent(**p) for p in cached]
        all_patents = []
        for fetcher in self.fetchers:
            try:
                raw = fetcher.fetch_patents(material, year_start, year_end, **kwargs)
                if raw:
                    patents = [fetcher._to_patent_model(p, material) for p in raw]
                    all_patents.extend(patents)
                    if len(all_patents) >= 30:
                        break
            except Exception as e:
                logger.error(f"Fetcher {fetcher.source_name} failed: {e}")
        if not all_patents:
            all_patents = self._load_demo_patents(material, year_start, year_end)
        patent_dicts = [p.model_dump(mode="json") for p in all_patents]
        self.cache.set_api_result(cache_key, patent_dicts)
        return all_patents
    
    def _load_demo_patents(self, material: str, year_start: int, year_end: int) -> List[Patent]:
        demo_file = settings.demo_data_dir / "patents_sample.json"
        if not demo_file.exists():
            self._create_demo_dataset()
        with open(demo_file, "r") as f:
            data = json.load(f)
        patents = []
        for p in data:
            if p.get("material_category") == material and year_start <= p.get("filing_year", 0) <= year_end:
                patents.append(Patent(**p))
        return patents
    
    def _create_demo_dataset(self):
        demo_patents = [
            {"id": "EP1234567A1", "title": "Processo di pressofusione per leghe di Zama", "abstract": "...", "filing_date": "2021-03-15", "inventors": ["Rossi M."], "applicants": [{"name": "Fonderie Industriali S.p.A.", "country": "IT"}], "cpc_classes": ["B22D17/22"], "status": "granted", "country_code": "EP", "material_category": "Zama", "data_source": "demo", "filing_year": 2021},
            {"id": "US2022123456A1", "title": "Aluminium die casting method", "abstract": "...", "filing_date": "2020-06-20", "inventors": ["Johnson P."], "applicants": [{"name": "AutoTech GmbH", "country": "DE"}], "cpc_classes": ["B22D17/20"], "status": "granted", "country_code": "US", "material_category": "Alluminio", "data_source": "demo", "filing_year": 2020},
            {"id": "WO2023123456A1", "title": "Magnesium alloy die casting", "abstract": "...", "filing_date": "2022-09-01", "inventors": ["Chen W."], "applicants": [{"name": "Magnesium Research Inst.", "country": "CN"}], "cpc_classes": ["B22D17/00"], "status": "pending", "country_code": "WO", "material_category": "Magnesio", "data_source": "demo", "filing_year": 2022},
        ]
        settings.demo_data_dir.mkdir(exist_ok=True)
        with open(settings.demo_data_dir / "patents_sample.json", "w") as f:
            json.dump(demo_patents, f, indent=2)

patent_fetcher = CompositePatentFetcher()