from pydantic import BaseModel, EmailStr, AnyUrl, Field
from typing import List, Optional

class Attachment(BaseModel):
    name: str = Field(..., description="Filename, e.g., sample.png")
    url: str = Field(..., description="data will be like data:image/png;base64,iVBOR...")

class ClientTask(BaseModel):
    email: EmailStr
    secret: str
    task: str
    round: int
    evaluation_url: AnyUrl
    nonce: Optional[str] = None
    brief: Optional[str] = None
    checks: Optional[List[str] | str] = None
    attachments: Optional[List[Attachment]] = None

# Ai Output model
class FileContent(BaseModel):
    """
    File content is required for building the static web page for github pages to pass checks
    """
    path: str = Field(..., description="file path") # index.html
    content: str = Field(..., description="file content") # <doctype...
    commit_message: str 

