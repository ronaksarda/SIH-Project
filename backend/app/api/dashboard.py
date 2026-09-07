from fastapi import APIRouter, Depends
from app.api.auth import get_current_user, User
from app.core.supabase import supabase

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard(current_user: User = Depends(get_current_user)):
    # Basic aggregates
    # Note: For production, consider using a DB view or RPC for complex aggregates.
    
    # Let's get total inspections based on user role (RLS handles this partially, but we can do a simple select)
    query = supabase.table("inspections").select("id, status", count="exact")
    
    if current_user.role == "inspector":
        query = query.eq("inspector_id", current_user.id)
        
    res = query.execute()
    total = res.count if res.count is not None else 0
    data = res.data or []
    
    compliant_count = sum(1 for i in data if i.get("status") == "pass")
    non_compliant_count = sum(1 for i in data if i.get("status") == "fail")
    review_count = sum(1 for i in data if i.get("status") == "review")

    # Get recent inspections
    recent_query = supabase.table("inspections").select("id, product_name, status, inspection_timestamp").order("inspection_timestamp", desc=True).limit(5)
    if current_user.role == "inspector":
        recent_query = recent_query.eq("inspector_id", current_user.id)
        
    recent_res = recent_query.execute()
    
    return {
        "stats": {
            "total_inspections": total,
            "compliant_count": compliant_count,
            "non_compliant_count": non_compliant_count,
            "review_count": review_count
        },
        "recent_inspections": recent_res.data or []
    }
