import base64
import json
import pymupdf
from google import genai
from google.genai import types

class DocumentPipeline:
    def __init__(self, api_key: str, model: str = "gemini-3.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def pdf_to_base64_images(self, pdf_file) -> list[str]:
        """Reads a PDF in memory and converts its pages to base64-encoded PNG strings."""
        pdf_bytes = pdf_file.read()
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        base64_pages = []
        
        for i in range(len(doc)):
            page = doc[i]
            pix = page.get_pixmap(dpi=150) # Render page at 150 DPI
            png_bytes = pix.tobytes("png")
            b64_string = base64.b64encode(png_bytes).decode("utf-8")
            base64_pages.append(b64_string)
            
        return base64_pages

    def extract_metadata(self, base64_pages: list[str]) -> tuple[dict, int, int]:
        """Sends the first page of the document to extract metadata in JSON format."""
        if not base64_pages:
            return {}, 0, 0

        prompt = """
        Analyze the provided first page of a document. Output a JSON object containing:
        {
          "title": "Document Title",
          "doc_date": "YYYY-MM-DD",
          "category": "Project Schedule/Bid/Proposal/Technical Spec/Other",
          "author_org": "Creating Organization or Author",
          "visuals_detected": ["Gantt Chart", "Table", etc.],
          "confidence_score": "High/Medium/Low",
          "summary": "3-sentence executive summary of the document contents"
        }
        """
        
        first_page_bytes = base64.b64decode(base64_pages[0])
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=first_page_bytes, mime_type="image/png"),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        
        input_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
        output_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
        
        try:
            return json.loads(response.text.strip()), input_tokens, output_tokens
        except Exception as e:
            return {
                "title": "Unknown Document",
                "doc_date": None,
                "category": "Other",
                "author_org": "Unknown",
                "visuals_detected": [],
                "confidence_score": "Low",
                "summary": f"Could not parse JSON output from model. Error: {str(e)}"
            }, input_tokens, output_tokens

    def convert_page_to_markdown_stream(self, base64_page: str, page_num: int):
        """Processes a single page and yields raw chunk objects containing markdown and usage metadata."""
        prompt = f"""
        Convert page {page_num} of the document image into high-fidelity Markdown.
        Rules:
        1. Maintain layout structure (headings #, ##, bullet points, lists).
        2. Convert tables into Markdown table syntax.
        3. If there is an embedded visual, Gantt chart, or graphic:
           - Render a section header: ### [Visual Element: <Type>]
           - Write a highly-detailed prose interpretation detailing tasks, dates, names, timelines, or variables represented.
           - DO NOT truncate tables, skip tasks, or output summarized warnings. You must transcribe all visual timelines, tasks, and values in full.
        """
        
        page_bytes = base64.b64decode(base64_page)
        
        return self.client.models.generate_content_stream(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=page_bytes, mime_type="image/png"),
                prompt
            ]
        )
