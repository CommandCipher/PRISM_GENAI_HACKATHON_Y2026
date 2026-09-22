from fastapi import FastAPI

app = FastAPI(
    title="Smart Guided Troubleshooting Engine",
    version="0.1.0"
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "troubleshooting-engine"
    }