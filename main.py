from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from services.firebase_service import initialize_firebase

app = FastAPI(
    title="VINS Backend API",
    description="Privacy-First Vehicle Identification & Contact System API",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
    initialize_firebase()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def read_root():
    return {"status": "VINS Backend is running. Privacy first."}