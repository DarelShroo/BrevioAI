import pytest

from core.brevio.services.summary_service import SummaryService


@pytest.fixture
def summary_service():
    # Instantiate with None dependencies since we are only testing pure python methods
    service = SummaryService()
    return service


def test_validate_global_structure_detects_multiple_intros(summary_service):
    text = """# Introducción
Este es el inicio.

## 1. Desarrollo
Algo de texto.

# Introducción
Otra introducción."""
    is_valid, errors = summary_service._validate_global_structure(text)
    assert not is_valid
    assert any("Múltiples introducciones detectadas" in e for e in errors)


def test_validate_global_structure_detects_numbering_restarts(summary_service):
    text = """# Resumen

## 1. Introducción
Texto.

## 2. Desarrollo
Texto.

## 1. Más cosas
Texto."""
    is_valid, errors = summary_service._validate_global_structure(text)
    assert not is_valid
    assert any("Reinicio de numeración anómalo detectado" in e for e in errors)


def test_sanitize_structure_fixes_anomalies(summary_service):
    text = """# 1. Introducción
Texto inicial.

## 1. Primer punto
Algo de texto.

## 2. Segundo punto
Más texto.

# 1. Introducción
Texto introductorio duplicado.

## 1. Tercer punto mal numerado
Texto extra.

# Conclusión
Primera conclusión.

# Conclusión
Segunda conclusión."""

    sanitized = summary_service._sanitize_structure(text)

    # 1. Duplicate intro should be removed
    assert sanitized.count("Introducción") == 1

    # 2. Numbering should be fixed (1, 2, 3)
    assert "## 1. Primer punto" in sanitized
    assert "## 2. Segundo punto" in sanitized
    assert "## 3. Tercer punto mal numerado" in sanitized

    # 3. Duplicate conclusions should be renamed or removed
    # In our logic we rename to "Puntos Finales"
    assert "Puntos Finales" in sanitized
    assert sanitized.count("Conclusión") == 1


def test_sanitize_drops_cloned_heading_sections(summary_service):
    text = (
        "### Execution of JavaScript\n"
        "First copy with Notepad++.\n\n"
        "### Execution of JavaScript\n"
        "First copy with Notepad++.\n\n"
        "### Execution of JavaScript\n"
        "First copy with Notepad++.\n"
    )
    sanitized = summary_service._sanitize_structure(text)
    assert sanitized.count("### Execution of JavaScript") == 1
    assert sanitized.count("Notepad++") == 1


def test_prose_language_mismatch_detects_english_when_spanish_requested(
    summary_service,
):
    english = (
        "The document is organized into units, with the execution of JavaScript "
        "in the browser and the integration of scripts for the user. "
        "This section is written in English and is intended for that language."
    )
    spanish = (
        "El documento se organiza en unidades y explica la ejecución de JavaScript "
        "en el navegador y la integración de scripts para el usuario."
    )
    from core.brevio.enums.language import LanguageType

    assert summary_service._prose_language_mismatch(english, LanguageType.SPANISH)
    assert not summary_service._prose_language_mismatch(spanish, LanguageType.SPANISH)
    assert not summary_service._prose_language_mismatch(english, LanguageType.ENGLISH)


def test_sanitize_structure_validates_cleanly_afterwards(summary_service):
    text = """## 1. Introducción
A

## 1. B
B

## 1. C
C"""
    sanitized = summary_service._sanitize_structure(text)
    is_valid, errors = summary_service._validate_global_structure(sanitized)
    assert is_valid, f"Errors: {errors}"
