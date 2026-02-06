"""
Gerenciador de Configurações com Segurança Aprimorada - VERSÃO EXPANDIDA
Inclui opção para baixar materiais complementares
Parte 1/5 da refatoração
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet, InvalidToken
import keyring
from keyring.errors import KeyringError
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Gerencia configurações com criptografia de senha"""
    
    SERVICE_NAME = "EstrategiaDownloader"
    CONFIG_FILE = Path("config.json")
    KEY_FILE = Path(".key")
    
    def __init__(self):
        """Inicializa o gerenciador de configurações"""
        self.config = self._load_config()
        self.cipher = self._get_cipher()
    
    def _get_cipher(self) -> Fernet:
        """
        Obtém ou cria chave de criptografia.
        
        Returns:
            Cipher Fernet para criptografia
        """
        try:
            if self.KEY_FILE.exists():
                key = self.KEY_FILE.read_bytes()
                logger.debug("✓ Chave de criptografia carregada")
            else:
                key = Fernet.generate_key()
                self.KEY_FILE.write_bytes(key)
                logger.info("✓ Nova chave de criptografia gerada")
                
                # Torna o arquivo oculto no Windows
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(str(self.KEY_FILE), 2)
                    logger.debug("✓ Arquivo de chave marcado como oculto")
                except (AttributeError, OSError):
                    pass
            
            return Fernet(key)
        
        except (OSError, IOError) as e:
            logger.error(f"❌ Erro ao gerenciar arquivo de chave: {e}")
            raise Exception(f"Não foi possível acessar chave de criptografia: {e}")
        
        except Exception as e:
            logger.critical(f"❌ Erro crítico ao inicializar criptografia: {e}", exc_info=True)
            raise
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Carrega configurações do arquivo.
        
        Returns:
            Dicionário de configurações
        """
        try:
            if self.CONFIG_FILE.exists():
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info("✓ Configurações carregadas")
                    return config
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Arquivo de configuração corrompido: {e}")
            logger.info("⚠ Usando configurações padrão")
        
        except (OSError, IOError) as e:
            logger.error(f"❌ Erro ao ler arquivo de configuração: {e}")
            logger.info("⚠ Usando configurações padrão")
        
        except Exception as e:
            logger.critical(f"❌ Erro inesperado ao carregar config: {e}", exc_info=True)
        
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Retorna configuração padrão.
        
        Returns:
            Dicionário com configurações padrão
        """
        return {
            "email": "",
            "downloadType": "pdf",
            "headless": False,
            "pdfConfig": {
                "pastaDownloads": str(Path.home() / "Downloads" / "Estrategia_PDFs"),
                "pdfType": 2,
                "baixarExtrasComPdf": False  # ✅ NOVO: Opção para baixar extras junto com PDFs
            },
            "videoConfig": {
                "pastaDownloads": str(Path.home() / "Downloads" / "Estrategia_Videos"),
                "resolucaoEscolhida": "720p",
                "baixarExtras": True  # ✅ NOVO: Baixar mapas mentais e resumos
            }
        }
    
    def save_config(self) -> None:
        """
        Salva configurações no arquivo.
        
        Raises:
            Exception: Se falhar ao salvar
        """
        try:
            if self.CONFIG_FILE.exists():
                backup_path = self.CONFIG_FILE.with_suffix('.json.bak')
                self.CONFIG_FILE.replace(backup_path)
            
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            logger.info("✓ Configurações salvas com sucesso")
        
        except (OSError, IOError) as e:
            logger.error(f"❌ Erro ao salvar configurações: {e}")
            raise Exception(f"Não foi possível salvar configurações: {e}")
        
        except Exception as e:
            logger.critical(f"❌ Erro crítico ao salvar config: {e}", exc_info=True)
            raise
    
    def get_password(self) -> Optional[str]:
        """
        Obtém senha do keyring de forma segura.
        
        Returns:
            Senha descriptografada ou None se não encontrada
        """
        email = self.config.get("email")
        if not email:
            logger.debug("⚠ Email não configurado, não há senha para recuperar")
            return None
        
        try:
            encrypted = keyring.get_password(self.SERVICE_NAME, email)
            if not encrypted:
                logger.debug("⚠ Senha não encontrada no keyring")
                return None
            
            decrypted = self.cipher.decrypt(encrypted.encode()).decode()
            logger.debug("✓ Senha recuperada do keyring")
            return decrypted
        
        except InvalidToken:
            logger.error("❌ Senha corrompida ou chave de criptografia alterada")
            logger.info("💡 Você precisará reconfigurar sua senha")
            return None
        
        except KeyringError as e:
            logger.error(f"❌ Erro ao acessar keyring do sistema: {e}")
            return None
        
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao obter senha: {e}", exc_info=True)
            return None
    
    def set_password(self, password: str) -> None:
        """
        Salva senha no keyring de forma criptografada.
        
        Args:
            password: Senha a ser salva
        
        Raises:
            ValueError: Se email não estiver configurado
            Exception: Se falhar ao salvar
        """
        email = self.config.get("email")
        if not email:
            raise ValueError("Email não configurado. Configure o email antes de definir a senha.")
        
        if not password:
            raise ValueError("Senha não pode estar vazia")
        
        try:
            encrypted = self.cipher.encrypt(password.encode()).decode()
            keyring.set_password(self.SERVICE_NAME, email, encrypted)
            logger.info("✓ Senha salva com segurança no keyring")
        
        except KeyringError as e:
            logger.error(f"❌ Erro ao salvar senha no keyring: {e}")
            raise Exception(f"Não foi possível salvar senha no sistema: {e}")
        
        except Exception as e:
            logger.error(f"❌ Erro ao criptografar/salvar senha: {e}", exc_info=True)
            raise Exception(f"Falha ao salvar senha: {e}")
    
    def delete_password(self) -> None:
        """Remove senha do keyring"""
        email = self.config.get("email")
        if not email:
            return
        
        try:
            keyring.delete_password(self.SERVICE_NAME, email)
            logger.info("✓ Senha removida do keyring")
        except KeyringError:
            pass
        except Exception as e:
            logger.warning(f"⚠ Erro ao remover senha: {e}")
    
    def get(self, *keys, default=None) -> Any:
        """
        Obtém valor aninhado do config.
        
        Args:
            *keys: Sequência de chaves para navegar no dicionário
            default: Valor padrão se chave não existir
        
        Returns:
            Valor encontrado ou default
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value
    
    def set(self, *keys, value: Any) -> None:
        """
        Define valor aninhado no config.
        
        Args:
            *keys: Sequência de chaves, última é onde o valor será definido
            value: Valor a ser definido
        """
        if not keys:
            logger.warning("⚠ Tentativa de set() sem chaves")
            return
        
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            elif not isinstance(config[key], dict):
                logger.warning(f"⚠ Sobrescrevendo valor não-dict em '{key}'")
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Valida se configurações estão corretas.
        
        Returns:
            Tupla (é_válido, lista_de_erros)
        """
        errors = []
        
        # Valida email
        email = self.config.get("email")
        if not email:
            errors.append("Email não configurado")
        elif "@" not in email:
            errors.append("Email inválido")
        
        # Valida senha
        if not self.get_password():
            errors.append("Senha não configurada")
        
        # Valida tipo de download
        download_type = self.config.get("downloadType")
        if download_type not in ["pdf", "video"]:
            errors.append(f"Tipo de download inválido: {download_type}")
        
        # Valida pasta de PDFs
        pdf_folder = self.get("pdfConfig", "pastaDownloads")
        if pdf_folder:
            try:
                pdf_path = Path(pdf_folder)
                pdf_path.mkdir(parents=True, exist_ok=True)
                if not pdf_path.is_dir():
                    errors.append(f"Pasta de PDFs inválida: {pdf_path}")
                elif not os.access(pdf_path, os.W_OK):
                    errors.append(f"Sem permissão de escrita na pasta de PDFs: {pdf_path}")
            except Exception:
                errors.append("Caminho de pasta de PDFs inválido")
        
        # Valida pasta de vídeos
        video_folder = self.get("videoConfig", "pastaDownloads")
        if video_folder:
            try:
                video_path = Path(video_folder)
                video_path.mkdir(parents=True, exist_ok=True)
                if not video_path.is_dir():
                    errors.append(f"Pasta de vídeos inválida: {video_path}")
                elif not os.access(video_path, os.W_OK):
                    errors.append(f"Sem permissão de escrita na pasta de vídeos: {video_path}")
            except Exception:
                errors.append("Caminho de pasta de vídeos inválido")
        
        return len(errors) == 0, errors


class ProgressManager:
    """Gerencia progresso de downloads"""
    
    PROGRESS_FILE = Path("progress.json")
    
    def __init__(self):
        """Inicializa o gerenciador de progresso"""
        self.progress = self._load_progress()
    
    def _load_progress(self) -> Dict[str, bool]:
        """
        Carrega progresso do arquivo.
        
        Returns:
            Dicionário de progresso
        """
        try:
            if self.PROGRESS_FILE.exists():
                with open(self.PROGRESS_FILE, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                    logger.info(f"✓ Progresso carregado ({len(progress)} itens)")
                    return progress
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Arquivo de progresso corrompido: {e}")
            logger.info("⚠ Iniciando com progresso vazio")
        
        except (OSError, IOError) as e:
            logger.error(f"❌ Erro ao ler progresso: {e}")
        
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao carregar progresso: {e}", exc_info=True)
        
        return {}
    
    def save_progress(self) -> None:
        """Salva progresso no arquivo"""
        try:
            temp_file = self.PROGRESS_FILE.with_suffix('.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, indent=2)
            
            temp_file.replace(self.PROGRESS_FILE)
            
            logger.debug(f"✓ Progresso salvo ({len(self.progress)} itens)")
        
        except (OSError, IOError) as e:
            logger.error(f"❌ Erro ao salvar progresso: {e}")
        
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao salvar progresso: {e}", exc_info=True)
    
    def is_completed(self, key: str) -> bool:
        """
        Verifica se item já foi baixado.
        
        Args:
            key: Chave única do item
        
        Returns:
            True se já foi baixado
        """
        return self.progress.get(key, False)
    
    def mark_completed(self, key: str) -> None:
        """
        Marca item como baixado.
        
        Args:
            key: Chave única do item
        """
        self.progress[key] = True
        self.save_progress()
    
    def clear(self) -> None:
        """Limpa todo o progresso"""
        self.progress = {}
        self.save_progress()
        logger.info("✓ Progresso limpo")
    
    def get_stats(self) -> dict:
        """
        Obtém estatísticas de progresso.
        
        Returns:
            Dicionário com estatísticas
        """
        return {
            "total_items": len(self.progress),
            "completed": sum(1 for v in self.progress.values() if v)
        }


class CourseUrlManager:
    """Gerencia URLs de cursos com validação"""
    
    URLS_FILE = Path("course-urls.json")
    
    def __init__(self):
        """Inicializa o gerenciador de URLs"""
        self.urls = self._load_urls()
    
    def _load_urls(self) -> list:
        """
        Carrega URLs do arquivo.
        
        Returns:
            Lista de URLs
        """
        try:
            if self.URLS_FILE.exists():
                with open(self.URLS_FILE, 'r', encoding='utf-8') as f:
                    urls = json.load(f)
                    logger.info(f"✓ {len(urls)} URL(s) de curso carregada(s)")
                    return urls
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Arquivo de URLs corrompido: {e}")
        
        except (OSError, IOError) as e:
            logger.error(f"❌ Erro ao ler URLs: {e}")
        
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao carregar URLs: {e}", exc_info=True)
        
        return []
    
    def save_urls(self) -> None:
        """Salva URLs no arquivo"""
        try:
            with open(self.URLS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.urls, f, indent=2, ensure_ascii=False)
            logger.debug(f"✓ {len(self.urls)} URL(s) salva(s)")
        
        except (OSError, IOError) as e:
            logger.error(f"❌ Erro ao salvar URLs: {e}")
        
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao salvar URLs: {e}", exc_info=True)
    
    def add_url(self, url: str) -> bool:
        """
        Adiciona URL se válida e não duplicada.
        
        Args:
            url: URL do curso
        
        Returns:
            True se adicionada com sucesso
        """
        url = url.strip()
        
        if not self._validate_url(url):
            logger.warning(f"⚠ URL inválida: {url}")
            return False
        
        if url in self.urls:
            logger.info("⚠ URL já existe na lista")
            return False
        
        self.urls.append(url)
        self.save_urls()
        logger.info(f"✓ URL adicionada: {url}")
        return True
    
    def remove_url(self, url: str) -> bool:
        """
        Remove URL da lista.
        
        Args:
            url: URL a ser removida
        
        Returns:
            True se removida com sucesso
        """
        if url in self.urls:
            self.urls.remove(url)
            self.save_urls()
            logger.info(f"✓ URL removida: {url}")
            return True
        
        logger.warning("⚠ URL não encontrada na lista")
        return False
    
    def get_all(self) -> list:
        """
        Retorna todas as URLs.
        
        Returns:
            Cópia da lista de URLs
        """
        return self.urls.copy()
    
    def clear(self) -> None:
        """Remove todas as URLs"""
        self.urls = []
        self.save_urls()
        logger.info("✓ Lista de URLs limpa")
    
    @staticmethod
    def _validate_url(url: str) -> bool:
        """
        Valida se URL é do domínio correto.
        
        Args:
            url: URL a ser validada
        
        Returns:
            True se válida
        """
        from urllib.parse import urlparse
        
        try:
            result = urlparse(url)
            
            if result.scheme not in ['http', 'https']:
                return False
            
            if 'estrategiaconcursos.com.br' not in result.netloc:
                return False
            
            if '/cursos/' not in result.path:
                return False
            
            if not result.path.endswith('/aulas'):
                logger.warning("⚠ URL deve terminar com '/aulas'")
                return False
            
            return True
        
        except Exception as e:
            logger.debug(f"Erro ao validar URL: {e}")
            return False
