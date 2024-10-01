"""FastAPI server application."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
async def root():
    """Health endpoint"""
    return await test()

@app.get("/test")
async def test():
    """Health endpoint"""
    return JSONResponse(content={"message": "Hello, World!"})
