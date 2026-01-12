from fastapi.middleware.cors import CORSMiddleware

CORS_CONFIG = {
    "allow_origins": ["*"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

def setup_cors(app):
    app.add_middleware(CORSMiddleware, **CORS_CONFIG)
