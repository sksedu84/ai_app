from fastapi import APIRouter
from fastapi.responses import JSONResponse
from common import constants

router = APIRouter(tags=["Health"])

class HealthEndpoint:
    def __init__(self):
        pass

    @staticmethod
    async def get() -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={
                "status": constants.OK,
                "service": constants.APP_NAME,
            },
        )


router.add_api_route("/", HealthEndpoint.get, methods=["GET"], response_class=JSONResponse, include_in_schema=False)
router.add_api_route("/health", HealthEndpoint.get, methods=["GET"], response_class=JSONResponse, include_in_schema=False)
