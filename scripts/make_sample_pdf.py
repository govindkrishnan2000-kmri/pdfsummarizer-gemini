"""Generate samples/sample.pdf used for demos and end-to-end checks.

Run from the repo root:  python scripts/make_sample_pdf.py
"""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent.parent / "samples" / "sample.pdf"

TITLE = "Quarterly Operations Review"
AUTHOR = "Acme Analytics"
SUBJECT = "Sample document for the PDF summarizer"

SECTIONS = [
    (
        "Overview",
        "Acme Analytics closed the second quarter with revenue of 12.4 million dollars, "
        "an increase of 18 percent compared with the same period last year. Growth was "
        "driven by the subscription analytics product, which added 214 new enterprise "
        "customers. The operations team processed 1.2 million documents through the "
        "automated pipeline, up from 780 thousand in the previous quarter.",
    ),
    (
        "Key findings",
        "Customer retention improved to 94 percent, the highest level recorded by the "
        "company. Support response time fell from 6.5 hours to 2.1 hours after the "
        "introduction of an automated triage system. However, infrastructure costs rose "
        "by 27 percent, outpacing revenue growth and reducing the gross margin by two "
        "percentage points. The finance team attributes most of the increase to expanded "
        "compute capacity in three regions.",
    ),
    (
        "Risks and considerations",
        "Three risks require attention. First, reliance on a single cloud provider creates "
        "concentration risk; a multi-cloud pilot is scheduled for the next quarter. Second, "
        "the hiring plan assumes six additional engineers, but the current recruitment "
        "pipeline covers only four. Third, new data residency rules in two markets may "
        "require regional storage by the end of the year, adding an estimated 400 thousand "
        "dollars in annual cost.",
    ),
    (
        "Recommendations",
        "Leadership should approve the multi-cloud pilot budget of 250 thousand dollars, "
        "accelerate recruiting for the two open engineering roles, and begin a data "
        "residency assessment before the next board meeting. The team also recommends "
        "renegotiating the cloud contract, which expires in November, to secure volume "
        "discounts that could recover one percentage point of margin.",
    ),
]


def build() -> Path:
    pdf = FPDF()
    pdf.set_title(TITLE)
    pdf.set_author(AUTHOR)
    pdf.set_subject(SUBJECT)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 10, TITLE, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for heading, body in SECTIONS:
        pdf.set_font("Helvetica", "B", 13)
        pdf.multi_cell(0, 8, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 6, body, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size} bytes)")
