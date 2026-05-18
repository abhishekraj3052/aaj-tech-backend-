from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import categories, products, blogs, enquiries, catalog, dashboard, clients, auth, uploads, harness
import uvicorn
import os
import cloudinary
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Aaj Tech Trading API")

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(categories.router, prefix="/api/categories", tags=["Categories"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(blogs.router, prefix="/api/blogs", tags=["Blogs"])
app.include_router(enquiries.router, prefix="/api/enquiries", tags=["Enquiries"])
app.include_router(catalog.router, prefix="/api/catalog", tags=["Catalog"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(clients.router, prefix="/api/clients", tags=["Clients"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(uploads.router, prefix="/api/upload", tags=["Upload"])
app.include_router(harness.router, prefix="/api/harness", tags=["Harness Products"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Aaj Tech Trading API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
