
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/compliance")
def read_compliance():
    return {"message": "Hello World from compliance app!"}