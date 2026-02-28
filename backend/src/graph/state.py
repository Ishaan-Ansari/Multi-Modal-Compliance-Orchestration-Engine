"""This module defines the global state of the graph execution."""

import operator
from typing import Annotated, List, Optional, Dict, TypedDict, Any

class ComplianceIssue(TypedDict):
    category: str
    description: str    # specific detail of violation
    severity: str       # CRITICAL, HIGH, MEDIUM, LOW
    timestamp: Optional[str]

# define the global state of the graph
class VideoAuditState:
    """Defines the data schema for Langgraph execution content"""
    video_url: str
    video_id: str

    local_file_path: Optional[str] 
    video_metadata: Optional[str, Any]
    transcript: Optional[str]
    ocr_text: List[str]

    # analysis results
    compliance_results: Annotated[List[ComplianceIssue], operator.add]

    # final deliverables
    final_status: str
    final_report: str

    # system observability
    # errors: API timeout, system level exceptions, etc.
    # system logs (stores crash logs, performance metrics, etc.)
    errors: List[str]

