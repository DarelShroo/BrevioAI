import asyncio
import logging
import os
import re
import json
import base64
from dataclasses import dataclass
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

@dataclass
class DiagramBlock:
    diagram_type: str
    source: str
    index: int
    mmd_path: Optional[str] = None
    svg_path: Optional[str] = None
    error: Optional[str] = None
    success: bool = False

class DiagramProcessor:
    """Detects and renders Mermaid diagrams from markdown into SVGs."""
    
    def __init__(self, mmdc_executable: str = "mmdc", timeout_seconds: int = 60):
        self.mmdc_executable = mmdc_executable
        self.timeout_seconds = timeout_seconds
        self.puppeteer_config_path = "/tmp/puppeteer-config.json"
        self.mermaid_config_path = "/tmp/mermaid-config.json"
        self._ensure_puppeteer_config()
        self._ensure_mermaid_config()
        # Match ```mermaid or ```Mermaid
        self.regex = re.compile(r"```[mM]ermaid\s*\n([\s\S]*?)\n```")

    def _ensure_puppeteer_config(self) -> None:
        """Create a puppeteer config to disable sandbox, required in many Docker environments."""
        if not os.path.exists(self.puppeteer_config_path):
            try:
                with open(self.puppeteer_config_path, "w") as f:
                    json.dump({"args": ["--no-sandbox"]}, f)
            except Exception as e:
                logger.error(f"Failed to write puppeteer config: {e}")

    def _ensure_mermaid_config(self) -> None:
        """Create a mermaid config to disable htmlLabels, required for PDF export."""
        if not os.path.exists(self.mermaid_config_path):
            try:
                # Force htmlLabels to false globally and for specific diagram types
                # to prevent <foreignObject> tags which WeasyPrint ignores.
                config = {
                    "htmlLabels": False,
                    "flowchart": {"htmlLabels": False},
                    "sequence": {"htmlLabels": False},
                    "state": {"htmlLabels": False},
                    "class": {"htmlLabels": False},
                    "journey": {"htmlLabels": False},
                    "gantt": {"htmlLabels": False},
                    "pie": {"htmlLabels": False},
                    "er": {"htmlLabels": False}
                }
                with open(self.mermaid_config_path, "w") as f:
                    json.dump(config, f)
            except Exception as e:
                logger.error(f"Failed to write mermaid config: {e}")

    async def _render_diagram(self, block: DiagramBlock, diagrams_dir: str) -> None:
        """Render a single Mermaid diagram block into an SVG."""
        base_name = f"diagram-{block.index:03d}"
        block.mmd_path = os.path.join(diagrams_dir, f"{base_name}.mmd")
        block.svg_path = os.path.join(diagrams_dir, f"{base_name}.svg")
        
        try:
            # Save the mermaid source
            with open(block.mmd_path, "w", encoding="utf-8") as f:
                f.write(block.source)
                
            cmd = [
                self.mmdc_executable,
                "-i", block.mmd_path,
                "-o", block.svg_path,
                "-b", "transparent",
                "-p", self.puppeteer_config_path,
                "-c", self.mermaid_config_path
            ]
            
            # Execute mmdc
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout_seconds)
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                raise TimeoutError(f"Diagram rendering timed out after {self.timeout_seconds} seconds")
                
            if process.returncode != 0:
                error_msg = stderr.decode().strip() or stdout.decode().strip()
                raise RuntimeError(f"mmdc failed with code {process.returncode}: {error_msg}")
                
            # Verify the SVG was actually created
            if not os.path.exists(block.svg_path):
                raise FileNotFoundError(f"SVG file was not created at {block.svg_path}")
                
            # Post-process the SVG to enforce absolute pixel dimensions and prevent web stretching/PDF clipping
            try:
                with open(block.svg_path, "r", encoding="utf-8") as f:
                    svg_content = f.read()
                
                # Extract viewBox dimensions
                match = re.search(r'viewBox="[\d\.\s-]+\s+[\d\.\s-]+\s+([\d\.]+)\s+([\d\.]+)"', svg_content)
                if match:
                    w = match.group(1)
                    h = match.group(2)
                    
                    # Remove existing width and height to avoid duplicates
                    svg_content = re.sub(r'\s+width="[^"]+"', '', svg_content)
                    svg_content = re.sub(r'\s+height="[^"]+"', '', svg_content)
                    
                    # Inject exact dimensions from viewBox
                    svg_content = svg_content.replace('<svg ', f'<svg width="{w}" height="{h}" ')
                    
                    with open(block.svg_path, "w", encoding="utf-8") as f:
                        f.write(svg_content)
            except Exception as e:
                logger.warning(f"[DIAGRAM] Failed to post-process SVG dimensions for block {block.index}: {e}")
                
            block.success = True
            logger.info(f"[DIAGRAM] Rendered diagram #{block.index} -> {os.path.basename(block.svg_path)}")
            
        except Exception as e:
            block.success = False
            block.error = str(e)
            logger.error(f"[DIAGRAM] Failed rendering diagram #{block.index}: {e}")

    async def process(
        self,
        markdown: str,
        output_directory: str,
        *,
        output_format: str = "markdown",
    ) -> Tuple[str, List[DiagramBlock]]:
        """
        Process the markdown, detect mermaid blocks, render them, and substitute the markdown blocks.
        
        Args:
            markdown: The original markdown text.
            output_directory: The directory where the summary.md is located. Artifacts will be saved in a 'diagrams' subdirectory.
            output_format: Format for image replacement: 'markdown' (default, e.g. ![Diagrama](diagrams/diagram-001.svg))
                           or 'html' (e.g. <img src="data:image/svg+xml;base64,..." alt="Diagrama" class="md-img" />).
            
        Returns:
            Tuple containing the processed markdown and the list of processed diagram blocks.
        """
        if not markdown or not isinstance(markdown, str):
            return markdown, []
            
        # Detect all mermaid blocks
        matches = list(self.regex.finditer(markdown))
        if not matches:
            return markdown, []
            
        logger.info(f"[DIAGRAM] Detected {len(matches)} Mermaid diagram(s)")
        
        diagrams_dir = os.path.join(output_directory, "diagrams")
        os.makedirs(diagrams_dir, exist_ok=True)
        
        blocks = []
        for i, match in enumerate(matches, start=1):
            source = match.group(1).strip()
            blocks.append(DiagramBlock(
                diagram_type="mermaid",
                source=source,
                index=i
            ))
            
        # Render diagrams concurrently (limited to 5 to avoid overwhelming the system)
        semaphore = asyncio.Semaphore(5)
        
        async def render_with_semaphore(block: DiagramBlock):
            async with semaphore:
                await self._render_diagram(block, diagrams_dir)
                
        await asyncio.gather(*(render_with_semaphore(block) for block in blocks))
        
        # Replace successfully rendered diagrams in the markdown
        # We do this backwards to avoid breaking string offsets
        result_markdown = markdown
        for match, block in reversed(list(zip(matches, blocks))):
            if block.success and block.svg_path:
                start, end = match.span()
                img_src_rel = f"diagrams/{os.path.basename(block.svg_path)}"
                if output_format == "html":
                    try:
                        with open(block.svg_path, "rb") as f:
                            svg_b64 = base64.b64encode(f.read()).decode("utf-8").replace('\n', '').replace('\r', '')
                        img_src = f"data:image/svg+xml;base64,{svg_b64}"
                        replacement = f'<img src="{img_src}" alt="Diagrama" class="md-img" />'
                    except Exception as e:
                        logger.error(f"[DIAGRAM] Failed to encode SVG as base64 for block {block.index}: {e}")
                        replacement = f"![Diagrama]({img_src_rel})"
                else:
                    replacement = f"![Diagrama]({img_src_rel})"
                    
                result_markdown = result_markdown[:start] + replacement + result_markdown[end:]
                
        return result_markdown, blocks
