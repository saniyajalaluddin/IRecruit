"""Integration tests for secure resume upload, validation, sanitization, and attack vectors."""

import io
import pytest
import pypdf
import docx


def create_minimal_pdf() -> bytes:
    """Generates a valid minimal PDF binary in-memory."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


def create_minimal_docx() -> bytes:
    """Generates a valid minimal DOCX binary in-memory."""
    doc = docx.Document()
    doc.add_paragraph("Candidate Resume text with Python, FastAPI, and SQL experience.")
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


@pytest.mark.asyncio
async def test_valid_pdf_upload_anonymous(async_client):
    """Verify anonymous user can upload a valid PDF and receive a valid resume_id."""
    pdf_bytes = create_minimal_pdf()
    files = {"file": ("my_resume.pdf", pdf_bytes, "application/pdf")}
    data = {"title": "My Software Resume"}

    response = await async_client.post("/api/v1/resumes/upload", files=files, data=data)
    assert response.status_code == 201
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["format"] == "pdf"
    assert payload["data"]["is_anonymous"] is True
    assert payload["data"]["resume_id"] is not None


@pytest.mark.asyncio
async def test_valid_docx_upload_authenticated(async_client):
    """Verify authenticated user can upload a DOCX resume linked to their account."""
    # Register and obtain token
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "docx.uploader@example.com", "password": "Password123!", "full_name": "Docx User"},
    )
    token = reg_res.json()["data"]["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    docx_bytes = create_minimal_docx()
    files = {"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

    response = await async_client.post("/api/v1/resumes/upload", files=files, headers=headers)
    assert response.status_code == 201
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["format"] == "docx"
    assert payload["data"]["is_anonymous"] is False


@pytest.mark.asyncio
async def test_valid_txt_upload(async_client):
    """Verify uploading a plain UTF-8 text resume succeeds."""
    txt_content = "Candidate Jane Doe\nSkills: Python, AWS, Docker".encode("utf-8")
    files = {"file": ("resume.txt", txt_content, "text/plain")}

    response = await async_client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 201
    payload = response.json()
    assert payload["data"]["format"] == "txt"


@pytest.mark.asyncio
async def test_empty_file_upload_rejected(async_client):
    """Verify empty 0-byte file is rejected with 400 Bad Request."""
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    response = await async_client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNSUPPORTED_DOCUMENT"


@pytest.mark.asyncio
async def test_oversized_file_upload_rejected(async_client):
    """Verify file exceeding 5MB is rejected with 400 Bad Request without crashing."""
    # 5.1 MB dummy content with PDF magic bytes
    oversized_bytes = b"%PDF-1.4\n" + b"A" * (5 * 1024 * 1024 + 1024)
    files = {"file": ("oversized.pdf", oversized_bytes, "application/pdf")}

    response = await async_client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNSUPPORTED_DOCUMENT"


@pytest.mark.asyncio
async def test_spoofed_extension_rejected(async_client):
    """Verify an invalid file disguised as a PDF fails magic byte / structural check."""
    fake_pdf = b"MZ\x90\x00\x03\x00FakePEHeaderNotPDF"
    files = {"file": ("malware.pdf", fake_pdf, "application/pdf")}

    response = await async_client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNSUPPORTED_DOCUMENT"


@pytest.mark.asyncio
async def test_unsupported_extension_rejected(async_client):
    """Verify executable or script extensions are rejected immediately."""
    files = {"file": ("script.py", b"print('hello')", "text/x-python")}
    response = await async_client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False


@pytest.mark.asyncio
async def test_path_traversal_filename_sanitization(async_client):
    """Verify path traversal filenames are neutralized and cannot escape sandbox."""
    pdf_bytes = create_minimal_pdf()
    traversal_name = "../../../../../etc/shadow.pdf"
    files = {"file": (traversal_name, pdf_bytes, "application/pdf")}

    response = await async_client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 201
    payload = response.json()
    assert ".." not in payload["data"]["title"]
    assert "etc" not in payload["data"]["title"]
