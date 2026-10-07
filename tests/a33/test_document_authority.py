from mizan_agents.document_authority import *

def test_mixed_official_judgment_then_appended_analysis():
    pages=[]
    for n in range(1,32):
        text="وزارة العدل\nالمحكمة الجزائية بمكة المكرمة\nصك رقم: 123456\nمتن الحكم"
        if n==31:
            text+="\nسقط حقه في طلب الاستئناف\nرئيس الدائرة القضائية"
        pages.append((n,text))
    for n in range(32,52):
        # Deliberately retain the official-looking header: this reproduces the
        # hard mixed-document pattern without using any real case data.
        text="وزارة العدل\nالمحكمة الجزائية\nصك رقم: 123456\nتحليل صك الحكم\nأعد هذا التحليل استنادًا إلى نص الصك"
        pages.append((n,text))
    classified=classify_authority_pages(pages)
    segments=build_authority_segments(classified)
    assert len(classified)==51
    assert classified[0].kind is AuthorityKind.OFFICIAL_COURT
    assert classified[30].kind is AuthorityKind.OFFICIAL_COURT
    assert classified[31].kind is AuthorityKind.APPENDED_ANALYSIS
    assert classified[-1].kind is AuthorityKind.APPENDED_ANALYSIS
    assert [(s.kind,s.first_page,s.last_page) for s in segments]==[
        (AuthorityKind.OFFICIAL_COURT,1,31),
        (AuthorityKind.APPENDED_ANALYSIS,32,51),
    ]

def test_quoted_memorandum_inside_judgment_does_not_change_authority():
    pages=[
        (1,"وزارة العدل\nالمحكمة الجزائية\nصك رقم: 999999"),
        (2,"قدم وكيل المدعى عليه مذكرة جوابية جاء فيها كذا"),
        (3,"الأسباب والحكم"),
    ]
    got=classify_authority_pages(pages)
    assert all(p.kind is AuthorityKind.OFFICIAL_COURT for p in got)

def test_analysis_marker_before_official_end_is_not_enough_to_demote_court_page():
    pages=[
        (1,"وزارة العدل\nالمحكمة الجزائية\nصك رقم: 999999"),
        (2,"ناقشت المحكمة تحليل صك الحكم المقدم من الخصم"),
        (3,"رئيس الدائرة القضائية"),
    ]
    got=classify_authority_pages(pages)
    assert all(p.kind is AuthorityKind.OFFICIAL_COURT for p in got)

def test_unknown_document_is_not_silently_promoted_to_official():
    got=classify_authority_pages([(1,"نص بلا مصدر واضح"),(2,"تكملة")])
    assert all(p.kind is AuthorityKind.UNKNOWN for p in got)
