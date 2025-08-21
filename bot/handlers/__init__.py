"""
This package contains all the bot's handlers.
The routers from each module are collected here and included in a single main router.
"""

from aiogram import Router

from . import admin, balance, billing, buy_number, history, search, start

# The main router for the entire application.
# We will include all other routers into this one.
all_routers = Router()

all_routers.include_router(start.router)
all_routers.include_router(admin.router)
all_routers.include_router(balance.router)
all_routers.include_router(billing.router)
all_routers.include_router(buy_number.router)
all_routers.include_router(history.router)
all_routers.include_router(search.router)
