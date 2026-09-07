from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from app.api.auth import get_current_user, User
from app.core.supabase import supabase
import uuid
import time

router = APIRouter()

@router.post("/scan")
async def scan_product(
    image: UploadFile = File(...),
    product_name: str = Form("Unknown Product"),
    location: str = Form(""),
    current_user: User = Depends(get_current_user)
):
    try:
        # Validate image size (e.g., 5MB limit)
        contents = await image.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image too large")

        # 1. Upload image to Supabase Storage
        file_ext = image.filename.split(".")[-1] if image.filename else "jpg"
        file_name = f"{current_user.id}/{uuid.uuid4()}.{file_ext}"
        
        # Upload using Supabase client
        storage_res = supabase.storage.from_("inspections").upload(
            file_name,
            contents,
            {"content-type": image.content_type}
        )
        
        # Get public URL
        image_url = supabase.storage.from_("inspections").get_public_url(file_name)

        # 2. Create Inspection Record
        inspection_data = {
            "inspector_id": current_user.id,
            "product_name": product_name,
            "location": location,
            "status": "review", # Default until OCR/Rules are applied in future phases
            "image_path": image_url
        }
        
        insert_res = supabase.table("inspections").insert(inspection_data).execute()
        inspection = insert_res.data[0]
        
        # In a real implementation, we would now trigger OCR and Rule Engine.
        # For Phase 3, we just return the created inspection.
        
        return {
            "message": "Scan uploaded successfully",
            "inspection": inspection
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process scan: {str(e)}")
