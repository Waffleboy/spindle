from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.database import init_db

app = FastAPI(title="Taxonomy Discovery Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.on_event("startup")
async def startup():
    init_db()


if __name__ == "__main__":
    import uvicorn

    from backend.config import get_settings

    _cfg = get_settings()
    uvicorn.run(app, host=_cfg.host, port=_cfg.port)
