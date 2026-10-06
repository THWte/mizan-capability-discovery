"""MIZAN Golden Dataset Contract v1 — A15."""
from __future__ import annotations
import dataclasses, hashlib
from enum import Enum


class GoldenDatasetError(ValueError):
    pass


class DatasetTier(str,Enum):
    SYNTHETIC="SYNTHETIC"
    ANONYMIZED_VERIFIED="ANONYMIZED_VERIFIED"
    REAL_VERIFIED="REAL_VERIFIED"


@dataclasses.dataclass(frozen=True,kw_only=True)
class GoldenCase:
    case_id:str
    query:str
    relevant_citation_ids:tuple[str,...]
    relevant_span_locators:tuple[str,...]
    label_source:str
    independently_reviewed:bool
    tier:DatasetTier
    notes:str=""

    def __post_init__(self):
        if not self.case_id or not self.query:
            raise GoldenDatasetError("case_id and query are required")
        if not self.relevant_citation_ids or not self.relevant_span_locators:
            raise GoldenDatasetError("gold label requires citation and locator targets")
        if len(self.relevant_citation_ids) != len(self.relevant_span_locators):
            raise GoldenDatasetError("citation/locator target cardinality mismatch")
        if self.tier != DatasetTier.SYNTHETIC and not self.independently_reviewed:
            raise GoldenDatasetError("non-synthetic gold labels require independent review")
        if not self.label_source:
            raise GoldenDatasetError("label_source is required")


@dataclasses.dataclass(frozen=True,kw_only=True)
class GoldenDatasetManifest:
    dataset_id:str
    version:str
    cases:tuple[GoldenCase,...]
    provenance_note:str
    sha256:str

    def __post_init__(self):
        if not self.cases:
            raise GoldenDatasetError("golden dataset cannot be empty")
        if len({c.case_id for c in self.cases}) != len(self.cases):
            raise GoldenDatasetError("duplicate golden case_id")
        if len(self.sha256)!=64 or any(ch not in "0123456789abcdef" for ch in self.sha256):
            raise GoldenDatasetError("manifest sha256 must be lowercase hex")


def manifest_sha256(cases:tuple[GoldenCase,...],*,dataset_id:str,version:str,provenance_note:str)->str:
    rows=[]
    for c in sorted(cases,key=lambda x:x.case_id):
        rows.append("|".join([
            c.case_id,c.query,",".join(c.relevant_citation_ids),",".join(c.relevant_span_locators),
            c.label_source,str(c.independently_reviewed),c.tier.value,c.notes
        ]))
    material=(dataset_id+"\n"+version+"\n"+provenance_note+"\n"+"\n".join(rows)).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def build_manifest(*,dataset_id:str,version:str,cases:tuple[GoldenCase,...],provenance_note:str)->GoldenDatasetManifest:
    return GoldenDatasetManifest(
        dataset_id=dataset_id,version=version,cases=cases,provenance_note=provenance_note,
        sha256=manifest_sha256(cases,dataset_id=dataset_id,version=version,provenance_note=provenance_note),
    )


def production_eligible_dataset(manifest:GoldenDatasetManifest)->bool:
    # Synthetic-only benchmarks can guide development but never approve production.
    return all(c.tier in (DatasetTier.ANONYMIZED_VERIFIED,DatasetTier.REAL_VERIFIED) and c.independently_reviewed for c in manifest.cases)
