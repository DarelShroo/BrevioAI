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
        self._ensure_puppeteer_config()
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
                "-p", self.puppeteer_config_path
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
                
            block.success = True
            logger.info(f"[DIAGRAM] Rendered diagram #{block.index} -> {os.path.basename(block.svg_path)}")
            
        except Exception as e:
            block.success = False
            block.error = str(e)
            logger.error(f"[DIAGRAM] Failed rendering diagram #{block.index}: {e}")

    async def process(self, markdown: str, output_directory: str) -> Tuple[str, List[DiagramBlock]]:
        """
        Process the markdown, detect mermaid blocks, render them, and substitute the markdown blocks.
        
        Args:
            markdown: The original markdown text.
            output_directory: The directory where the summary.md is located. Artifacts will be saved in a 'diagrams' subdirectory.
            
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
                try:
                    with open(block.svg_path, "rb") as f:
                        svg_b64 = base64.b64encode(f.read()).decode("utf-8").replace('\n', '').replace('\r', '')
                    img_src = f"data:image/svg+xml;base64,{svg_b64}"
                    replacement = f'<img src="{img_src}" alt="Diagrama" class="md-img" />'
                except Exception as e:
                    logger.error(f"[DIAGRAM] Failed to encode SVG as base64 for block {block.index}: {e}")
                    # Fallback to relative path
                    img_src = f"diagrams/{os.path.basename(block.svg_path)}"
                    replacement = f"![Diagrama]({img_src})"
                    
                result_markdown = result_markdown[:start] + replacement + result_markdown[end:]
                
        return result_markdown, blocks
