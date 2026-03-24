from fastapi import APIRouter
from schemas.payload import ExecuteRequest
from services.compiler import compile_and_run_project 

router = APIRouter()

@router.post("/execute")
async def execute_endpoint(request: ExecuteRequest):
    return compile_and_run_project(request.archivos)