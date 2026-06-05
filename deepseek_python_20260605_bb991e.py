from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field, field_validator

class Applicant(BaseModel):
    name: str
    country: Optional[str] = None
    city: Optional[str] = None
    organization_type: Optional[str] = None

class Citation(BaseModel):
    patent_id: str
    title: Optional[str] = None
    relationship: str
    date: Optional[date] = None

class Patent(BaseModel):
    id: str
    title: str
    abstract: str
    application_number: Optional[str] = None
    publication_number: Optional[str] = None
    ipc_classes: List[str] = Field(default_factory=list)
    cpc_classes: List[str] = Field(default_factory=list)
    filing_date: Optional[date] = None
    publication_date: Optional[date] = None
    grant_date: Optional[date] = None
    expiry_date: Optional[date] = None
    inventors: List[str] = Field(default_factory=list)
    applicants: List[Applicant] = Field(default_factory=list)
    assignees: List[Applicant] = Field(default_factory=list)
    status: str
    country_code: str = "EP"
    legal_status: Optional[Dict[str, Any]] = None
    forward_citations: List[Citation] = Field(default_factory=list)
    backward_citations: List[Citation] = Field(default_factory=list)
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    material_category: str
    data_source: str

    @field_validator("material_category")
    @classmethod
    def validate_material(cls, v: str) -> str:
        allowed = {"Zama", "Alluminio", "Magnesio"}
        if v not in allowed:
            raise ValueError(f"Materiale {v} non riconosciuto")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"granted", "pending", "expired", "unknown"}
        if v not in allowed:
            raise ValueError(f"Status {v} non valido")
        return v

class FTOScore(BaseModel):
    patent_id: str
    score: float
    age_factor: float
    citation_factor: float
    claim_factor: float
    risk_level: str