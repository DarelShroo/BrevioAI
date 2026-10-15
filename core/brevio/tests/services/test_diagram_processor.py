import os
import shutil
import pytest
from unittest.mock import AsyncMock, patch
from core.brevio.services.diagram_processor import DiagramProcessor, DiagramBlock

@pytest.fixture
def processor():
    return DiagramProcessor()

@pytest.fixture
def temp_dir(tmp_path):
    d = tmp_path / "summary_output"
    d.mkdir()
    return str(d)

@pytest.mark.asyncio
async def test_no_diagrams(processor, temp_dir):
    markdown = "# Title\n\nSome text."
    result, blocks = await processor.process(markdown, temp_dir)
    assert result == markdown
    assert len(blocks) == 0

@pytest.mark.asyncio
async def test_normal_code_blocks_ignored(processor, temp_dir):
    markdown = "# Title\n\n```python\nprint('hello')\n```\n"
    result, blocks = await processor.process(markdown, temp_dir)
    assert result == markdown
    assert len(blocks) == 0

@pytest.mark.asyncio
async def test_detects_mermaid(processor, temp_dir):
    markdown = "Text\n```mermaid\nflowchart TD\n  A --> B\n```\nMore text"
    
    async def mock_render(block, d_dir):
        block.success = True
        block.svg_path = os.path.join(d_dir, f"diagram-{block.index:03d}.svg")
        
    with patch.object(processor, '_render_diagram', new=AsyncMock(side_effect=mock_render)):
        result, blocks = await processor.process(markdown, temp_dir)
        
    assert len(blocks) == 1
    assert blocks[0].source == "flowchart TD\n  A --> B"
    assert "![Diagrama](diagrams/diagram-001.svg)" in result
    assert "```mermaid" not in result

@pytest.mark.asyncio
async def test_multiple_diagrams(processor, temp_dir):
    markdown = (
        "Text1\n"
        "```mermaid\nA\n```\n"
        "Text2\n"
        "```Mermaid\nB\n```\n"
    )
    
    async def mock_render(block, d_dir):
        block.success = True
        block.svg_path = os.path.join(d_dir, f"diagram-{block.index:03d}.svg")
        
    with patch.object(processor, '_render_diagram', new=AsyncMock(side_effect=mock_render)):
        result, blocks = await processor.process(markdown, temp_dir)
        
    assert len(blocks) == 2
    assert blocks[0].source == "A"
    assert blocks[1].source == "B"
    assert "![Diagrama](diagrams/diagram-001.svg)" in result
    assert "![Diagrama](diagrams/diagram-002.svg)" in result

@pytest.mark.asyncio
async def test_failed_diagram_not_replaced(processor, temp_dir):
    markdown = "Text\n```mermaid\nINVALID\n```\nMore text"
    
    async def mock_render(block, d_dir):
        block.success = False
        block.error = "Syntax error"
        
    with patch.object(processor, '_render_diagram', new=AsyncMock(side_effect=mock_render)):
        result, blocks = await processor.process(markdown, temp_dir)
        
    assert len(blocks) == 1
    assert not blocks[0].success
    assert result == markdown  # Not replaced
    assert "```mermaid" in result

@pytest.mark.asyncio
async def test_integration_mmdc(processor, temp_dir):
    """Real integration test with mmdc if installed."""
    if not shutil.which("mmdc"):
        pytest.skip("mmdc is not installed in the current environment")
        
    markdown = "```mermaid\ngraph TD\nA-->B\n```"
    result, blocks = await processor.process(markdown, temp_dir)
    
    assert len(blocks) == 1
    assert blocks[0].success
    assert "![Diagrama](diagrams/diagram-001.svg)" in result
    
    # Verify file was actually created
    svg_file = os.path.join(temp_dir, "diagrams", "diagram-001.svg")
    assert os.path.exists(svg_file)
    assert os.path.getsize(svg_file) > 0


@pytest.mark.asyncio
async def test_integration_mmdc_html_format(processor, temp_dir):
    """Real integration test with mmdc producing inline HTML base64 format."""
    if not shutil.which("mmdc"):
        pytest.skip("mmdc is not installed in the current environment")

    markdown = "```mermaid\ngraph TD\nA-->B\n```"
    result, blocks = await processor.process(markdown, temp_dir, output_format="html")

    assert len(blocks) == 1
    assert blocks[0].success
    assert '<img src="data:image/svg+xml;base64,' in result
    assert 'alt="Diagrama" class="md-img" />' in result

