from dataclasses import dataclass

@dataclass(frozen=True)
class RetrievalProviderDecision:
    vector_store:str="pgvector"
    embedding_model:str="BAAI/bge-m3"
    vector_store_status:str="REUSE_EXTEND_BASELINE_CANDIDATE"
    embedding_status:str="REUSE_EXTEND_SYNTHETIC_BASELINE_CANDIDATE"
    production_approved:bool=False
    golden_dataset_required:bool=True

BASELINE=RetrievalProviderDecision()
