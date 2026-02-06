"""
Módulo Principal de Download - VERSÃO FINAL INTEGRADA v3.1
Inclui suporte completo a materiais complementares
Parte 4/5 da refatoração
"""
import logging
import sys
import asyncio
from pathlib import Path
from typing import Optional, Callable
from playwright.async_api import async_playwright, Error as PlaywrightError
from config_manager import ConfigManager, ProgressManager, CourseUrlManager
from auth import AuthManager
from video_processor import VideoProcessor
from pdf_processor import PDFProcessor
from utils import setup_logger, PrintRedirector, DownloadMetrics

logger = logging.getLogger(__name__)


class DownloadManager:
    """Gerenciador principal que orquestra todo o processo de download"""
    
    BROWSER_TIMEOUT = 30000  # ms
    
    def __init__(self, config_manager: ConfigManager, log_queue=None):
        """
        Inicializa o gerenciador de downloads.
        
        Args:
            config_manager: Gerenciador de configurações
            log_queue: Fila para enviar logs para interface (opcional)
        """
        self.config = config_manager
        self.progress = ProgressManager()
        self.url_manager = CourseUrlManager()
        self.log_queue = log_queue
        
        self._cancel_event = asyncio.Event()
        self.metrics = DownloadMetrics()
        
        # Configura logger
        global logger
        logger = setup_logger(__name__, log_queue)
        
        # Redireciona print para logger
        sys.stdout = PrintRedirector(logger)
        
        logger.info("✓ DownloadManager inicializado")
    
    def request_cancel(self) -> None:
        """Solicita cancelamento dos downloads em andamento (thread-safe)"""
        self._cancel_event.set()
        logger.warning("⚠ Cancelamento solicitado pelo usuário")
    
    @property
    def cancel_requested(self) -> bool:
        """Verifica se cancelamento foi solicitado"""
        return self._cancel_event.is_set()
    
    async def start_downloads(
        self,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """
        Inicia processo de download de todos os cursos na fila.
        
        Args:
            progress_callback: Função callback para atualizar progresso (opcional)
                             Recebe um float entre 0.0 e 1.0
        
        Returns:
            True se completou com sucesso, False caso contrário
        """
        logger.info("=" * 70)
        logger.info("🚀 INICIANDO ESTRATÉGIA DOWNLOADER PRO v3.1")
        logger.info("=" * 70)
        
        # Health check
        if not await self._health_check():
            logger.error("❌ Health check falhou. Processo abortado.")
            return False
        
        # Obtém lista de URLs
        course_urls = self.url_manager.get_all()
        if not course_urls:
            logger.warning("⚠ Nenhum curso na lista para baixar")
            logger.info("   Adicione cursos na aba 'Cursos' e tente novamente")
            return False
        
        total_courses = len(course_urls)
        logger.info(f"📚 Total de cursos na fila: {total_courses}")
        logger.info("")
        
        # Inicia navegador
        playwright = None
        context = None
        
        try:
            playwright = await async_playwright().start()
            context = await self._launch_browser(playwright)
            page = await context.new_page()
            
            # Faz login
            await self._perform_authentication(page)
            
            # Processa cada curso
            success_count = 0
            failed_count = 0
            
            for i, course_url in enumerate(course_urls, 1):
                if self.cancel_requested:
                    logger.warning("❌ Downloads cancelados pelo usuário")
                    break
                
                logger.info("")
                logger.info("=" * 70)
                logger.info(f"📖 Processando curso {i}/{total_courses}")
                logger.info("=" * 70)
                logger.info(f"🔗 URL: {course_url}")
                logger.info("")
                
                # Processa o curso
                try:
                    success = await self._process_course(page, course_url)
                    
                    if success:
                        success_count += 1
                        logger.info(f"✅ Curso {i}/{total_courses} processado com sucesso!")
                    else:
                        failed_count += 1
                        logger.error(f"❌ Curso {i}/{total_courses} falhou")
                
                except asyncio.CancelledError:
                    logger.warning("⚠ Processamento cancelado")
                    break
                
                except Exception as e:
                    logger.error(f"❌ Erro ao processar curso {i}: {e}", exc_info=True)
                    failed_count += 1
                
                # Atualiza callback de progresso
                if progress_callback:
                    try:
                        progress_callback(i / total_courses)
                    except Exception as e:
                        logger.warning(f"⚠ Erro no callback de progresso: {e}")
            
            # Relatório final
            logger.info("")
            logger.info("=" * 70)
            logger.info("📊 RELATÓRIO FINAL")
            logger.info("=" * 70)
            logger.info(f"✅ Cursos processados com sucesso: {success_count}")
            logger.info(f"❌ Cursos com falha: {failed_count}")
            logger.info(f"📚 Total de cursos: {total_courses}")
            logger.info("=" * 70)
            
            # Estatísticas de download
            self.metrics.log_stats(logger)
            
            logger.info("=" * 70)
            logger.info("✅ PROCESSO FINALIZADO")
            logger.info("=" * 70)
            
            return failed_count == 0
        
        except asyncio.CancelledError:
            logger.warning("⚠ Processo cancelado pelo usuário")
            return False
        
        except PlaywrightError as e:
            logger.error(f"❌ Erro do Playwright: {e}", exc_info=True)
            return False
        
        except Exception as e:
            logger.error(f"❌ Erro crítico no processo: {e}", exc_info=True)
            return False
        
        finally:
            # Cleanup
            if context:
                logger.info("🔒 Fechando navegador...")
                try:
                    await context.close()
                except Exception as e:
                    logger.warning(f"⚠ Erro ao fechar contexto: {e}")
            
            if playwright:
                try:
                    await playwright.stop()
                except Exception as e:
                    logger.warning(f"⚠ Erro ao parar playwright: {e}")
            
            logger.info("✓ Recursos liberados")
    
    async def _health_check(self) -> bool:
        """
        Verifica se sistema está pronto para download.
        
        Returns:
            True se todos os checks passarem
        """
        logger.info("🔍 Realizando health check...")
        
        checks = {}
        
        # Check 1: Email configurado
        email = self.config.config.get("email")
        checks["Email configurado"] = bool(email and "@" in email)
        
        # Check 2: Senha configurada
        checks["Senha configurada"] = bool(self.config.get_password())
        
        # Check 3: Tipo de download válido
        download_type = self.config.config.get("downloadType")
        checks["Tipo de download válido"] = download_type in ["pdf", "video"]
        
        # Check 4: Pasta de destino acessível
        if download_type == "pdf":
            folder = self.config.get("pdfConfig", "pastaDownloads")
        else:
            folder = self.config.get("videoConfig", "pastaDownloads")
        
        try:
            folder_path = Path(folder)
            checks["Pasta pai existe"] = folder_path.parent.exists()
            
            # Tenta criar pasta de destino
            folder_path.mkdir(parents=True, exist_ok=True)
            checks["Pasta gravável"] = folder_path.exists()
        except Exception as e:
            logger.error(f"❌ Erro ao verificar pasta: {e}")
            checks["Pasta pai existe"] = False
            checks["Pasta gravável"] = False
        
        # Check 5: URLs na fila
        checks["URLs na fila"] = len(self.url_manager.get_all()) > 0
        
        # ✅ Check 6: Configuração de extras (se aplicável)
        if download_type == "video":
            baixar_extras = self.config.get("videoConfig", "baixarExtras", default=True)
            checks["Config de extras válida"] = isinstance(baixar_extras, bool)
            logger.info(f"   Baixar materiais extras: {'Sim' if baixar_extras else 'Não'}")
        
        # Exibe resultados
        logger.info("")
        for check, status in checks.items():
            logger.info(f"{'✅' if status else '❌'} {check}")
        logger.info("")
        
        all_passed = all(checks.values())
        
        if not all_passed:
            logger.error("❌ Health check falhou. Corrija os problemas acima.")
            logger.info("💡 Configure em: Configurações")
        else:
            logger.info("✅ Health check passou!")
        
        return all_passed
    
    async def _launch_browser(self, playwright) -> "BrowserContext":
        """
        Inicia navegador Chrome com configurações apropriadas.
        
        Args:
            playwright: Instância do Playwright
        
        Returns:
            Contexto do navegador
        
        Raises:
            Exception: Se Chrome não for encontrado ou falhar ao iniciar
        """
        # Configurações do navegador
        headless = self.config.config.get("headless", False)
        cache_dir = Path.home() / "AppData" / "Local" / "EstrategiaDownloaderCache"
        
        logger.info("🌐 Iniciando navegador...")
        logger.info(f"✓ Modo headless: {'Sim' if headless else 'Não'}")
        logger.info(f"✓ Cache: {cache_dir}")
        
        try:
            # Tenta criar diretório de cache
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, IOError) as e:
                logger.warning(f"⚠ Não foi possível criar diretório de cache: {e}")
                # Usa diretório temporário
                import tempfile
                cache_dir = Path(tempfile.mkdtemp(prefix="estrategia_"))
                logger.info(f"✓ Usando cache temporário: {cache_dir}")
            
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(cache_dir),
                headless=headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                ],
                timeout=self.BROWSER_TIMEOUT
            )
            
            logger.info("✓ Navegador iniciado com sucesso")
            return context
        
        except PlaywrightError as e:
            error_msg = str(e).lower()
            
            if "executable" in error_msg or "chromium" in error_msg:
                logger.error("❌ Chromium não encontrado")
                logger.info("💡 Execute: playwright install chromium")
                raise Exception(
                    "Chromium não instalado. Execute: playwright install chromium"
                )
            else:
                logger.error(f"❌ Falha ao iniciar navegador: {e}")
                raise Exception(f"Não foi possível iniciar o navegador: {e}")
        
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao iniciar navegador: {e}", exc_info=True)
            raise
    
    async def _perform_authentication(self, page: "Page") -> None:
        """
        Realiza autenticação na plataforma.
        
        Args:
            page: Página do Playwright
        
        Raises:
            Exception: Se autenticação falhar
        """
        email = self.config.config.get("email")
        password = self.config.get_password()
        
        if not email or not password:
            raise ValueError("Email ou senha não configurados")
        
        logger.info("🔐 Iniciando processo de autenticação...")
        
        try:
            auth = AuthManager(email, password)
            await auth.ensure_logged_in(page)
            logger.info("✓ Autenticação concluída com sucesso")
        
        except ValueError as e:
            logger.error(f"❌ Erro de validação: {e}")
            raise
        
        except Exception as e:
            logger.error(f"❌ Falha na autenticação: {e}")
            logger.info("   Verifique suas credenciais em: Configurações")
            raise
    
    async def _process_course(self, page: "Page", course_url: str) -> bool:
        """
        Processa um curso específico usando o processador apropriado.
        
        Args:
            page: Página do Playwright
            course_url: URL do curso
        
        Returns:
            True se processado com sucesso
        """
        download_type = self.config.config.get("downloadType", "pdf")
        
        try:
            # Cria processador apropriado
            if download_type == "pdf":
                processor = self._create_pdf_processor()
            else:
                processor = self._create_video_processor()
            
            # Propaga cancelamento para o processador
            if self.cancel_requested:
                processor.request_cancel()
            
            # Processa o curso
            success = await processor.process_course(page, course_url)
            
            # ✅ NOVA LÓGICA: Se for tipo PDF e tiver opção de baixar extras de vídeo habilitada
            if success and download_type == "pdf":
                baixar_extras = self.config.get("pdfConfig", "baixarExtrasComPdf", default=False)
                
                if baixar_extras:
                    logger.info("")
                    logger.info("🎬 Iniciando download de materiais complementares dos vídeos...")
                    logger.info("(Mapas Mentais, Resumos e Slides)")
                    logger.info("-" * 50)
                    
                    # Cria processador de vídeo em modo "skip_video"
                    video_processor = self._create_video_processor_for_extras()
                    
                    # Propaga cancelamento
                    if self.cancel_requested:
                        video_processor.request_cancel()
                    
                    # Executa
                    await video_processor.process_course(page, course_url)
            
            return success
        
        except asyncio.CancelledError:
            logger.warning("⚠ Processamento cancelado")
            return False
        
        except Exception as e:
            logger.error(f"❌ Erro ao processar curso: {e}", exc_info=True)
            return False
    
    def _create_pdf_processor(self) -> PDFProcessor:
        """
        Cria processador de PDF com configurações do usuário.
        
        Returns:
            Instância configurada de PDFProcessor
        """
        base_dir = Path(self.config.get("pdfConfig", "pastaDownloads"))
        pdf_type = self.config.get("pdfConfig", "pdfType", default=2)
        
        logger.info(f"📄 Criando processador de PDF (tipo: {pdf_type})")
        
        return PDFProcessor(
            base_dir=base_dir,
            progress_manager=self.progress,
            pdf_type=pdf_type,
            log_queue=self.log_queue  # ✅ Passa fila de logs
        )
    
    def _create_video_processor(self) -> VideoProcessor:
        """
        Cria processador de vídeo com configurações do usuário.
        
        Returns:
            Instância configurada de VideoProcessor
        """
        base_dir = Path(self.config.get("videoConfig", "pastaDownloads"))
        resolution = self.config.get("videoConfig", "resolucaoEscolhida", default="720p")
        
        # ✅ NOVA CONFIGURAÇÃO: Suporte a baixar extras
        download_extras = self.config.get("videoConfig", "baixarExtras", default=True)
        
        logger.info(f"🎥 Criando processador de vídeo")
        logger.info(f"   Resolução: {resolution}")
        logger.info(f"   Baixar extras: {'Sim' if download_extras else 'Não'}")
        
        return VideoProcessor(
            base_dir=base_dir,
            progress_manager=self.progress,
            preferred_resolution=resolution,
            download_extras=download_extras,  # ✅ Passa configuração para o processador
            skip_video=False,
            log_queue=self.log_queue  # ✅ Passa fila de logs
        )

    def _create_video_processor_for_extras(self) -> VideoProcessor:
        """
        Cria processador de vídeo configurado APENAS para baixar extras.
        Usa a pasta de PDFs como destino para manter tudo junto.
        """
        # Usa a pasta de PDFs como base, já que é um complemento ao download de PDFs
        base_dir = Path(self.config.get("pdfConfig", "pastaDownloads"))
        
        logger.info(f"🎥 Criando processador auxiliar para Materiais Extras")
        logger.info(f"   Destino: {base_dir}")
        
        return VideoProcessor(
            base_dir=base_dir,
            progress_manager=self.progress,
            preferred_resolution='360p', # Irrelevante pois não vai baixar vídeo
            download_extras=True,
            skip_video=True, # ✅ MODO IMPORTANTE: Pula download de vídeo
            log_queue=self.log_queue  # ✅ Passa fila de logs
        )


# Função auxiliar para uso standalone (linha de comando)
async def main() -> int:
    """
    Função principal para execução via linha de comando.
    
    Returns:
        Código de saída (0 = sucesso, 1 = falha)
    """
    import asyncio
    
    config = ConfigManager()
    manager = DownloadManager(config)
    
    print("\n" + "="*70)
    print("ESTRATÉGIA DOWNLOADER PRO v3.1 - Modo Linha de Comando")
    print("="*70 + "\n")
    
    try:
        success = await manager.start_downloads()
        
        if success:
            print("\n✅ Todos os downloads foram concluídos com sucesso!")
            return 0
        else:
            print("\n⚠ Alguns downloads falharam. Verifique os logs.")
            return 1
    
    except KeyboardInterrupt:
        print("\n⚠ Processo interrompido pelo usuário")
        return 130  # Código padrão para Ctrl+C
    
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        return 1


if __name__ == "__main__":
    """Permite executar diretamente: python downloader.py"""
    import asyncio
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠ Interrompido")
        sys.exit(130)
