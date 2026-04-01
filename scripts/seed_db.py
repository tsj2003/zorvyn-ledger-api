"""
Seed script — generates demo users and financial records.
Run: python -m scripts.seed_db
"""
import asyncio
import random
from datetime import date, timedelta, timezone, datetime
from decimal import Decimal
from app.database import engine, async_session_factory
from app.models import Base, User, FinancialRecord, UserRole, RecordType
from app.security import hash_password
from sqlalchemy import select

SEED_USERS = [
    {"email": "admin@zorvyn.local", "username": "admin", "password": "password123", "role": UserRole.ADMIN},
    {"email": "analyst@zorvyn.local", "username": "analyst", "password": "password123", "role": UserRole.ANALYST},
    {"email": "viewer@zorvyn.local", "username": "viewer", "password": "password123", "role": UserRole.VIEWER},
]

INCOME_CATEGORIES = ["salary", "consulting", "freelance", "investments", "refunds"]
EXPENSE_CATEGORIES = ["rent", "utilities", "groceries", "software", "marketing", "travel", "equipment", "office_supplies"]

RECORD_COUNT = 150


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # skip if already seeded
        existing = await session.execute(select(User).where(User.email == "admin@zorvyn.local"))
        if existing.scalar_one_or_none():
            print("\n⚠ Database already seeded — skipping.\n")
            return

        user_ids = []
        print("\n" + "=" * 55)
        print("  SEED USERS — USE THESE CREDENTIALS TO LOG IN")
        print("=" * 55)

        for spec in SEED_USERS:
            user = User(
                email=spec["email"],
                username=spec["username"],
                hashed_password=hash_password(spec["password"]),
                role=spec["role"],
            )
            session.add(user)
            await session.flush()
            user_ids.append(user.id)
            print(f"  {spec['role'].value:>8}  |  {spec['email']:<24}  |  pw: {spec['password']}")

        print("=" * 55 + "\n")

        admin_id = user_ids[0]
        today = date.today()

        for i in range(RECORD_COUNT):
            is_income = random.random() < 0.4
            rec_type = RecordType.INCOME if is_income else RecordType.EXPENSE
            cats = INCOME_CATEGORIES if is_income else EXPENSE_CATEGORIES

            amount = Decimal(str(round(random.uniform(50, 15000), 2)))
            rec_date = today - timedelta(days=random.randint(0, 180))

            record = FinancialRecord(
                amount=amount,
                record_type=rec_type,
                category=random.choice(cats),
                description=f"Auto-generated seed record #{i+1}",
                record_date=rec_date,
                created_by=admin_id,
            )
            session.add(record)

        await session.commit()
        print(f"✓ Seeded {RECORD_COUNT} financial records across the last 6 months.\n")


def main():
    asyncio.run(seed())


if __name__ == "__main__":
    main()
