import asyncio
import os
import time
import threading
import logging
from dotenv import load_dotenv
from openai import AsyncOpenAI
from backend.brevio.models.summary_config_model import SummaryConfig
from ..constants.summary_messages import SummaryMessages
from ..enums.role import RoleType
from ..managers.directory_manager import DirectoryManager
from ..models.response_model import SummaryResponse
import markdown
from docx import Document
from bs4 import BeautifulSoup
from .advanced_content_generator import AdvancedContentGenerator
load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class SummaryService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(SummaryService, cls).__new__(cls)
                    cls._instance._initialize()
                    logger.info("Created new instance of SummaryService.")
        else:
            logger.info("Using existing instance of SummaryService.")
        return cls._instance

    def _initialize(self):
        logger.info("Initializing SummaryService.")
        self.directory_manager = DirectoryManager()
        logger.info("DirectoryManager initialized.")
        self.max_tokens = int(os.getenv("MAX_TOKENS"))
        self.tokens_per_minute = int(os.getenv("TOKENS_PER_MINUTE"))
        self.temperature = float(os.getenv("TEMPERATURE"))
        logger.debug(f"Configuration: max_tokens={self.max_tokens}, tokens_per_minute={self.tokens_per_minute}, "
                     f"temperature={self.temperature}")

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            logger.error(
                "DEEPSEEK_API_KEY is not set in the environment variables.")
            raise ValueError("DEEPSEEK_API_KEY not set")
        self.client = AsyncOpenAI(
            api_key=api_key, base_url="https://api.deepseek.com")
        logger.info("OpenAI client initialized.")
        self.semaphore = asyncio.Semaphore(10)  # Control de concurrencia
        self.generator = AdvancedContentGenerator()

    def chunk_text(self, text, chunk_size):
        logger.debug("Chunking text into pieces.")
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    async def generate_summary_chunk(self, total_tokens_used, chunk, summary_config: SummaryConfig):
        logger.info("Generating summary for a text chunk.")
        if total_tokens_used + self.max_tokens > self.tokens_per_minute:
            logger.info(SummaryMessages.WAITING)
            # Nota: En un entorno async, podrías usar await asyncio.sleep(60)
            time.sleep(60)
            total_tokens_used = 0

        generator = self.generator.generate_prompt(
            category='journalism',
            style='breaking_news',
            output_format='html',
            lang=summary_config.language.name,
            source_type='video'
        )
        try:
            logger.debug(
                "Sending request to OpenAI API for summary generation.")
            response = await self.client.chat.completions.create(  # Añadimos await aquí
                model="deepseek-chat",  # summary_config.model.value,
                messages=[
                    {"role": RoleType.SYSTEM.value,
                     "content": generator},
                    {"role": RoleType.USER.value, "content": chunk}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            logger.debug("Received response from OpenAI API.")
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
            raise

        summary = response.choices[0].message.content.strip()
        total_tokens_used += response.usage.total_tokens
        logger.info(f"Chunk summary generated. Tokens used in this call: {response.usage.total_tokens}. "
                    f"Total tokens used: {total_tokens_used}.")
        return summary, total_tokens_used

    def markdown_to_docx(self, md_file_path, docx_file_path):
        logger.info(
            f"Converting Markdown file '{md_file_path}' to DOCX file '{docx_file_path}'.")
        try:
            with open(md_file_path, 'r', encoding='utf-8') as md_file:
                md_content = md_file.read()
            logger.debug("Markdown file read successfully.")

            html_content = markdown.markdown(md_content)
            logger.debug("Converted Markdown to HTML.")

            # Si el archivo DOCX ya existe, lo abrimos; si no, creamos uno nuevo
            if os.path.exists(docx_file_path):
                doc = Document(docx_file_path)
                logger.info(
                    f"Appending to existing DOCX file '{docx_file_path}'.")
            else:
                doc = Document()
                logger.info(f"Creating new DOCX file '{docx_file_path}'.")

            def add_html_to_docx(html):
                soup = BeautifulSoup(html, 'html.parser')
                for element in soup:
                    if element.name == 'h1':
                        doc.add_heading(element.text, level=1)
                    elif element.name == 'h2':
                        doc.add_heading(element.text, level=2)
                    elif element.name == 'h3':
                        doc.add_heading(element.text, level=3)
                    elif element.name == 'p':
                        doc.add_paragraph(element.text)
                    elif element.name == 'ul':
                        for li in element.find_all('li'):
                            doc.add_paragraph(li.text, style='List Bullet')
                logger.debug("HTML content added to DOCX document.")

            add_html_to_docx(html_content)
            doc.save(docx_file_path)
            logger.info(f"Word file saved at '{docx_file_path}'.")
        except Exception as e:
            logger.error(
                f"Error converting Markdown to Word: {e}", exc_info=True)
            raise

    async def generate_summary(self, summary_config: SummaryConfig):
        logger.info("Starting summary generation process.")
        try:
            logger.info(
                f"Validating transcription path: {summary_config.transcription_path}.")
            self.directory_manager.validate_paths(
                summary_config.transcription_path)

            logger.info(
                f"Reading transcription from: {summary_config.transcription_path}.")
            transcription = self.directory_manager.read_transcription(
                summary_config.transcription_path)
            logger.info("Transcription read successfully.")

            chunks = self.chunk_text(transcription, self.max_tokens)
            logger.info(f"Text split into {len(chunks)} chunks.")

            # Función asincrónica para procesar cada chunk, retornando su índice
            async def process_chunk(index, chunk):
                async with self.semaphore:  # Limitar llamadas concurrentes
                    try:
                        chunk_summary, tokens_used = await self.generate_summary_chunk(
                            0,  # Valor inicial o variable adecuada para tokens
                            chunk,
                            summary_config
                        )
                        return index, chunk_summary, tokens_used
                    except Exception as e:
                        logger.error(
                            f"Error procesando chunk {index}: {str(e)}")
                        return index, "", 0

            # Procesar todos los chunks concurrentemente, manteniendo el índice
            tasks = [process_chunk(i, chunk) for i, chunk in enumerate(chunks)]
            results = await asyncio.gather(*tasks)

            # Ordenar los resultados por índice para conservar el orden original
            results.sort(key=lambda x: x[0])
            # Separar los resultados
            chunk_summaries = [result[1] for result in results]
            tokens_used_list = [result[2] for result in results]

            # Combinar los resúmenes en el orden correcto
            full_summary = "\n".join([cs.lstrip('\n')
                                    for cs in chunk_summaries if cs])
            total_tokens_used = sum(tokens_used_list)

            logger.info(
                f"Writing summary to file: {summary_config.summary_path}.")
            self.directory_manager.write_summary(
                full_summary, summary_config.summary_path)

            docx_path = summary_config.summary_path.replace('.md', '.docx')
            logger.info(
                f"Converting Markdown summary to DOCX file: {docx_path}.")
            self.markdown_to_docx(summary_config.summary_path, docx_path)

            logger.info("Summary generation process completed successfully.")
            return SummaryResponse(
                success=True,
                summary=str(full_summary),
                message=str(SummaryMessages.WRITE_SUMMARY.format(
                    summary_config.summary_path))
            )
        except Exception as e:
            logger.error(
                f"Error during summary generation: {e}", exc_info=True)
            return SummaryResponse(
                success=False,
                summary=f"Error occurred: {str(e)}",
                message=SummaryMessages.ERROR_GENERATING_SUMMARY.format(str(e))
            )
    async def generate_summary_pdf(self, summary_config: SummaryConfig):
        logger.info("Starting PDF summary generation process.")
        try:
            self.directory_manager.validate_paths(summary_config.pdf_path)
            logger.info(f"Reading PDF from: {summary_config.pdf_path}")

            # Leer el PDF y dividir en fragmentos
            fragments = list(self.directory_manager.read_pdf(
                summary_config.pdf_path))
            all_chunks = []
            for fragment in fragments:
                chunks = self.chunk_text(fragment, self.max_tokens)
                all_chunks.extend(chunks)
            logger.info(f"Text split into {len(all_chunks)} chunks.")

            # Función asincrónica para procesar cada chunk, retornando su índice
            async def process_chunk(index, chunk):
                async with self.semaphore:  # Limitar llamadas concurrentes
                    try:
                        chunk_summary, tokens_used = await self.generate_summary_chunk(
                            0,  # Valor inicial o variable adecuada para tokens
                            chunk,
                            summary_config
                        )
                        return index, chunk_summary, tokens_used
                    except Exception as e:
                        logger.error(
                            f"Error procesando chunk {index}: {str(e)}")
                        return index, "", 0

            # Procesar todos los chunks concurrentemente, manteniendo el índice
            tasks = [process_chunk(i, chunk)
                     for i, chunk in enumerate(all_chunks)]
            results = await asyncio.gather(*tasks)

            # Ordenar los resultados por índice para conservar el orden original
            results.sort(key=lambda x: x[0])
            # Separar los resultados
            chunk_summaries = [result[1] for result in results]
            tokens_used_list = [result[2] for result in results]

            # Combinar los resúmenes en el orden correcto
            full_summary = "\n".join([cs.lstrip('\n')
                                     for cs in chunk_summaries if cs])
            total_tokens_used = sum(tokens_used_list)

            logger.info(
                f"Writing summary to file: {summary_config.summary_path}")
            self.directory_manager.write_summary(
                full_summary, summary_config.summary_path)

            docx_path = summary_config.summary_path.replace('.md', '.docx')
            logger.info(f"Converting Markdown summary to DOCX: {docx_path}")
            self.markdown_to_docx(summary_config.summary_path, docx_path)

            logger.info("PDF summary generation completed successfully.")
            return SummaryResponse(
                success=True,
                summary=full_summary,
                message=SummaryMessages.WRITE_SUMMARY.format(
                    summary_config.summary_path)
            )
        except Exception as e:
            logger.error(
                f"Error during PDF summary generation: {e}", exc_info=True)
            return SummaryResponse(
                success=False,
                summary=f"Error occurred: {str(e)}",
                message=SummaryMessages.ERROR_GENERATING_SUMMARY.format(str(e))
            )

    async def generate_summary_docx(self, summary_config: SummaryConfig):
        logger.info("Starting DOCX summary generation process.")
        try:
            logger.info(f"Validating DOCX path: {summary_config.docx_path}")
            self.directory_manager.validate_paths(summary_config.docx_path)

            logger.info(f"Reading DOCX from: {summary_config.docx_path}")
            doc = Document(summary_config.docx_path)
            full_text = "\n".join(
                [para.text for para in doc.paragraphs if para.text.strip()])

            chunks = self.chunk_text(full_text, self.max_tokens)
            logger.info(f"Text split into {len(chunks)} chunks.")

            # Función para procesar cada chunk con control de concurrencia y retornar su índice
            async def process_chunk(index, chunk):
                async with self.semaphore:  # Limitar llamadas concurrentes
                    try:
                        response = await self.client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[
                                {"role": RoleType.SYSTEM.value,
                                 "content": summary_config.content.value.format(summary_config.language.name)},
                                {"role": RoleType.USER.value, "content": chunk}
                            ],
                            max_tokens=self.max_tokens,
                            temperature=self.temperature
                        )
                        return index, response.choices[0].message.content.strip()
                    except Exception as e:
                        logger.error(
                            f"Error procesando chunk {index}: {str(e)}")
                        return index, ""

            # Procesar todos los chunks concurrentemente, asignando índices para preservar el orden
            tasks = [process_chunk(i, chunk) for i, chunk in enumerate(chunks)]
            results = await asyncio.gather(*tasks)

            # Ordenar los resultados por índice para conservar el orden original
            results.sort(key=lambda x: x[0])
            chunk_summaries = [result[1] for result in results]

            # Combinar los resúmenes en el orden correcto
            summary = "\n".join([cs.lstrip('\n')
                                for cs in chunk_summaries if cs])

            logger.info(
                f"Writing summary to file: {summary_config.summary_path}")
            self.directory_manager.write_summary(
                summary, summary_config.summary_path)

            docx_path = summary_config.summary_path.replace('.md', '.docx')
            logger.info(f"Converting Markdown summary to DOCX: {docx_path}")
            self.markdown_to_docx(summary_config.summary_path, docx_path)

            logger.info("DOCX summary generation completed successfully.")
            return SummaryResponse(
                success=True,
                summary=summary,
                message=SummaryMessages.WRITE_SUMMARY.format(
                    summary_config.summary_path)
            )
        except Exception as e:
            logger.error(
                f"Error during DOCX summary generation: {e}", exc_info=True)
            return SummaryResponse(
                success=False,
                summary=f"Error occurred: {str(e)}",
                message=SummaryMessages.ERROR_GENERATING_SUMMARY.format(str(e))
            )
