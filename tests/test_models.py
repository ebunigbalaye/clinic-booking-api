import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import models
from app.database import Base
from app.models import *

print("Registered tables:")
for table_name in Base.metadata.tables:
    print(table_name)

print("\nSlot columns:")
for column in models.Slot.__table__.columns:
    print(column.name, column.type)

print("\nBooking columns:")
for column in models.Booking.__table__.columns:
    print(column.name, column.type)
