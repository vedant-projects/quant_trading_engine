"""Versioned read-only API router."""

from fastapi import APIRouter

from app.api.orders import router as orders_router
from app.api.portfolio import router as portfolio_router
from app.api.signals import router as signals_router
from app.api.strategies import router as strategies_router
from app.api.trades import router as trades_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(strategies_router)
api_router.include_router(signals_router)
api_router.include_router(orders_router)
api_router.include_router(trades_router)
api_router.include_router(portfolio_router)
