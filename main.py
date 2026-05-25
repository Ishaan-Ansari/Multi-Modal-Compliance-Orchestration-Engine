"""This module is the main entry point for the FastAPI application."""

import uuid
import json
import uvicorn
from fastapi import FastAPI

# Tasks imports
from backend.compliance import app as compliance_app
from backend.src.graph.workflow import app
from logger import loggerMain as logger

def run():
    """
    Orchestrates the execution of entire audit workflow
    - Creates a unique session ID for each audit request
    - Prepares the video URL and metadata
    - Runs the AI workflow
    - Display the compliance results
    """

    # STEP 1:  Generate a unique session ID for the audit request
    session_id = str(uuid.uuid4())
    logger.info(f"Received audit request for video URL: Session ID: {session_id}")

    # STEP 2: Prepare the video URL and metadata
    initial_inputs = {
        "video_url": "https://example.com/video.mp4",
        "video_id": f"vid_{session_id[:8]}",
        "compliance_results": [],
        "errors": []
    }

    print("-----Initializing workflow------")
    print(f"Input Payload: {json.dumps(initial_inputs, indent=2)}")

    try:
        final_state = app.invoke(initial_inputs)
        print("\n-----Workflow execution is complete-----")
        print("\n-----COMPLIANCE AUDIT REPORT------")
        print(f"Video ID: {final_state.get('video_id')}")
        print(f"Status: {final_state.get('final_status')}")
        print("\n [VIOLATIONS DETECTED]")
        results = final_state.get("compliance_results", [])
        if results:
            for issue in results:
                print(f"- [{issue.get('severity')}] [{issue.get('category')}]: [{issue.get('description')}]")
        else:
            print("No compliance issues detected. The video is compliant.")
        
        print("\n[FINAL_SUMMARY]")
        print(final_state.get("final_report", "No summary available."))
    except Exception as e:
        logger.error(f"Error occurred while invoking the app: {e}")
        return

if __name__ == "__main__":    # Run the FastAPI app using Uvicorn
    run()