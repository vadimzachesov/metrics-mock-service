from fastapi import APIRouter, Response
from services.business import BusinessService

router = APIRouter(prefix="/api/v1", tags=["Business API"])

@router.get("/orders")
async def get_orders(response: Response):
    """Эндпоинт чтения бизнес-данных (заказы)."""
    status_code, payload = await BusinessService.process_orders()
    response.status_code = status_code
    return payload

@router.post("/payment")
async def process_payment(response: Response):
    """Эндпоинт транзакций (платежи)."""
    status_code, payload = await BusinessService.process_payment()
    response.status_code = status_code
    return payload

