from __future__ import annotations
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import os

def setup_cors(app: FastAPI, allow_all: bool = True) -> None:
    if allow_all and not os.getenv("ALLOWED_ORIGINS"):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        return

    origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS","").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost","http://127.0.0.1"],
        allow_credentials=True,
        allow_methods=["GET","POST","PATCH","DELETE","PUT","OPTIONS"],
        allow_headers=["Authorization","Content-Type","If-None-Match","If-Modified-Since","X-Request-Id","X-Idempotency-Key"],
    )