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
    """
    Test para verificar que la inicialización con una instancia válida de Database funcione.
    """
    db = mongomock.MongoClient().db
    repo = FolderEntryRepository(db)
    assert repo.collection is not None
    assert repo.collection.name == "entries"  # Fixed: Check collection.name, not db_entry.name
    assert repo.collection.database is db

def test_init_invalid_db():
    """
    Test para verificar que se lance una excepción HTTPException si se pasa una instancia inválida.
    """
    with pytest.raises(HTTPException) as exc_info:
        FolderEntryRepository("not a database")
    assert exc_info.value.status_code == 500
    assert "Invalid database instance provided" in exc_info.value.detail

def test_create_entry_success():
    """
    Test para verificar que se crea correctamente una FolderEntry.
    """
    db = mongomock.MongoClient().db
    repo = FolderEntryRepository(db)
    
    entry = dummy_folder_entry()
    created_entry = repo.create_entry(entry)
    
    assert created_entry.id is not None
    assert isinstance(created_entry, FolderEntry)
    assert created_entry.name == entry.name 
    
def test_create_entry_database_error(monkeypatch):
    """
    Test para simular un error de la base de datos (PyMongoError) al insertar el documento.
    """
    db = mongomock.MongoClient().db
    repo = FolderEntryRepository(db)
    
    entry = dummy_folder_entry()
    
    def fake_insert_one(document):
        raise PyMongoError("Fake DB error")
    
    monkeypatch.setattr(repo.collection, "insert_one", fake_insert_one)
    
    with pytest.raises(HTTPException) as exc_info:
        repo.create_entry(entry)
    assert exc_info.value.status_code == 500
    assert "Database error" in exc_info.value.detail

"""def test_create_entry_invalid_data(monkeypatch):
    db = mongomock.MongoClient().db
    repo = FolderEntryRepository(db)
    
    entry = dummy_folder_entry()
    
    def fake_model_dump(self):
        from pydantic import ValidationError
        from pydantic_core import ErrorDetails
        
        # Definir una lista de errores válida para Pydantic 2.x
        errors = [
            ErrorDetails(
                type='value_error',
                loc=('name',),
                msg='Fake validation error',
                input=None,
                ctx=None
            )
        ]
        # Crear el ValidationError correctamente con la lista de errores y el modelo
        raise ValidationError(errors, FolderEntry)
    
    # Aplicar el monkeypatch al método model_dump de FolderEntry
    monkeypatch.setattr(FolderEntry, "model_dump", fake_model_dump)
    
    # Esperar un HTTPException con código de estado 400
    with pytest.raises(HTTPException) as exc_info:
        repo.create_entry(entry)
    assert exc_info.value.status_code == 400
    assert "Invalid FolderEntry data" in exc_info.value.detail"""