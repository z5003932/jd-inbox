"""
JD Content Extraction Service
Uses Claude API to extract structured data from PDFs, images, Word docs
"""
import os
import base64
from pathlib import Path
from typing import Dict, Any
import anthropic

# Initialize Claude client
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not CLAUDE_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable not set")

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

async def extract_jd_content(file_path: str, file_ext: str) -> Dict[str, Any]:
    """
    Extract JD content from file using Claude API
    
    Returns:
        {
            "role": str,
            "company": str,
            "sector": str,  
            "mode": str,  # Remote/Hybrid/Onsite
            "jd_text": str  # Full JD text
        }
    """
    
    if file_ext in ['.pdf', '.png', '.jpg', '.jpeg']:
        # Use vision API for PDFs and images
        return await extract_via_vision(file_path, file_ext)
    elif file_ext in ['.docx', '.doc']:
        # Use python-docx for Word docs
        return await extract_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")

async def extract_via_vision(file_path: str, file_ext: str) -> Dict[str, Any]:
    """Extract JD content using Claude vision API"""
    
    # Read file as base64
    with open(file_path, 'rb') as f:
        file_data = base64.standard_b64encode(f.read()).decode('utf-8')
    
    # Determine media type
    media_type_map = {
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg'
    }
    media_type = media_type_map.get(file_ext, 'application/pdf')
    
    # Call Claude API
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document" if file_ext == '.pdf' else "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": file_data
                    }
                },
                {
                    "type": "text",
                    "text": """Extract the following from this job description:

1. Job title (extract exact title, e.g. "Senior Product Manager")
2. Company name
3. Sector (e.g. "FinTech", "HealthTech", "E-commerce", "Gov/Regulatory")  
4. Work mode (Remote / Hybrid / Onsite / Not specified)
5. Full job description text (all text content)

Respond in this exact JSON format:
{
  "role": "exact job title",
  "company": "company name",
  "sector": "sector",
  "mode": "work mode",
  "jd_text": "full JD text content"
}

If any field cannot be determined, use "Not specified" as the value."""
                }
            ]
        }]
    )
    
    # Parse response
    response_text = message.content[0].text
    
    # Extract JSON from response (handle markdown fences)
    import json
    import re
    
    # Remove markdown code fences if present
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response_text
    
    try:
        extracted = json.loads(json_str.strip())
    except json.JSONDecodeError:
        # Fallback: basic extraction
        extracted = {
            "role": "Not specified",
            "company": "Not specified",
            "sector": "Not specified",
            "mode": "Not specified",
            "jd_text": response_text
        }
    
    return extracted

async def extract_from_docx(file_path: str) -> Dict[str, Any]:
    """Extract JD content from Word document"""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx not installed. Run: pip install python-docx")
    
    doc = Document(file_path)
    
    # Extract all text
    full_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    
    # Use Claude to parse the text content
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""Extract the following from this job description:

1. Job title
2. Company name
3. Sector
4. Work mode (Remote/Hybrid/Onsite)

Job description text:
{full_text}

Respond in JSON format:
{{
  "role": "job title",
  "company": "company name",
  "sector": "sector",
  "mode": "work mode",
  "jd_text": "full text"
}}"""
        }]
    )
    
    response_text = message.content[0].text
    
    import json
    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response_text
    
    try:
        extracted = json.loads(json_str.strip())
        extracted['jd_text'] = full_text  # Use original text, not Claude's version
    except json.JSONDecodeError:
        extracted = {
            "role": "Not specified",
            "company": "Not specified",
            "sector": "Not specified",
            "mode": "Not specified",
            "jd_text": full_text
        }
    
    return extracted
