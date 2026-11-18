from sqlalchemy import inspect
from database.database import engine

inspector = inspect(engine)

for table_name in ["tickets", "companies", "knowledge_base_files", "knowledge_base_records"]:
    print(f"\n===== {table_name.upper()} =====")

    if not inspector.has_table(table_name):
        print("Table does not exist")
        continue

    for column in inspector.get_columns(table_name):
        print(
            column["name"],
            "| type:", column["type"],
            "| nullable:", column["nullable"],
            "| default:", column["default"]
        )

    print("Foreign keys:", inspector.get_foreign_keys(table_name))
    print("Unique constraints:", inspector.get_unique_constraints(table_name))
