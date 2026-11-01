from datetime import date
from pydantic import BaseModel, Field, model_validator


class PolicyMetadata(BaseModel):
    carrier: str = Field(min_length=1, max_length=255)
    policy_number: str = Field(min_length=1, max_length=255)
    product_name: str = Field(min_length=1, max_length=255)
    jurisdiction: str | None = None
    policy_holder: str | None = None
    effective_date: date
    expiry_date: date
    version_label: str = "1.0"
    source_metadata: str | None = None

    @model_validator(mode="after")
    def validate_coverage_period(self) -> "PolicyMetadata":
        if self.expiry_date < self.effective_date:
            raise ValueError("expiry_date must not be before effective_date")
        return self


class PolicyCreate(BaseModel):
    carrier: str = Field(min_length=1, max_length=255)
    policy_number: str = Field(min_length=1, max_length=255)
    product_name: str = Field(min_length=1, max_length=255)
    jurisdiction: str | None = Field(default=None, max_length=255)
    policy_holder: str | None = Field(default=None, max_length=255)


class PolicyVersionCreate(BaseModel):
    effective_date: date
    expiry_date: date
    version_label: str = Field(default="1.0", min_length=1, max_length=100)
    source_metadata: str | None = None

    @model_validator(mode="after")
    def validate_coverage_period(self) -> "PolicyVersionCreate":
        if self.expiry_date < self.effective_date:
            raise ValueError("expiry_date must not be before effective_date")
        return self


class PolicySummary(BaseModel):
    id: int
    carrier: str
    policy_number: str
    product_name: str
    jurisdiction: str | None
    policy_holder: str | None


class VersionSummary(BaseModel):
    id: int
    effective_date: date
    expiry_date: date
    version_label: str


class DocumentSummary(BaseModel):
    id: int
    policy_version_id: int
    filename: str
    media_type: str
    byte_size: int
    sha256: str
    validation_state: str


class PageSummary(BaseModel):
    id: int
    page_index: int
    page_number: int
    text_length: int
    content_hash: str


class ClauseSummary(BaseModel):
    id: int
    heading: str | None
    title: str | None
    text: str
    page_number: int
    start_offset: int
    end_offset: int
    ordinal: int
    segmentation_method: str


class IngestionResult(BaseModel):
    document: DocumentSummary
    policy: PolicySummary
    version: VersionSummary
    duplicate: bool = False
    page_count: int = 0
    clause_count: int = 0
