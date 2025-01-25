"""Server runner for the FastAPI application."""
import uvicorn

if (__name__ == "__main__"):
    uvicorn.run('app.main:serverInstance.app', host="0.0.0.0", port=8491,
                # reload=True
)
