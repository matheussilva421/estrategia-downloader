"""
Processador Base para Cursos - VERSÃO CORRIGIDA
Parte 2/5 da refatoração
"""
import logging
import re
import asyncio
from pathlib import Path
from typing import Tuple, Optional
from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError
from utils import sanitize_filename, extract_materia_name

logger = logging.getLogger(__name__)


class BaseCourseProcessor:
    """
    Classe base para processamento de cursos.
    Define métodos comuns para processadores de PDF e Vídeo.
    """
    
    # ✅ NOVAS CONSTANTES: Magic numbers convertidos em constantes
    DEFAULT_NAVIGATION_TIMEOUT = 60000  # ms
    DEFAULT_ELEMENT_TIMEOUT = 30000     # ms
    LESSON_EXPAND_TIMEOUT = 15000       # ms
    POST_EXPAND_DELAY = 1.0             # segundos
    RATE_LIMIT_DELAY = 0.5              # segundos entre downloads
    MAX_CONCURRENT_DOWNLOADS = 3        # downloads simultâneos
    
    def __init__(self, base_dir: Path, progress_manager, log_queue=None):
        """
        Inicializa o processador base.
        
        Args:
            base_dir: Diretório base para downloads
            progress_manager: Gerenciador de progresso
            log_queue: Fila para enviar logs e status
        """
        self.base_dir = Path(base_dir)
        self.progress_manager = progress_manager
        self.log_queue = log_queue
        
        # ✅ CORREÇÃO: asyncio.Event ao invés de bool para thread-safety
        self._cancel_event = asyncio.Event()
        
        # ✅ NOVA FUNCIONALIDADE: Semáforo para rate limiting
        self._download_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_DOWNLOADS)
    
    def request_cancel(self) -> None:
        """Solicita cancelamento do processamento atual (thread-safe)"""
        self._cancel_event.set()
        logger.info("⚠ Cancelamento solicitado")
    
    @property
    def cancel_requested(self) -> bool:
        """
        Verifica se cancelamento foi solicitado (thread-safe).
        
        Returns:
            True se cancelamento foi solicitado
        """
        return self._cancel_event.is_set()
    
    async def check_cancellation(self) -> None:
        """
        Verifica cancelamento e lança exceção se solicitado.
        
        Raises:
            asyncio.CancelledError: Se cancelamento foi solicitado
        """
        if self.cancel_requested:
            raise asyncio.CancelledError("Processamento cancelado pelo usuário")
    
    async def navigate_to_course(self, page: Page, course_url: str) -> None:
        """
        Navega para a página do curso.
        Lida com redirecionamentos para dashboard.
        
        Args:
            page: Página do Playwright
            course_url: URL do curso
        
        Raises:
            Exception: Se navegação falhar
        """
        logger.info(f"🌐 Navegando para: {course_url}")
        
        try:
            await page.goto(
                course_url,
                wait_until='domcontentloaded',
                timeout=self.DEFAULT_NAVIGATION_TIMEOUT
            )
            
            # Verifica se foi redirecionado para o dashboard genérico
            if "app/dashboard/cursos" in page.url and not re.search(r'/cursos/\d+/aulas', page.url):
                logger.warning("⚠ Redirecionado para dashboard. Tentando novamente...")
                
                await asyncio.sleep(1)  # Pequeno delay antes de retry
                
                await page.goto(
                    course_url,
                    wait_until='domcontentloaded',
                    timeout=self.DEFAULT_NAVIGATION_TIMEOUT
                )
                
                # Se ainda estiver no dashboard, algo está errado
                if "app/dashboard/cursos" in page.url and not re.search(r'/cursos/\d+/aulas', page.url):
                    raise Exception(
                        "Não foi possível acessar a página do curso. "
                        "Verifique se a URL está correta e se você tem acesso ao curso."
                    )
            
            logger.info("✓ Navegação concluída")
        
        # ✅ CORREÇÃO: Tratamento de erro mais específico
        except PlaywrightTimeoutError:
            raise Exception(f"Timeout ao navegar para {course_url}")
        
        except Exception as e:
            logger.error(f"❌ Erro na navegação: {e}")
            raise
    
    async def extract_course_info(self, page: Page) -> Tuple[str, Path]:
        """
        Extrai informações do curso (nome e diretório).
        
        Args:
            page: Página do Playwright
        
        Returns:
            Tupla com (nome_do_curso, diretório_do_curso)
        
        Raises:
            Exception: Se extração falhar
        """
        logger.info("📚 Extraindo informações do curso...")
        
        try:
            # Tenta extrair nome do elemento específico
            course_name_element = await page.wait_for_selector(
                '.CourseInfo-content-title',
                timeout=self.DEFAULT_ELEMENT_TIMEOUT
            )
            course_name = await course_name_element.text_content()
            logger.info(f"✓ Nome extraído: {course_name}")
        
        except PlaywrightTimeoutError:
            logger.warning("⚠ Timeout ao extrair nome. Usando título da página.")
            try:
                course_name = await page.title()
            except Exception:
                course_name = "Curso Desconhecido"
        
        except Exception as e:
            logger.warning(f"⚠ Erro ao extrair nome: {e}. Usando título da página.")
            try:
                course_name = await page.title()
            except Exception:
                course_name = "Curso Desconhecido"
        
        # Extrai nome da matéria e cria diretório
        materia_name = extract_materia_name(course_name)
        course_dir = self.base_dir / sanitize_filename(materia_name)
        
        # ✅ MELHORIA: Trata erro ao criar diretório
        try:
            course_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, IOError) as e:
            logger.error(f"❌ Erro ao criar diretório: {e}")
            raise Exception(f"Não foi possível criar diretório do curso: {e}")
        
        logger.info(f"✓ Curso: {course_name}")
        logger.info(f"✓ Pasta: {course_dir}")
        
        return course_name, course_dir
    
    async def get_lessons(self, page: Page) -> list[Locator]:
        """
        Obtém lista de elementos de aulas do curso.
        
        Args:
            page: Página do Playwright
        
        Returns:
            Lista de elementos de aula
        
        Raises:
            Exception: Se não encontrar aulas
        """
        try:
            # ✅ MELHORIA: Aguarda aulas carregarem
            await page.wait_for_selector(
                '.LessonList-item',
                timeout=self.DEFAULT_ELEMENT_TIMEOUT
            )
            
            aulas = await page.locator('.LessonList-item').all()
            total = len(aulas)
            
            if total == 0:
                raise Exception("Nenhuma aula encontrada na página")
            
            logger.info(f"✓ Total de aulas encontradas: {total}")
            return aulas
        
        except PlaywrightTimeoutError:
            logger.error("❌ Timeout ao buscar aulas")
            raise Exception("Não foi possível encontrar aulas no curso")
        
        except Exception as e:
            logger.error(f"❌ Erro ao obter aulas: {e}")
            raise
    
    async def expand_lesson(self, page: Page, aula_id: str) -> None:
        """
        Garante que uma aula esteja expandida para mostrar seu conteúdo.
        
        Args:
            page: Página do Playwright
            aula_id: ID da aula a ser expandida
        """
        logger.info(f"📂 Expandindo aula #{aula_id}...")
        
        try:
            # Tenta expandir via JavaScript
            await page.evaluate(
                """(id) => {
                    const header = document.querySelector(`#${id} .Collapse-header`);
                    if (header) {
                        const content = header.parentElement.nextElementSibling;
                        if (content && content.style.display === "none") {
                            header.click();
                        }
                    }
                }""",
                aula_id
            )
            
            # Aguarda conteúdo ficar visível
            await page.wait_for_selector(
                f'#{aula_id} [class*="ListVideos"], #{aula_id} [class*="VideoItem"]',
                state='visible',
                timeout=self.LESSON_EXPAND_TIMEOUT
            )
            
            logger.info(f"✓ Aula #{aula_id} expandida")
        
        except PlaywrightTimeoutError:
            logger.warning(f"⚠ Timeout ao expandir aula #{aula_id}. Conteúdo pode já estar visível.")
        
        except Exception as e:
            logger.error(f"❌ Erro ao expandir aula #{aula_id}: {e}")
        
        # Aguarda carregamento assíncrono adicional
        await asyncio.sleep(self.POST_EXPAND_DELAY)
    
    async def extract_lesson_info(
        self,
        aula_element: Locator,
        index: int
    ) -> Tuple[str, str, str]:
        """
        Extrai informações de uma aula (ID, nome, subtítulo).
        
        Args:
            aula_element: Elemento da aula
            index: Índice da aula (usado como fallback)
        
        Returns:
            Tupla com (aula_id, lesson_name, lesson_subtitle)
        """
        # Extrai ID
        aula_id = await aula_element.get_attribute('id')
        if not aula_id:
            aula_id = f'aula{index:02d}'
        
        # Extrai título principal
        try:
            title_element = aula_element.locator(".LessonCollapseHeader-title .SectionTitle")
            if await title_element.count() > 0:
                lesson_name_raw = await title_element.text_content()
            else:
                lesson_name_raw = f"Aula {index:02d}"
        except Exception as e:
            logger.debug(f"Erro ao extrair título: {e}")
            lesson_name_raw = f"Aula {index:02d}"
        
        # Extrai subtítulo
        try:
            subtitle_element = aula_element.locator(".LessonCollapseHeader-title .sc-gZMcBi")
            if await subtitle_element.count() > 0:
                lesson_subtitle_raw = await subtitle_element.text_content()
            else:
                lesson_subtitle_raw = "Sem Subtítulo"
        except Exception as e:
            logger.debug(f"Erro ao extrair subtítulo: {e}")
            lesson_subtitle_raw = "Sem Subtítulo"
        
        # Sanitiza os nomes
        lesson_name = sanitize_filename(lesson_name_raw)
        lesson_subtitle = sanitize_filename(lesson_subtitle_raw)
        
        return aula_id, lesson_name, lesson_subtitle
    
    def is_already_downloaded(self, progress_key: str) -> bool:
        """
        Verifica se um item já foi baixado anteriormente.
        
        Args:
            progress_key: Chave única do item
        
        Returns:
            True se já foi baixado
        """
        return self.progress_manager.is_completed(progress_key)
    
    def mark_as_downloaded(self, progress_key: str) -> None:
        """
        Marca um item como baixado no registro de progresso.
        
        Args:
            progress_key: Chave única do item
        """
        self.progress_manager.mark_completed(progress_key)
    
    # ✅ NOVA FUNCIONALIDADE: Download com rate limiting
    async def download_with_rate_limit(self, download_func, *args, **kwargs):
        """
        Executa download com rate limiting.
        
        Args:
            download_func: Função de download assíncrona
            *args: Argumentos posicionais para a função
            **kwargs: Argumentos nomeados para a função
        
        Returns:
            Resultado da função de download
        """
        async with self._download_semaphore:
            # ✅ CORREÇÃO: Garante que kwargs sejam passados corretamente
            result = await download_func(*args, **kwargs)
            await asyncio.sleep(self.RATE_LIMIT_DELAY)
            return result
    
    async def process_course(self, page: Page, course_url: str) -> bool:
        """
        Método abstrato que deve ser implementado pelas subclasses.
        Processa um curso completo.
        
        Args:
            page: Página do Playwright
            course_url: URL do curso
        
        Returns:
            True se processado com sucesso
        
        Raises:
            NotImplementedError: Se não for implementado pela subclasse
        """
        raise NotImplementedError(
            "As subclasses devem implementar o método process_course()"
        )
