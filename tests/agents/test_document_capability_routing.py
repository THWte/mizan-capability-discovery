from mizan_agents.document_routing import DocumentKind, DocumentProfile, PdfMode, Provider, RoutingStatus, RouteDecision, route_document


def test_born_digital_pdf_routes_to_docling_without_paddleocr():
    d = route_document(DocumentProfile(kind=DocumentKind.PDF, pdf_mode=PdfMode.BORN_DIGITAL))
    assert d.primary is Provider.DOCLING
    assert d.secondary is Provider.NONE
    assert "PADDLEOCR_ALWAYS_OCR" in d.reason_codes
    assert d.production_approved is False


def test_scanned_arabic_pdf_routes_to_paddleocr_serialized():
    d = route_document(DocumentProfile(kind=DocumentKind.PDF, pdf_mode=PdfMode.SCANNED, arabic_expected=True))
    assert d.primary is Provider.PADDLEOCR
    assert "NO_CONCURRENT_CONVERT" in d.execution_constraints
    assert any("WER_0_667" in x for x in d.reason_codes)
    assert d.production_approved is False


def test_scanned_table_never_claims_structure_solved():
    d = route_document(DocumentProfile(kind=DocumentKind.PDF, pdf_mode=PdfMode.SCANNED, arabic_expected=True, table_structure_required=True))
    assert d.status is RoutingStatus.REVIEW_REQUIRED
    assert "SCANNED_TABLE_STRUCTURE_NOT_ESTABLISHED" in d.unresolved


def test_office_formats_route_only_to_docling_candidate():
    for kind in (DocumentKind.DOCX, DocumentKind.XLSX, DocumentKind.PPTX):
        d = route_document(DocumentProfile(kind=kind))
        assert d.primary is Provider.DOCLING
        assert "PADDLEOCR_FORMAT_UNSUPPORTED" in d.reason_codes


def test_ambiguous_arabic_pdf_requires_review_and_optional_paddle_fallback():
    d = route_document(DocumentProfile(kind=DocumentKind.PDF, pdf_mode=PdfMode.AMBIGUOUS, arabic_expected=True))
    assert d.status is RoutingStatus.REVIEW_REQUIRED
    assert d.primary is Provider.DOCLING
    assert d.secondary is Provider.PADDLEOCR
    assert "ENGINE_DISAGREEMENT_REQUIRES_EVIDENCE_RESOLUTION" in d.unresolved


def test_router_cannot_production_approve_provider():
    try:
        RouteDecision(status=RoutingStatus.CANDIDATE_ROUTE, primary=Provider.DOCLING, production_approved=True)
        raised = False
    except ValueError:
        raised = True
    assert raised