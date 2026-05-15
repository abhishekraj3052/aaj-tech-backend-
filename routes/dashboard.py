from fastapi import APIRouter
from database import get_db
from datetime import datetime

router = APIRouter()
db = get_db()

@router.get("/")
def get_dashboard_data():
    total_products = db.products.count_documents({})
    total_enquiries = db.enquiries.count_documents({})
    total_clients = len(db.enquiries.distinct("email"))
    total_categories = db.categories.count_documents({})
    
    recent_enquiries = list(db.enquiries.find().sort("createdAt", -1).limit(5))
    formatted_enquiries = []
    for enq in recent_enquiries:
        created_at = enq.get("createdAt")
        if isinstance(created_at, datetime):
            date_str = created_at.strftime("%Y-%m-%d")
        elif isinstance(created_at, str):
            # Try to parse ISO format if it's a string, or just use it
            date_str = created_at[:10]
        else:
            date_str = "Unknown"

        formatted_enquiries.append({
            "id": str(enq["_id"]),
            "clientName": enq.get("fullName", "Unknown"),
            "company": enq.get("company", ""),
            "subject": enq.get("inquiryType", "Enquiry"),
            "status": enq.get("status", "New").lower(),
            "priority": "medium",
            "date": date_str
        })

    # mock activities for now
    activities = [
        {"id": 1, "user": "System", "action": "Database", "target": "backup completed", "timestamp": "1 hour ago"},
        {"id": 2, "user": "System", "action": "Server", "target": "health check passed", "timestamp": "2 hours ago"}
    ]
        
    return {
        "stats": {
            "totalProducts": total_products,
            "totalEnquiries": total_enquiries,
            "totalClients": total_clients,
            "totalCategories": total_categories,
            "revenueGrowth": "LIVE"
        },
        "recentEnquiries": formatted_enquiries,
        "recentActivities": activities
    }
