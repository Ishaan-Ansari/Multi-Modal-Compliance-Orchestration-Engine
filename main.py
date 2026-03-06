"""This module is the main entry point for the FastAPI application."""

import uvicorn
from fastapi import FastAPI

# Tasks imports
from backend.compliance import app as compliance_app

app = FastAPI()

@app.get("/app")
def read_main():
    return {"message": "Hello World from main app!"}


app.mount("/compliance", compliance_app)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)