"""
Módulo de Autenticação - VERSÃO CORRIGIDA
Parte 2/5 da refatoração
"""
import logging
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class AuthManager:
    """Gerencia autenticação na plataforma Estratégia Concursos"""
    
    LOGIN_URL = 'https://www.estrategiaconcursos.com.br/app/auth/login'
    DASHBOARD_URL = 'https://www.estrategiaconcursos.com.br/app/dashboard/assinaturas'
    
    # ✅ NOVAS CONSTANTES: Timeouts configuráveis
    PAGE_LOAD_TIMEOUT = 60000      # ms
    ELEMENT_WAIT_TIMEOUT = 30000   # ms
    LOGIN_CONFIRM_TIMEOUT = 60000  # ms
    NAVIGATION_TIMEOUT = 30000     # ms
    
    def __init__(self, email: str, password: str):
        """
        Inicializa o gerenciador de autenticação.
        
        Args:
            email: Email do usuário
            password: Senha do usuário
        
        Raises:
            ValueError: Se email ou senha estiverem vazios
        """
        if not email or not password:
            raise ValueError("Email e senha são obrigatórios")
        
        self.email = email
        self.password = password
    
    async def ensure_logged_in(self, page: Page) -> bool:
        """
        Garante que o usuário está logado na plataforma.
        
        Args:
            page: Página do Playwright
        
        Returns:
            True se login bem-sucedido
        
        Raises:
            Exception: Se falhar o login
        """
        logger.info("🔐 Verificando estado de autenticação...")
        
        try:
            await page.goto(
                self.LOGIN_URL,
                wait_until='domcontentloaded',
                timeout=self.PAGE_LOAD_TIMEOUT
            )
            
            # Verifica se já está logado
            if await self._is_logged_in(page):
                logger.info("✓ Sessão ativa detectada")
                await self._navigate_to_catalog(page)
                return True
            
            # Realiza login
            logger.info("Realizando login...")
            await self._perform_login(page)
            
            # Navega para o catálogo
            await self._navigate_to_catalog(page)
            
            logger.info("✓ Login realizado com sucesso!")
            return True
        
        # ✅ CORREÇÃO: Tratamento de erro mais específico
        except PlaywrightTimeoutError as e:
            logger.error(f"❌ Timeout durante autenticação: {e}")
            raise Exception(
                "Timeout ao acessar plataforma. Verifique sua conexão com internet."
            )
        
        except ValueError as e:
            logger.error(f"❌ Erro de validação: {e}")
            raise
        
        except Exception as e:
            logger.error(f"❌ Falha na autenticação: {e}", exc_info=True)
            raise Exception(
                "Não foi possível fazer login. Verifique suas credenciais e tente novamente."
            )
    
    async def _is_logged_in(self, page: Page) -> bool:
        """
        Verifica se já está logado procurando por elementos da dashboard.
        
        Args:
            page: Página do Playwright
        
        Returns:
            True se já está logado
        """
        try:
            await page.wait_for_selector(
                'a:has-text("Catálogo de Cursos")',
                timeout=5000
            )
            return True
        
        except PlaywrightTimeoutError:
            return False
        
        except Exception as e:
            logger.debug(f"Erro ao verificar login: {e}")
            return False
    
    async def _perform_login(self, page: Page) -> None:
        """
        Executa o processo de login preenchendo formulário.
        
        Args:
            page: Página do Playwright
        
        Raises:
            Exception: Se o login falhar
        """
        try:
            # Aguarda e preenche campo de email
            logger.debug("Aguardando campo de email...")
            await page.wait_for_selector(
                'input[name="loginField"]',
                state='visible',
                timeout=self.ELEMENT_WAIT_TIMEOUT
            )
            
            await page.fill('input[name="loginField"]', self.email)
            logger.info(f"✓ Email preenchido: {self.email}")
            
            # Aguarda e preenche campo de senha
            logger.debug("Aguardando campo de senha...")
            await page.wait_for_selector(
                'input[name="passwordField"]',
                state='visible',
                timeout=self.ELEMENT_WAIT_TIMEOUT
            )
            
            await page.fill('input[name="passwordField"]', self.password)
            logger.info("✓ Senha preenchida")
            
            # Clica no botão de submit
            logger.debug("Enviando formulário...")
            await page.click('button[type="submit"]')
            logger.info("✓ Formulário enviado")
            
            # Aguarda confirmação de login bem-sucedido
            logger.debug("Aguardando confirmação de login...")
            await page.wait_for_selector(
                'a:has-text("Catálogo de Cursos")',
                timeout=self.LOGIN_CONFIRM_TIMEOUT
            )
            logger.info("✓ Login confirmado")
        
        # ✅ CORREÇÃO: Tratamento de erro mais específico
        except PlaywrightTimeoutError as e:
            logger.error(f"❌ Timeout durante login: {e}")
            
            # ✅ MELHORIA: Verifica se há mensagem de erro na página
            try:
                error_message = await page.locator('.error, .alert-danger').text_content()
                if error_message:
                    raise Exception(f"Erro de login: {error_message}")
            except:
                pass
            
            raise Exception(
                "Timeout durante o processo de login. "
                "Verifique suas credenciais e tente novamente."
            )
        
        except Exception as e:
            logger.error(f"❌ Erro durante login: {e}")
            raise Exception(f"Falha ao fazer login: {e}")
    
    async def _navigate_to_catalog(self, page: Page) -> None:
        """
        Navega para o catálogo de cursos após login.
        Lida com diferentes redirecionamentos pós-login.
        
        Args:
            page: Página do Playwright
        
        Raises:
            Exception: Se falhar a navegação
        """
        try:
            current_url = page.url
            logger.debug(f"URL atual: {current_url}")
            
            # Cenário 1: Foi redirecionado para a página de perfil
            if "perfil.estrategia.com" in current_url:
                logger.info("⚠ Redirecionado para perfil. Navegando para catálogo...")
                await page.goto(
                    self.DASHBOARD_URL,
                    wait_until='domcontentloaded',
                    timeout=self.PAGE_LOAD_TIMEOUT
                )
                current_url = page.url
                logger.info("✓ Navegação para catálogo concluída")
            
            # Cenário 2: Está no dashboard genérico (não no catálogo)
            if "/app/dashboard/cursos" in current_url and "assinaturas" not in current_url:
                logger.info("⚠ No dashboard genérico. Clicando em 'Catálogo de Cursos'...")
                
                # ✅ MELHORIA: Tenta múltiplas formas de acessar catálogo
                try:
                    await page.locator('a:has-text("Catálogo de Cursos")').click()
                    await page.wait_for_url(
                        "**/app/dashboard/assinaturas",
                        timeout=self.NAVIGATION_TIMEOUT
                    )
                except PlaywrightTimeoutError:
                    # Fallback: navega diretamente
                    logger.debug("Click falhou, navegando diretamente...")
                    await page.goto(
                        self.DASHBOARD_URL,
                        wait_until='domcontentloaded',
                        timeout=self.PAGE_LOAD_TIMEOUT
                    )
                
                logger.info("✓ Catálogo de cursos acessado")
            
            logger.info("✓ Navegação pós-login concluída com sucesso")
        
        # ✅ CORREÇÃO: Tratamento de erro mais específico
        except PlaywrightTimeoutError as e:
            logger.error(f"❌ Timeout ao navegar para catálogo: {e}")
            raise Exception("Timeout ao acessar catálogo de cursos")
        
        except Exception as e:
            logger.error(f"❌ Erro ao navegar para catálogo: {e}")
            raise Exception(f"Falha ao acessar catálogo de cursos: {e}")
    
    # ✅ NOVA FUNCIONALIDADE: Logout
    async def logout(self, page: Page) -> bool:
        """
        Realiza logout da plataforma.
        
        Args:
            page: Página do Playwright
        
        Returns:
            True se logout bem-sucedido
        """
        try:
            logger.info("🔓 Realizando logout...")
            
            # Procura botão de logout
            logout_button = page.locator('button:has-text("Sair"), a:has-text("Sair")')
            
            if await logout_button.count() > 0:
                await logout_button.first.click()
                logger.info("✓ Logout realizado")
                return True
            else:
                logger.warning("⚠ Botão de logout não encontrado")
                return False
        
        except Exception as e:
            logger.error(f"❌ Erro ao fazer logout: {e}")
            return False
