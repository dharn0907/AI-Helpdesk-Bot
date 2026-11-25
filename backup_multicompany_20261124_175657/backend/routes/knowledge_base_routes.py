
import uuid
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import (
    Company,
    KnowledgeBaseFile,
    KnowledgeBaseRecord,
)


router = APIRouter(
    prefix="/knowledge-base",
    tags=["Company Knowledge Base"],
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "company_knowledge"
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}


def get_active_company(db):
    company = (
        db.query(Company)
        .filter(Company.is_active.is_(True))
        .first()
    )

    if not company:
        raise HTTPException(status_code=404, detail="No active company found.")

    return company


def read_spreadsheet(file_path, extension):
    try:
        if extension == ".csv":
            dataframe = pd.read_csv(
                file_path,
                dtype=str,
                keep_default_na=False,
            )
        else:
            dataframe = pd.read_excel(
                file_path,
                dtype=str,
                keep_default_na=False,
                engine="openpyxl",
            )

        if dataframe.empty:
            raise HTTPException(
                status_code=400,
                detail="The uploaded spreadsheet contains no records.",
            )

        dataframe.columns = [
            str(column).strip() for column in dataframe.columns
        ]

        if any(not column for column in dataframe.columns):
            raise HTTPException(
                status_code=400,
                detail="Every column must have a column name.",
            )

        if len(set(dataframe.columns)) != len(dataframe.columns):
            raise HTTPException(
                status_code=400,
                detail="Duplicate column names are not allowed.",
            )

        records = dataframe.to_dict(orient="records")

        cleaned_records = []

        for record in records:
            cleaned = {
                str(key): str(value).strip() if value is not None else ""
                for key, value in record.items()
            }

            if any(value for value in cleaned.values()):
                cleaned_records.append(cleaned)

        if not cleaned_records:
            raise HTTPException(
                status_code=400,
                detail="No usable records were found.",
            )

        return cleaned_records

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to read spreadsheet: {str(exc)}",
        )


@router.post("/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    original_name = Path(file.filename or "").name
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only CSV and XLSX files are supported currently.",
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="The file is empty.")

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Maximum upload size is 10 MB.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid.uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / stored_filename

    file_path.write_bytes(contents)

    try:
        records = read_spreadsheet(file_path, extension)
        company = get_active_company(db)

        knowledge_file = KnowledgeBaseFile(
            company_id=company.id,
            original_filename=original_name,
            stored_filename=stored_filename,
            file_type=extension.lstrip("."),
            row_count=len(records),
            status="processed",
        )

        db.add(knowledge_file)
        db.flush()

        knowledge_records = []

        for record in records:
            search_text = " ".join(
                f"{key}: {value}"
                for key, value in record.items()
                if value
            )

            knowledge_records.append(
                KnowledgeBaseRecord(
                    company_id=company.id,
                    file_id=knowledge_file.id,
                    record_data=record,
                    search_text=search_text,
                )
            )

        db.add_all(knowledge_records)
        db.commit()
        db.refresh(knowledge_file)

        return {
            "message": "Knowledge Base file uploaded successfully.",
            "file_id": knowledge_file.id,
            "filename": original_name,
            "records_saved": len(knowledge_records),
            "status": knowledge_file.status,
        }

    except Exception:
        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise

    finally:
        await file.close()


@router.get("/files")
def list_knowledge_files(
    db: Session = Depends(get_db),
):
    company = get_active_company(db)

    files = (
        db.query(KnowledgeBaseFile)
        .filter(KnowledgeBaseFile.company_id == company.id)
        .order_by(KnowledgeBaseFile.created_at.desc())
        .all()
    )

    return {
        "files": [
            {
                "id": item.id,
                "filename": item.original_filename,
                "file_type": item.file_type,
                "row_count": item.row_count,
                "status": item.status,
                "created_at": (
                    item.created_at.isoformat()
                    if item.created_at else None
                ),
            }
            for item in files
        ]
    }


@router.delete("/files/{file_id}")
def delete_knowledge_file(
    file_id: int,
    db: Session = Depends(get_db),
):
    company = get_active_company(db)

    item = (
        db.query(KnowledgeBaseFile)
        .filter(
            KnowledgeBaseFile.id == file_id,
            KnowledgeBaseFile.company_id == company.id,
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="File not found.")

    file_path = UPLOAD_DIR / item.stored_filename

    try:
        db.query(KnowledgeBaseRecord).filter(
            KnowledgeBaseRecord.file_id == item.id,
            KnowledgeBaseRecord.company_id == company.id,
        ).delete(synchronize_session=False)

        db.delete(item)
        db.commit()

        if file_path.exists():
            file_path.unlink()

        return {"message": "Knowledge Base file and its records deleted."}

    except Exception:
        db.rollback()
        raise
