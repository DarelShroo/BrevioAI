import pytest

from core.brevio.enums.summary_level import SummaryLevel
from core.shared.utils.summary_quality import (
    QualitySignals,
    evaluate_artifact,
    ArtifactVerdict,
)

def test_evaluate_large_document_section_assembly():
    """
    Test Caso 4 & 6: Documento grande/gigante finalizado en múltiples partes (section_assembly=True).
    El target final es 12000, max_tokens por llamada (hard limit) es 8192.
    El artifact final ensamblado tiene 11500 tokens.
    Debería pasar y no fallar por `below_output_min` con un límite artificial de 8192.
    """
    signals = QualitySignals(
        source_tokens=350_000,
        source_words=250_000,
        map_tokens=50_000,
        map_words=35_000,
        final_tokens=11_500,
        final_words=8_000,
        output_min_tokens=10_000,
        output_target_tokens=12_000,
        output_hard_limit=8192,
        summary_level=SummaryLevel.MODERATE,
        route="hierarchical",
        section_assembly=True,
    )
    report = evaluate_artifact("text " * 8500, signals)
    assert report.verdict == ArtifactVerdict.VALID
    assert "below_output_min" not in str(report.reasons)

def test_evaluate_map_collapse_on_large_document():
    """
    Test Caso 5: Output colapsado de forma irrecuperable.
    """
    signals = QualitySignals(
        source_tokens=350_000,
        source_words=250_000,
        map_tokens=50_000,
        map_words=35_000,
        final_tokens=500,
        final_words=300,
        output_min_tokens=10_000,
        output_target_tokens=12_000,
        output_hard_limit=8192,
        summary_level=SummaryLevel.MODERATE,
        route="hierarchical",
        section_assembly=True,
    )
    report = evaluate_artifact("text", signals)
    assert report.verdict == ArtifactVerdict.INVALID
    assert any("map_collapse" in r for r in report.reasons) or any("source_collapse" in r for r in report.reasons) or any("below_output_min" in r for r in report.reasons)

def test_evaluate_source_collapse_with_absolute_ceiling():
    """
    Test Caso 3: Documento gigante (500k) no debe exigir un porcentaje lineal absurdo.
    Si el floor_ratio es 0.035, el lineal requeriría 17500 words.
    Pero como configuramos MAX_REQUIRED_SOURCE_WORDS = 5000,
    un output de 6000 words debería ser suficiente para no disparar source_collapse.
    """
    signals = QualitySignals(
        source_tokens=700_000,
        source_words=500_000,
        map_tokens=70_000,
        map_words=50_000,
        final_tokens=8_500,
        final_words=6_000,
        output_min_tokens=7_000,
        output_target_tokens=9_000,
        output_hard_limit=8192,
        summary_level=SummaryLevel.MODERATE,
        route="hierarchical",
        section_assembly=True,
    )
    report = evaluate_artifact("text " * 6500, signals)
    assert not any("source_collapse" in r for r in report.reasons)
