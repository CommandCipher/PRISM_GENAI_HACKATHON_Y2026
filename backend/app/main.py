from fastapi import FastAPI
from app.api import router
from app.device_brain.catalog import DeviceCatalog

app = FastAPI(
    title="Smart Guided Troubleshooting Engine",
    version="0.2.0",
)
app.include_router(router)

@app.get("/health")
def health():
    catalog = DeviceCatalog()
    return {
        "status": "ok",
        "service": "troubleshooting-engine",
        "scenarios_loaded": len(catalog.scenarios),
        "deeplinks_loaded": len(catalog.deeplinks),
    }
