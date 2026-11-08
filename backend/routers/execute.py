from fastapi import APIRouter, Request
from schemas.payload import ExecuteRequest
from services.compiler import compile_and_run_project
from services.rate_limit import limiter, EXECUTE_LIMIT

router = APIRouter()

@router.post("/execute")
@limiter.limit(EXECUTE_LIMIT)
async def execute_endpoint(request: Request, body: ExecuteRequest):
    return await compile_and_run_project(body.archivos)
