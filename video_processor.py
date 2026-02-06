"""
Processador de Vídeos - VERSÃO EXPANDIDA
Inclui download de Mapas Mentais e Resumos
Parte 3/5 da refatoração
"""
import logging
import asyncio
import re
from pathlib import Path
from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError
from base_processor import BaseCourseProcessor
from utils import sanitize_filename, download_file, verify_download
import aiohttp

logger = logging.getLogger(__name__)


class VideoProcessor(BaseCourseProcessor):
    """Processador especializado para download de vídeos e materiais complementares"""
    
    AVAILABLE_RESOLUTIONS = ['720p', '480p', '360p']
    
    # Constantes
    VIDEO_PLAYER_TIMEOUT = 15000
    PLAYER_HEIGHT_CHECK_TIMEOUT = 10000
    MIN_PLAYER_HEIGHT = 120
    PLAYER_LOAD_DELAY = 1.2
    VIDEO_SELECTION_DELAY = 1.0
    QUALITY_MENU_TIMEOUT = 8000
    RESOLUTION_CHANGE_TIMEOUT = 15000
    
    # ✅ NOVAS CONSTANTES: Para materiais complementares
    MATERIAL_LOAD_TIMEOUT = 10000
    MATERIAL_CLICK_DELAY = 0.5
    
    def __init__(
        self,
        base_dir: Path,
        progress_manager,
        preferred_resolution: str = '720p',
        download_extras: bool = True,  # ✅ NOVO: Flag para baixar materiais extras
        skip_video: bool = False,      # ✅ NOVO: Se True, não baixa vídeo (apenas extras)
        log_queue=None                 # ✅ Passa fila de logs
    ):
        """
        Inicializa o processador de vídeos.
        
        Args:
            base_dir: Diretório base para downloads
            progress_manager: Gerenciador de progresso
            preferred_resolution: Resolução preferida (720p, 480p, 360p)
            download_extras: Se True, baixa também mapas mentais e resumos
            skip_video: Se True, apenas navega e baixa extras, ignorando o arquivo de vídeo
            log_queue: Fila para enviar status
        """
        super().__init__(base_dir, progress_manager, log_queue)
        
        if preferred_resolution not in self.AVAILABLE_RESOLUTIONS:
            logger.warning(
                f"⚠ Resolução inválida ({preferred_resolution}), usando padrão (720p)"
            )
            preferred_resolution = '720p'
        
        self.preferred_resolution = preferred_resolution
        self.download_extras = download_extras
        self.skip_video = skip_video
        
        logger.info(f"🎥 Processador de vídeo inicializado")
        logger.info(f"   Resolução: {preferred_resolution}")
        logger.info(f"   Baixar extras: {'Sim' if download_extras else 'Não'}")
        if skip_video:
            logger.info("   ⚠ MODO SOMENTE EXTRAS: Download de vídeo será ignorado")
    
    async def process_course(self, page: Page, course_url: str) -> bool:
        """
        Processa curso completo para download de vídeos.
        
        Args:
            page: Página do Playwright
            course_url: URL do curso
        
        Returns:
            True se processado com sucesso
        """
        try:
            await self.check_cancellation()
            
            await self.navigate_to_course(page, course_url)
            course_name, course_dir = await self.extract_course_info(page)
            aulas = await self.get_lessons(page)
            
            if not aulas:
                logger.warning("⚠ Nenhuma aula encontrada no curso")
                return False
            
            success_count = 0
            failed_count = 0
            
            for aula_element in aulas:
                await self.check_cancellation()
                
                try:
                    await self._process_lesson(page, aula_element, course_dir, course_url)
                    success_count += 1
                except Exception as e:
                    logger.error(f"❌ Erro ao processar aula: {e}")
                    failed_count += 1
            
            logger.info(f"✅ Curso '{course_name}' processado!")
            logger.info(f"   ✓ Aulas processadas: {success_count}")
            if failed_count > 0:
                logger.warning(f"   ⚠ Aulas com erro: {failed_count}")
            
            return success_count > 0
        
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
        course_url: str
    ) -> None:
        """
        Processa uma aula específica para download de vídeos.
        
        Args:
            page: Página do Playwright
            aula_element: Elemento da aula
            course_dir: Diretório do curso
            course_url: URL do curso (para recuperação de erros)
        """
        try:
            aula_id, lesson_name, _ = await self.extract_lesson_info(aula_element, 0)
            
            lesson_dir = course_dir / lesson_name
            
            try:
                lesson_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, IOError) as e:
                logger.error(f"❌ Erro ao criar diretório da aula: {e}")
                return
            
            logger.info(f"🎬 Processando aula: {lesson_name}")
            
            await self.expand_lesson(page, aula_id)
            
            videos = await aula_element.locator('.ListVideos-items-video a.VideoItem').all()
            
            if not videos:
                logger.info(f"ℹ️  Nenhum vídeo encontrado em '{lesson_name}'")
                return
            
            logger.info(f"✓ Encontrados {len(videos)} vídeo(s)")
            
            for j, video_element in enumerate(videos, 1):
                await self.check_cancellation()
                
                await self._process_video(
                    page, video_element, lesson_name, lesson_dir,
                    aula_id, j, course_url
                )
        
        except asyncio.CancelledError:
            raise
        
        except Exception as e:
            logger.error(f"❌ Erro ao processar aula: {e}")
    
    async def _process_video(
        self,
        page: Page,
        video_element: Locator,
        lesson_name: str,
        lesson_dir: Path,
        aula_id: str,
        video_index: int,
        course_url: str
    ) -> None:
        """
        Processa um vídeo individual e seus materiais complementares.
        
        Args:
            page: Página do Playwright
            video_element: Elemento do vídeo
            lesson_name: Nome da aula
            lesson_dir: Diretório da aula
            aula_id: ID da aula
            video_index: Índice do vídeo
            course_url: URL do curso (para recuperação)
        """
        file_path = None
        
        try:
            video_title_raw = await video_element.locator(".VideoItem-info-title").text_content()
            video_title = sanitize_filename(video_title_raw)
            
            progress_key = f'{aula_id}-{video_title}-{video_index}'
            
            progress_key = f'{aula_id}-{video_title}-{video_index}'
            
            # Se for baixar vídeo, verifica se j está baixado
            if not self.skip_video and self.is_already_downloaded(progress_key):
                logger.info(f"⏭️  Já baixado: {video_title}")
                # ✅ MELHORIA: Mesmo se vídeo já foi baixado, tenta baixar extras se habilitado
                if self.download_extras:
                    await self._download_video_extras(
                        page, video_element, lesson_name, lesson_dir,
                        aula_id, video_index, video_title
                    )
                return
            
            # Scroll e clique no vídeo (necessário para carregar extras também)
            try:
                await video_element.scroll_into_view_if_needed()
            except Exception:
                await page.evaluate(
                    '(el) => el.scrollIntoView({block: "center", inline: "nearest"});',
                    video_element
                )
            
            await video_element.click()
            logger.info(f"✓ Selecionado: {video_title}")
            
            # Aguarda player carregar (importante pois os extras carregam junto com a aula)
            try:
                await page.wait_for_selector(
                    'video.video-react-video',
                    state='visible',
                    timeout=self.VIDEO_PLAYER_TIMEOUT
                )
            except Exception:
                # Se falhar player, talvez extras ainda estejam disponíveis
                logger.warning("⚠ Player de vídeo demorou a carregar")
            
            await asyncio.sleep(self.PLAYER_LOAD_DELAY)
            
            # ----- INICIO BLOCO DOWNLOAD DE VIDEO -----
            if not self.skip_video:
                # Obtém URL do vídeo
                video_info = await self._get_video_url_by_resolution(page)
                video_url = video_info['url']
                used_resolution = video_info['resolution']
                
                if video_url:
                    # Define nome e caminho
                    file_name = f'{lesson_name} - Vídeo {video_index} {video_title} [{used_resolution}].mp4'
                    file_path = lesson_dir / sanitize_filename(file_name)
                    
                    logger.info(f"⬇️  Baixando vídeo: {file_name}")
                    
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

                    await self.download_with_rate_limit(
                        download_file,
                        video_url,
                        file_path,
                        logger,
                        progress_callback=progress_callback
                    )
                    
                    await verify_download(
                        file_path,
                        logger,
                        expected_extension='.mp4'
                    )
                    
                    self.mark_as_downloaded(progress_key)
                    logger.info(f"✅ Vídeo concluído: {video_title}")
                else:
                    logger.error(f"❌ Não foi possível obter URL para '{video_title}'")
            # ----- FIM BLOCO DOWNLOAD DE VIDEO -----
            
            # ✅ NOVA FUNCIONALIDADE: Baixa materiais extras
            if self.download_extras:
                await self._download_video_extras(
                    page, video_element, lesson_name, lesson_dir,
                    aula_id, video_index, video_title
                )
            
            await asyncio.sleep(self.VIDEO_SELECTION_DELAY)
        
        except asyncio.CancelledError:
            logger.warning("⚠ Download cancelado")
            if file_path and file_path.exists():
                file_path.unlink()
                logger.debug(f"✓ Arquivo parcial removido: {file_path.name}")
            raise
        
        except Exception as e:
            logger.error(f"❌ Falha ao baixar vídeo: {e}")
            
            if file_path and file_path.exists():
                file_path.unlink()
                logger.debug("✓ Arquivo corrompido removido")
            
            try:
                logger.info("🔄 Tentando recuperar recarregando a página...")
                await page.goto(course_url, wait_until='domcontentloaded')
                await asyncio.sleep(2)
            except Exception as recovery_error:
                logger.error(f"❌ Falha na recuperação: {recovery_error}")
    
    # ✅ NOVO MÉTODO: Baixa materiais complementares (Mapas Mentais e Resumos)
    async def _download_video_extras(
        self,
        page: Page,
        video_element: Locator,
        lesson_name: str,
        lesson_dir: Path,
        aula_id: str,
        video_index: int,
        video_title: str
    ) -> None:
        """
        Baixa materiais complementares do vídeo (Mapas Mentais e Resumos).
        
        Args:
            page: Página do Playwright
            video_element: Elemento do vídeo
            lesson_name: Nome da aula
            lesson_dir: Diretório da aula
            aula_id: ID da aula
            video_index: Índice do vídeo
            video_title: Título do vídeo
        """
        try:
            logger.info(f"📚 Buscando materiais complementares de '{video_title}'...")
            
            # Aguarda página carregar completamente após clicar no vídeo
            await asyncio.sleep(self.MATERIAL_CLICK_DELAY)
            
            # ✅ Tenta baixar Mapa Mental
            await self._download_mapa_mental(
                page, lesson_dir, lesson_name, video_index, video_title, aula_id
            )
            
            # ✅ Tenta baixar Resumo
            await self._download_resumo(
                page, lesson_dir, lesson_name, video_index, video_title, aula_id
            )
            
            # ✅ Tenta baixar Slides (se disponível)
            await self._download_slides(
                page, lesson_dir, lesson_name, video_index, video_title, aula_id
            )
        
        except Exception as e:
            logger.warning(f"⚠ Erro ao baixar materiais complementares: {e}")
    
    async def _download_mapa_mental(
        self,
        page: Page,
        lesson_dir: Path,
        lesson_name: str,
        video_index: int,
        video_title: str,
        aula_id: str
    ) -> None:
        """
        Baixa Mapa Mental se disponível.
        
        Args:
            page: Página do Playwright
            lesson_dir: Diretório da aula
            lesson_name: Nome da aula
            video_index: Índice do vídeo
            video_title: Título do vídeo
            aula_id: ID da aula
        """
        try:
            # Procura botão "Baixar Mapa Mental"
            mapa_button = page.locator('button:has-text("Baixar Mapa Mental"), a:has-text("Baixar Mapa Mental")')
            
            if await mapa_button.count() == 0:
                logger.debug(f"   ℹ️  Sem mapa mental para '{video_title}'")
                return
            
            # Verifica se já foi baixado
            progress_key = f'{aula_id}-{video_title}-{video_index}-mapa'
            if self.is_already_downloaded(progress_key):
                logger.info(f"   ⏭️  Mapa mental já baixado")
                return
            
            # Obtém URL do mapa
            mapa_url = await mapa_button.first.get_attribute('href')
            
            if not mapa_url:
                # Se não tem href, pode ser um botão que precisa de click
                logger.debug("   Tentando clicar no botão de mapa mental...")
                await mapa_button.first.click()
                await asyncio.sleep(0.5)
                
                # Tenta encontrar link de download que apareceu
                download_link = page.locator('a[download]').last
                if await download_link.count() > 0:
                    mapa_url = await download_link.get_attribute('href')
            
            if not mapa_url:
                logger.debug(f"   ⚠ Não foi possível obter URL do mapa mental")
                return
            
            # Normaliza URL
            if mapa_url.startswith('/'):
                mapa_url = "https://www.estrategiaconcursos.com.br" + mapa_url
            
            # Define nome do arquivo
            file_name = f'{lesson_name} - Vídeo {video_index} {video_title} - Mapa Mental.pdf'
            file_path = lesson_dir / sanitize_filename(file_name)
            
            logger.info(f"   ⬇️  Baixando mapa mental...")
            
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

            await self.download_with_rate_limit(
                download_file,
                mapa_url,
                file_path,
                logger,
                progress_callback=progress_callback
            )
            
            await verify_download(file_path, logger, expected_extension='.pdf')
            
            self.mark_as_downloaded(progress_key)
            
            logger.info(f"   ✅ Mapa mental baixado")
        
        except Exception as e:
            logger.debug(f"   ⚠ Erro ao baixar mapa mental: {e}")
    
    async def _download_resumo(
        self,
        page: Page,
        lesson_dir: Path,
        lesson_name: str,
        video_index: int,
        video_title: str,
        aula_id: str
    ) -> None:
        """
        Baixa Resumo se disponível.
        
        Args:
            page: Página do Playwright
            lesson_dir: Diretório da aula
            lesson_name: Nome da aula
            video_index: Índice do vídeo
            video_title: Título do vídeo
            aula_id: ID da aula
        """
        try:
            # Procura botão "Baixar Resumo"
            resumo_button = page.locator('button:has-text("Baixar Resumo"), a:has-text("Baixar Resumo")')
            
            if await resumo_button.count() == 0:
                logger.debug(f"   ℹ️  Sem resumo para '{video_title}'")
                return
            
            # Verifica se já foi baixado
            progress_key = f'{aula_id}-{video_title}-{video_index}-resumo'
            if self.is_already_downloaded(progress_key):
                logger.info(f"   ⏭️  Resumo já baixado")
                return
            
            # Obtém URL do resumo
            resumo_url = await resumo_button.first.get_attribute('href')
            
            if not resumo_url:
                logger.debug("   Tentando clicar no botão de resumo...")
                await resumo_button.first.click()
                await asyncio.sleep(0.5)
                
                download_link = page.locator('a[download]').last
                if await download_link.count() > 0:
                    resumo_url = await download_link.get_attribute('href')
            
            if not resumo_url:
                logger.debug(f"   ⚠ Não foi possível obter URL do resumo")
                return
            
            # Normaliza URL
            if resumo_url.startswith('/'):
                resumo_url = "https://www.estrategiaconcursos.com.br" + resumo_url
            
            # Define nome do arquivo
            file_name = f'{lesson_name} - Vídeo {video_index} {video_title} - Resumo.pdf'
            file_path = lesson_dir / sanitize_filename(file_name)
            
            logger.info(f"   ⬇️  Baixando resumo...")
            
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

            await self.download_with_rate_limit(
                download_file,
                resumo_url,
                file_path,
                logger,
                progress_callback=progress_callback
            )
            
            await verify_download(file_path, logger, expected_extension='.pdf')
            
            self.mark_as_downloaded(progress_key)
            
            logger.info(f"   ✅ Resumo baixado")
        
        except Exception as e:
            logger.debug(f"   ⚠ Erro ao baixar resumo: {e}")
    
    async def _download_slides(
        self,
        page: Page,
        lesson_dir: Path,
        lesson_name: str,
        video_index: int,
        video_title: str,
        aula_id: str
    ) -> None:
        """
        Baixa Slides se disponível.
        
        Args:
            page: Página do Playwright
            lesson_dir: Diretório da aula
            lesson_name: Nome da aula
            video_index: Índice do vídeo
            video_title: Título do vídeo
            aula_id: ID da aula
        """
        try:
            # Procura botão "Baixar Slides"
            slides_button = page.locator('button:has-text("Baixar Slides"), a:has-text("Baixar Slides")')
            
            if await slides_button.count() == 0:
                logger.debug(f"   ℹ️  Sem slides para '{video_title}'")
                return
            
            # Verifica se já foi baixado
            progress_key = f'{aula_id}-{video_title}-{video_index}-slides'
            if self.is_already_downloaded(progress_key):
                logger.info(f"   ⏭️  Slides já baixados")
                return
            
            # Obtém URL dos slides
            slides_url = await slides_button.first.get_attribute('href')
            
            if not slides_url:
                logger.debug("   Tentando clicar no botão de slides...")
                await slides_button.first.click()
                await asyncio.sleep(0.5)
                
                download_link = page.locator('a[download]').last
                if await download_link.count() > 0:
                    slides_url = await download_link.get_attribute('href')
            
            if not slides_url:
                logger.debug(f"   ⚠ Não foi possível obter URL dos slides")
                return
            
            # Normaliza URL
            if slides_url.startswith('/'):
                slides_url = "https://www.estrategiaconcursos.com.br" + slides_url
            
            # Define nome do arquivo
            file_name = f'{lesson_name} - Vídeo {video_index} {video_title} - Slides.pdf'
            file_path = lesson_dir / sanitize_filename(file_name)
            
            logger.info(f"   ⬇️  Baixando slides...")
            
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

            await self.download_with_rate_limit(
                download_file,
                slides_url,
                file_path,
                logger,
                progress_callback=progress_callback
            )
            
            await verify_download(file_path, logger, expected_extension='.pdf')
            
            self.mark_as_downloaded(progress_key)
            
            logger.info(f"   ✅ Slides baixados")
        
        except Exception as e:
            logger.debug(f"   ⚠ Erro ao baixar slides: {e}")
    
    async def _get_video_url_by_resolution(self, page: Page) -> dict:
        """
        Obtém URL do vídeo na resolução preferida.
        
        Args:
            page: Página do Playwright
        
        Returns:
            Dict com 'url' e 'resolution'
        """
        try:
            await page.wait_for_selector(
                'video.video-react-video',
                state='visible',
                timeout=self.DEFAULT_ELEMENT_TIMEOUT
            )
            
            await page.evaluate("""() => {
                const v = document.querySelector("video.video-react-video");
                if(v){ v.play(); setTimeout(()=>v.pause(), 1000); }
            }""")
            
            video_player = page.locator('video.video-react-video')
            current_url = await video_player.get_attribute('src')
            
            if self.preferred_resolution == '360p' and '360' in current_url:
                logger.info("✓ Resolução 360p já selecionada")
                return {'url': current_url, 'resolution': '360p'}
            
            try:
                await page.locator('.PlayerControl-button').click()
                await page.wait_for_selector(
                    '.PlayerControl-options',
                    state='visible',
                    timeout=self.QUALITY_MENU_TIMEOUT
                )
            except Exception:
                await page.evaluate("""() => {
                    const btn = document.querySelector('.PlayerControl-button');
                    if (btn) btn.click();
                }""")
                await asyncio.sleep(0.5)
            
            resolution_buttons = await page.locator('.PlayerControlOptions-button').all()
            available_resolutions = {}
            
            for btn in resolution_buttons:
                text = await btn.text_content()
                if text in self.AVAILABLE_RESOLUTIONS:
                    available_resolutions[text] = btn
            
            logger.info(f"✓ Resoluções disponíveis: {list(available_resolutions.keys())}")
            
            for resolution in [self.preferred_resolution] + self.AVAILABLE_RESOLUTIONS:
                if resolution in available_resolutions:
                    logger.info(f"🎯 Selecionando resolução: {resolution}")
                    
                    old_url = await video_player.get_attribute('src')
                    
                    await page.evaluate("""(res) => {
                        const button = Array.from(document.querySelectorAll('.PlayerControlOptions-button'))
                            .find(btn => btn.textContent === res);
                        if (button) button.click();
                    }""", resolution)
                    
                    try:
                        await page.wait_for_function(
                            f'() => document.querySelector("video.video-react-video").src !== "{old_url}"',
                            timeout=self.RESOLUTION_CHANGE_TIMEOUT
                        )
                        logger.info("✓ URL do vídeo atualizada")
                    except PlaywrightTimeoutError:
                        logger.warning(f"⚠ URL não mudou após selecionar {resolution}")
                    
                    new_url = await video_player.get_attribute('src')
                    
                    if resolution == '720p' and ('360' in new_url or '480' in new_url):
                        logger.warning("⚠ Resolução incorreta detectada. Tentando forçar...")
                        forced_url = await self._force_resolution(new_url, '720')
                        if forced_url:
                            return {'url': forced_url, 'resolution': '720p'}
                    
                    return {'url': new_url, 'resolution': resolution}
            
            logger.warning("⚠ Usando resolução padrão")
            return {'url': current_url, 'resolution': 'padrão'}
        
        except Exception as e:
            logger.error(f"❌ Erro ao obter URL do vídeo: {e}")
            try:
                current_url = await page.locator('video.video-react-video').get_attribute('src')
                return {'url': current_url, 'resolution': 'padrão'}
            except:
                return {'url': None, 'resolution': 'erro'}
    
    async def _force_resolution(self, url: str, resolution: str) -> str:
        """
        Tenta forçar uma resolução modificando a URL.
        
        Args:
            url: URL original
            resolution: Resolução desejada (ex: '720')
        
        Returns:
            URL forçada se válida, None caso contrário
        """
        forced_url = re.sub(r"/(360|480)/", f"/{resolution}/", url)
        
        try:
            timeout_config = aiohttp.ClientTimeout(total=10, connect=5)
            connector = aiohttp.TCPConnector(limit_per_host=2)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout_config
            ) as session:
                async with session.get(forced_url) as resp:
                    if resp.status == 200:
                        logger.info(f"✓ Forçado para {resolution}p com sucesso")
                        return forced_url
        
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"⚠ Não foi possível validar {resolution}p: {e}")
        
        except Exception as e:
            logger.debug(f"Erro ao forçar resolução: {e}")
        
        return None
