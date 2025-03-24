import mongomock
import pytest
from fastapi import HTTPException
from pymongo.errors import PyMongoError
from pydantic import ValidationError

from backend.models.user.folder_entry import FolderEntry
from backend.repositories.folder_entry_repository import FolderEntryRepository

def dummy_folder_entry():
    return FolderEntry(name="Test Entry")

def test_init_valid_db():
    """Should initialize the repository successfully with a valid database instance."""
    db = mongomock.MongoClient().db
    repo = FolderEntryRepository(db)
    assert repo.collection is not None
    assert repo.collection.name == "entries"  # Fixed: Check collection.name, not db_entry.name
    assert repo.collection.database is db

def test_init_invalid_db():
    """Should raise an HTTPException with status 500 when initialized with an invalid database instance."""
    with pytest.raises(HTTPException) as exc_info:
        FolderEntryRepository("not a database")
    assert exc_info.value.status_code == 500
    assert "Invalid database instance provided" in exc_info.value.detail

def test_create_entry_success():
    """Should create a FolderEntry successfully and return it with an assigned ID."""
    db = mongomock.MongoClient().db
    repo = FolderEntryRepository(db)
    
    entry = dummy_folder_entry()
    created_entry = repo.create_folder_entry(entry)
    
    assert created_entry.id is not None
    assert isinstance(created_entry, FolderEntry)
    assert created_entry.name == entry.name 
    
def test_create_entry_database_error(monkeypatch):
    """Should raise an HTTPException with status 500 when a database error occurs during entry creation."""
    db = mongomock.MongoClient().db
    repo = FolderEntryRepository(db)
    
    entry = dummy_folder_entry()
    
    def fake_insert_one(document):
        raise PyMongoError("Fake DB error")
    
    monkeypatch.setattr(repo.collection, "insert_one", fake_insert_one)
    
    with pytest.raises(HTTPException) as exc_info:
        repo.create_folder_entry(entry)
    assert exc_info.value.status_code == 500
    assert "Database error" in exc_info.value.detail

def test_create_entry_invalid_data(monkeypatch):
    """Should raise an HTTPException with status 400 when the FolderEntry data is invalid."""
    db = mongomock.MongoClient().db
    repo = FolderEntryRepository(db)
    
    entry = dummy_folder_entry()
    
    def fake_model_dump(self):
        return {"name": None} 
    
    monkeypatch.setattr(FolderEntry, "model_dump", fake_model_dump)
    
    with pytest.raises(HTTPException) as exc_info:
        repo.create_folder_entry(entry)
    assert exc_info.value.status_code == 400