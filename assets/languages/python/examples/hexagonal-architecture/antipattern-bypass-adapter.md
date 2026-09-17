```python
# ❌ Route handler hits the database directly
@app.get("/users/active")
async def list_active_users() -> JSONResponse:
    rows = await db.execute(select(users).where(users.c.active.is_(True)))
    ...


# ✅ Route handler calls a use case, which goes through a port
@app.get("/users/active")
async def list_active_users() -> JSONResponse:
    result = await get_active_users(user_repo)
    ...
```
