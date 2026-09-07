from fastapi import APIRouter, Depends, HTTPException, status
from app.api.auth import get_current_user, User
from app.core.supabase import supabase

router = APIRouter()

@router.get("/report/{id}")
async def get_report(id: str, current_user: User = Depends(get_current_user)):
    # 1. Fetch inspection
    inspection_res = supabase.table("inspections").select("*").eq("id", id).execute()
    if not inspection_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
        
    inspection = inspection_res.data[0]
    
    # 2. Fetch declarations
    decl_res = supabase.table("declarations").select("*").eq("inspection_id", id).execute()
    declarations = decl_res.data[0] if decl_res.data else {}
    
    # 3. Fetch violations
    viol_res = supabase.table("violations").select("*").eq("inspection_id", id).execute()
    violations = viol_res.data
    
    # 4. Fetch reports (PDF/DOCX urls if they exist)
    rep_res = supabase.table("reports").select("*").eq("inspection_id", id).execute()
    report_files = rep_res.data[0] if rep_res.data else {}
    
    return {
        "inspection": inspection,
        "declarations": declarations,
        "violations": violations,
        "report_files": report_files
    }
