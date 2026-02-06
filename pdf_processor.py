"""
Processador de PDFs - VERSÃO CORRIGIDA
Parte 3/5 da refatoração
"""
import logging
from pathlib import Path
from playwright.async_api import Page, Locator
from base_processor import BaseCourseProcessor
from utils import sanitize_filename, download_file, verify_download

logger = logging.getLogger(__name__)


class PDFProcessor(BaseCourseProcessor):
    """Processador especializado para download de PDFs"""
    
    PDF_TYPES = {
        1: {'name': 'versão simplificada', 'urlPart': 'pdfSimplificado/download'},
        2: {'name': 'versão original', 'urlPart': 'pdf/download'},
        3: {'name': 'marcação dos aprovados', 'urlPart': 'pdfGrifado/download'}
    }
    
    def __init__(self, base_dir: Path, progress_manager, pdf_type: int = 2, log_queue=None):
        """
        Inicializa o processador de PDFs.
        
        Args:
            base_dir: Diretório base para downloads
            progress_manager: Gerenciador de progresso
            pdf_type: Tipo de PDF a baixar (1-4)
            log_queue: Fila para enviar status
        """
        super().__init__(base_dir, progress_manager, log_queue)
        
        # ✅ VALIDAÇÃO: Garante que pdf_type é válido
        if pdf_type not in [1, 2, 3, 4]:
            logger.warning(f"⚠ Tipo de PDF inválido ({pdf_type}), usando padrão (2)")
            pdf_type = 2
        
        # Define quais tipos de PDF baixar
        if pdf_type == 4:  # Baixar todos os tipos
            self.pdf_types_to_download = [1, 2, 3]
        else:
            self.pdf_types_to_download = [pdf_type]
        
        logger.info(f"📄 Processador de PDF inicializado (tipos: {self.pdf_types_to_download})")

    async def process_course(self, page: Page, course_url: str) -> bool:
        """
        Processa curso completo para download de PDFs.
        
        Args:
            page: Página do Playwright
            course_url: URL do curso
        
        Returns:
            True se processado com sucesso
        """
        try:
            # ✅ CORREÇÃO: Verifica cancelamento antes de começar
            await self.check_cancellation()
            
            # Usa métodos herdados do BaseCourseProcessor
            await self.navigate_to_course(page, course_url)
            course_name, course_dir = await self.extract_course_info(page)
            aulas = await self.get_lessons(page)
            
            if not aulas:
                logger.warning("⚠ Nenhuma aula encontrada no curso")
                return False
            
            # Processa cada aula
            success_count = 0
            failed_count = 0
            
            for i, aula_element in enumerate(aulas, 1):
                # ✅ CORREÇÃO: Verifica cancelamento a cada aula
                await self.check_cancellation()
                
                try:
                    await self._process_lesson(page, aula_element, course_dir, i)
                    success_count += 1
                except Exception as e:
                    logger.error(f"❌ Erro ao processar aula {i}: {e}")
                    failed_count += 1
            
            logger.info(f"✅ Curso '{course_name}' processado!")
            logger.info(f"   ✓ Aulas processadas: {success_count}")
            if failed_count > 0:
                logger.warning(f"   ⚠ Aulas com erro: {failed_count}")
            
            return success_count > 0
        
        # ✅ CORREÇÃO: Tratamento específico para cancelamento
        except asyncio.CancelledError:
            logger.warning("⚠ Processamento do curso cancelado")
            return False
        
        except Exception as e:
            logger.error(f"❌ Erro ao processar curso: {e}", exc_info=True)
            return False
    
    async def _process_lesson(
        self,
        page: Page,
        aula_element: Locator,
        course_dir: Path,
        index: int
    ) -> None:
        """
        Processa uma aula específica para download de PDFs.
        
        Args:
            page: Página do Playwright
            aula_element: Elemento da aula
            course_dir: Diretório do curso
            index: Índice da aula
        """
        try:
            # Extrai informações da aula (método herdado)
            aula_id, lesson_name, lesson_subtitle = await self.extract_lesson_info(aula_element, index)
            
            logger.info(f"📚 Processando aula {index}: {lesson_name}")
            
            # Expande a aula (método herdado)
            await self.expand_lesson(page, aula_id)
            
            # Busca botões de download de PDF
            download_buttons = await aula_element.locator('a:has-text("Baixar Livro Eletrônico")').all()
            
            if not download_buttons:
                logger.info(f"ℹ️  Nenhum PDF disponível em '{lesson_name}'")
                return
            
            logger.info(f"✓ Encontrados {len(download_buttons)} link(s) de PDF")
            
            # Processa cada botão de download encontrado
            for button in download_buttons:
                await self.check_cancellation()
                
                await self._process_pdf_button(
                    button, course_dir, lesson_name,
                    lesson_subtitle, aula_id
                )
        
        except asyncio.CancelledError:
            raise  # Propaga cancelamento
        
        except Exception as e:
            logger.error(f"❌ Erro ao processar aula {index}: {e}")
            # Não propaga para permitir continuar com outras aulas
    
    async def _process_pdf_button(
        self,
        button: Locator,
        course_dir: Path,
        lesson_name: str,
        lesson_subtitle: str,
        aula_id: str
    ) -> None:
        """
        Processa um botão de download de PDF específico.
        
        Args:
            button: Elemento do botão
            course_dir: Diretório do curso
            lesson_name: Nome da aula
            lesson_subtitle: Subtítulo da aula
            aula_id: ID da aula
        """
        try:
            pdf_url = await button.get_attribute('href')
            
            if not pdf_url:
                logger.warning("⚠ Botão sem URL de download")
                return
            
            # Normaliza URL (adiciona domínio se necessário)
            if pdf_url.startswith('/api'):
                pdf_url = "https://www.estrategiaconcursos.com.br" + pdf_url
            
            # ✅ VALIDAÇÃO: Verifica se URL é válida
            if not pdf_url.startswith('http'):
                logger.warning(f"⚠ URL inválida: {pdf_url}")
                return
            
            # Verifica cada tipo de PDF solicitado
            for pdf_type in self.pdf_types_to_download:
                await self.check_cancellation()
                
                pdf_info = self.PDF_TYPES.get(pdf_type)
                
                if not pdf_info:
                    continue
                
                # Verifica se a URL corresponde ao tipo de PDF
                if pdf_info["urlPart"] not in pdf_url:
                    continue
                
                # Define nome do arquivo
                base_file_name = f'{lesson_name} - {lesson_subtitle}'
                file_name = f'{sanitize_filename(base_file_name, 180)} ({pdf_info["name"]}).pdf'
                file_path = course_dir / file_name
                
                # Chave única para controle de progresso (estável entre execuções)
                progress_key = f'{aula_id}-{file_name}'
                
                # Verifica se já foi baixado (método herdado)
                if self.is_already_downloaded(progress_key):
                    logger.info(f"⏭️  Já baixado: {file_name}")
                    continue
                
                try:
                    logger.info(f"⬇️  Baixando: {file_name}")
                    
                    # ✅ Callback de progresso
                    def progress_callback(current, total, speed):
                        if self.log_queue:
                            try:
                                self.log_queue.put_nowait({
                                    "type": "progress",
                                    "file": file_name,
                                    "current": current,
                                    "total": total,
                                    "speed": speed
                                })
                            except:
                                pass

                    # ✅ MELHORIA: Download com rate limiting
                    await self.download_with_rate_limit(
                        download_file,
                        pdf_url,
                        file_path,
                        logger,
                        progress_callback=progress_callback
                    )
                    
                    # ✅ NOVA FUNCIONALIDADE: Validação de magic bytes
                    await verify_download(
                        file_path,
                        logger,
                        min_size=10240,  # Min 10KB
                        expected_extension='.pdf'
                    )
                    
                    # Marca como baixado (método herdado)
                    self.mark_as_downloaded(progress_key)
                    
                    logger.info(f"✅ Concluído: {file_name}")
                
                except asyncio.CancelledError:
                    # ✅ CORREÇÃO: Remove arquivo parcial em cancelamento
                    logger.warning("⚠ Download cancelado")
                    if file_path.exists():
                        file_path.unlink()
                        logger.debug(f"✓ Arquivo parcial removido: {file_name}")
                    raise
                
                except Exception as e:
                    logger.error(f"❌ Falha ao baixar '{file_name}': {e}")
                    # Remove arquivo corrompido se existir
                    if file_path.exists():
                        file_path.unlink()
                        logger.debug("✓ Arquivo corrompido removido")
                
                # Só processa o primeiro tipo de PDF que corresponder
                break
        
        except asyncio.CancelledError:
            raise  # Propaga cancelamento
        
        except Exception as e:
            logger.error(f"❌ Erro ao processar botão de PDF: {e}")
