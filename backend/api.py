from fastapi import FastAPI

app = FastAPI(title="AI is LOVE", version="0.1.0")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "AI is LOVE", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
