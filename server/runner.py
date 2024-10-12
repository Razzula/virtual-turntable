"""Server runner for the FastAPI application."""
import uvicorn

if (__name__ == "__main__"):
    uvicorn.run('app.main:serverInstance.app', host="localhost", port=8491,
                # reload=True
)
