from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import List, Optional
from database import get_db
from models import (
    JobCreate, JobResponse,
    CareerApplicationCreate, CareerApplicationResponse,
    DepartmentCreate, DepartmentResponse
)
from bson import ObjectId
from datetime import datetime
import cloudinary.uploader
from utils.auth import require_admin

router = APIRouter()

def job_helper(job) -> dict:
    return {
        "id": str(job["_id"]),
        "title": job["title"],
        "department": job["department"],
        "location": job["location"],
        "experience": job["experience"],
        "employmentType": job["employmentType"],
        "salary": job.get("salary"),
        "description": job["description"],
        "status": job.get("status", "active"),
        "createdAt": job.get("createdAt"),
        "updatedAt": job.get("updatedAt"),
    }

def application_helper(app) -> dict:
    return {
        "id": str(app["_id"]),
        "name": app["name"],
        "email": app["email"],
        "phone": app["phone"],
        "department": app.get("department"),
        "position": app["position"],
        "experience": app["experience"],
        "currentCTC": app["currentCTC"],
        "expectedCTC": app["expectedCTC"],
        "resume": app["resume"],
        "message": app.get("message"),
        "status": app.get("status", "Applied"),
        "createdAt": app.get("createdAt"),
    }

def seed_jobs_if_empty(db):
    if db.jobs.count_documents({}) == 0:
        now = datetime.now()
        initial_jobs = [
            {
                "title": "Sales Executive",
                "department": "Sales",
                "location": "New Delhi, Delhi",
                "experience": "2-4 years",
                "employmentType": "Full-time",
                "salary": "₹3,00,000 - ₹5,00,000 P.A.",
                "description": "Responsible for managing B2B client relations, product sales, and business expansion. Must have excellent communication skills.",
                "status": "active",
                "createdAt": now,
                "updatedAt": now
            },
            {
                "title": "Purchase Executive",
                "department": "Procurement",
                "location": "New Delhi, Delhi",
                "experience": "1-3 years",
                "employmentType": "Full-time",
                "salary": "₹2,50,000 - ₹4,00,000 P.A.",
                "description": "Coordinate with global suppliers to procure high-quality industrial components, manage purchase orders, and verify stock availability.",
                "status": "active",
                "createdAt": now,
                "updatedAt": now
            },
            {
                "title": "Electronics Engineer",
                "department": "Engineering",
                "location": "New Delhi, Delhi",
                "experience": "3-5 years",
                "employmentType": "Full-time",
                "salary": "₹4,50,000 - ₹7,00,000 P.A.",
                "description": "Design, test, and troubleshoot EV solutions, circular connectors, and custom wire harness assemblies. Hands-on experience with PCB design is a plus.",
                "status": "active",
                "createdAt": now,
                "updatedAt": now
            },
            {
                "title": "Digital Marketing Executive",
                "department": "Marketing",
                "location": "New Delhi, Delhi",
                "experience": "1-3 years",
                "employmentType": "Full-time",
                "salary": "₹3,00,000 - ₹4,50,000 P.A.",
                "description": "Formulate and run marketing strategies across B2B portals, manage social media profiles, optimize SEO, and generate quality industrial leads.",
                "status": "active",
                "createdAt": now,
                "updatedAt": now
            },
            {
                "title": "Backend Developer",
                "department": "IT & Software",
                "location": "New Delhi, Delhi",
                "experience": "2-4 years",
                "employmentType": "Full-time",
                "salary": "₹6,00,000 - ₹9,00,000 P.A.",
                "description": "Develop, scale, and maintain backend APIs using FastAPI/Node.js. Architect MongoDB databases and integrate third-party APIs.",
                "status": "active",
                "createdAt": now,
                "updatedAt": now
            },
            {
                "title": "Frontend Developer",
                "department": "IT & Software",
                "location": "New Delhi, Delhi",
                "experience": "2-4 years",
                "employmentType": "Full-time",
                "salary": "₹5,00,000 - ₹8,00,000 P.A.",
                "description": "Implement modern, fast, and responsive user interfaces using React, Next.js, and Framer Motion. Work closely with design and backend teams.",
                "status": "active",
                "createdAt": now,
                "updatedAt": now
            }
        ]
        db.jobs.insert_many(initial_jobs)

# JOBS API ENDPOINTS

@router.get("/jobs", response_model=List[JobResponse])
def get_jobs(active_only: bool = False):
    db = get_db()
    # seed_jobs_if_empty(db) # Disabled automatic seeder
    query = {"status": "active"} if active_only else {}
    jobs = list(db.jobs.find(query).sort("_id", -1))
    return [job_helper(job) for job in jobs]

@router.post("/jobs", response_model=JobResponse)
def create_job(job: JobCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    job_dict = job.model_dump()
    job_dict["createdAt"] = datetime.now()
    job_dict["updatedAt"] = datetime.now()
    result = db.jobs.insert_one(job_dict)
    job_dict["_id"] = result.inserted_id
    return job_helper(job_dict)

@router.put("/jobs/{job_id}", response_model=JobResponse)
def update_job(job_id: str, job: JobCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    
    job_dict = job.model_dump()
    job_dict["updatedAt"] = datetime.now()
    
    # Preserve original createdAt
    original = db.jobs.find_one({"_id": ObjectId(job_id)})
    if original and "createdAt" in original:
        job_dict["createdAt"] = original["createdAt"]
    else:
        job_dict["createdAt"] = datetime.now()

    result = db.jobs.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": job_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_dict["_id"] = ObjectId(job_id)
    return job_helper(job_dict)

@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    result = db.jobs.delete_one({"_id": ObjectId(job_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job deleted successfully"}


# APPLICATIONS API ENDPOINTS

@router.post("/apply", response_model=dict)
def apply_career(application: CareerApplicationCreate):
    db = get_db()
    app_dict = application.model_dump()
    app_dict["createdAt"] = datetime.now()
    result = db.careerApplications.insert_one(app_dict)
    return {"message": "Application submitted successfully", "id": str(result.inserted_id)}

@router.get("/applications", response_model=List[CareerApplicationResponse])
def get_applications():
    db = get_db()
    apps = list(db.careerApplications.find().sort("_id", -1))
    return [application_helper(app) for app in apps]

@router.put("/applications/{app_id}/status", response_model=CareerApplicationResponse)
def update_application_status(app_id: str, status: str, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(app_id):
        raise HTTPException(status_code=400, detail="Invalid application ID")
    
    valid_statuses = ["Applied", "Under Review", "Interview Scheduled", "Selected", "Rejected"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")
    
    result = db.careerApplications.update_one(
        {"_id": ObjectId(app_id)},
        {"$set": {"status": status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Application not found")
    
    updated_app = db.careerApplications.find_one({"_id": ObjectId(app_id)})
    return application_helper(updated_app)

@router.delete("/applications/{app_id}")
def delete_application(app_id: str, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(app_id):
        raise HTTPException(status_code=400, detail="Invalid application ID")
    result = db.careerApplications.delete_one({"_id": ObjectId(app_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"message": "Application deleted successfully"}


# RESUME UPLOAD ENDPOINT

@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    # Standard file check
    content_type = file.content_type
    allowed_types = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    
    # Sometimes octet-stream is sent, so we can also check the extension
    filename = file.filename or ""
    is_valid_ext = filename.endswith(".pdf") or filename.endswith(".doc") or filename.endswith(".docx")
    
    if content_type not in allowed_types and not is_valid_ext:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Please upload a PDF or Word document (.doc, .docx).")

    try:
        # Upload the file directly to Cloudinary
        result = cloudinary.uploader.upload(
            file.file,
            folder="aaj_tech/resumes",
            resource_type="auto"
        )
        return {"url": result.get("secure_url")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload resume to Cloudinary: {str(e)}")


# DEPARTMENT API ENDPOINTS

def department_helper(dept) -> dict:
    return {
        "id": str(dept["_id"]),
        "name": dept["name"],
        "createdAt": dept.get("createdAt")
    }

def seed_departments_if_empty(db):
    if db.departments.count_documents({}) == 0:
        now = datetime.now()
        default_depts = [
            {"name": "Sales", "createdAt": now},
            {"name": "Procurement", "createdAt": now},
            {"name": "Engineering", "createdAt": now},
            {"name": "Marketing", "createdAt": now},
            {"name": "IT & Software", "createdAt": now}
        ]
        db.departments.insert_many(default_depts)

@router.get("/departments", response_model=List[DepartmentResponse])
def get_departments():
    db = get_db()
    # seed_departments_if_empty(db) # Disabled automatic seeder
    departments = list(db.departments.find().sort("name", 1))
    return [department_helper(d) for d in departments]

@router.post("/departments", response_model=DepartmentResponse)
def create_department(dept: DepartmentCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    
    # Check if department already exists (case-insensitive)
    existing = db.departments.find_one({"name": {"$regex": f"^{dept.name}$", "$options": "i"}})
    if existing:
         raise HTTPException(status_code=400, detail="Department already exists")

    dept_dict = dept.model_dump()
    dept_dict["createdAt"] = datetime.now()
    result = db.departments.insert_one(dept_dict)
    dept_dict["_id"] = result.inserted_id
    return department_helper(dept_dict)

@router.delete("/departments/{dept_id}")
def delete_department(dept_id: str, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(dept_id):
        raise HTTPException(status_code=400, detail="Invalid department ID")
    
    # Optional check: are there active jobs in this department?
    # For now, let's just delete the department.
    result = db.departments.delete_one({"_id": ObjectId(dept_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Department not found")
    return {"message": "Department deleted successfully"}
