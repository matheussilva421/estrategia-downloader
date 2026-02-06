"""
Utilitários e Funções Auxiliares - VERSÃO CORRIGIDA
Parte 1/5 da refatoração
"""
import re
import logging
from pathlib import Path
from typing import Optional, Literal
import aiohttp
import asyncio
import queue

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, max_length: int = 80) -> str:
    """
    Remove caracteres inválidos e limita comprimento do nome.
    
    Args:
        filename: Nome do arquivo a ser sanitizado
        max_length: Comprimento máximo do nome
    
    Returns:
        Nome de arquivo sanitizado
    """
    # Remove caracteres inválidos para Windows
    sanitized = ''.join('_' if c in '<>:"/\\|?*' else c for c in filename)
    
    # Normaliza espaços
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    # Limita tamanho do nome
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rsplit(' ', 1)[0]
        return sanitized.strip('. ')
    
    return sanitized


def extract_materia_name(course_name: str) -> str:
    """
    Extrai nome da matéria do título completo do curso.
    
    Args:
        course_name: Nome completo do curso
    
    Returns:
        Nome da matéria extraído
    """
    if 'Conhecimentos Regionais' in course_name:
        return 'Conhecimentos Regionais'
    
    materia = course_name
    
    # Remove prefixos comuns
    patterns = [
        r'^Concursos da Área Fiscal\s*-\s*',
        r'Curso (Completo|Básico) de ',
        r'\(Profs?\.?[\w\s,]+\)',
        r'\s*-\s*\d{4}(?!\d)',
        r'\s*\(Pós-Edital\)',
        r'Prefeitura [\w\s-]+?-',
        r'\([^)]+\)',
        r' - Área Administrativa',
        r'Noções de ',
        r'^\s*-\s*|\s*-\s*$'
    ]
    
    for pattern in patterns:
        materia = re.sub(pattern, '', materia, flags=re.IGNORECASE)
    
    materia = materia.strip()
    
    # Remove texto após dois pontos
    if ':' in materia:
        materia = materia.split(':')[1].strip()
    
    return materia or 'Matéria Desconhecida'


async def download_file(
    url: str,
    file_path: Path,
    logger: logging.Logger,
    retries: int = 3,
    chunk_size: int = 8192,
    timeout: int = 300,
    progress_callback=None  # ✅ Callback de progresso
) -> None:
    """
    Faz download de arquivo com retries e backoff exponencial.
    
    Args:
        url: URL do arquivo
        file_path: Caminho onde salvar o arquivo
        logger: Logger para mensagens
        retries: Número de tentativas
        chunk_size: Tamanho dos chunks de download
        timeout: Timeout total em segundos
        progress_callback: Função chamada com (downloaded_bytes, total_bytes, speed)
    """
    import time
    
    for attempt in range(1, retries + 1):
        try:
            # Garante que a pasta existe
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ✅ CORREÇÃO: Configuração de timeout mais robusta
            timeout_config = aiohttp.ClientTimeout(
                total=timeout,
                connect=30,      # Timeout de conexão
                sock_read=60     # Timeout de leitura do socket
            )
            
            # ✅ CORREÇÃO: Connector com limite de conexões
            connector = aiohttp.TCPConnector(
                limit_per_host=5,
                force_close=True
            )
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout_config
            ) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Status HTTP inválido: {response.status}")
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    start_time = time.time()
                    last_update = 0
                    
                    # ✅ MELHORIA: Download com arquivo temporário
                    temp_path = file_path.with_suffix('.tmp')
                    
                    try:
                        with open(temp_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(chunk_size):
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                # Atualiza progresso
                                current_time = time.time()
                                if progress_callback and (current_time - last_update > 0.5 or downloaded == total_size):
                                    elapsed = current_time - start_time
                                    speed = downloaded / elapsed if elapsed > 0 else 0
                                    progress_callback(downloaded, total_size, speed)
                                    last_update = current_time
                        
                        # Move arquivo temporário para final
                        temp_path.replace(file_path)
                        
                    except Exception as e:
                        # Remove arquivo temporário em caso de erro
                        if temp_path.exists():
                            temp_path.unlink()
                        raise e
            
            logger.info(f"✓ Baixado: {file_path.name}")
            return
            
        except asyncio.CancelledError:
            logger.warning("Download cancelado pelo usuário")
            # Remove arquivo parcial
            if file_path.exists():
                file_path.unlink()
            raise
        
        # ✅ CORREÇÃO: Exceções mais específicas
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.error(f"Tentativa {attempt}/{retries} falhou: {e}")
            
            # Remove arquivo corrompido
            if file_path.exists():
                file_path.unlink()
            
            if attempt < retries:
                wait_time = 2 ** attempt
                logger.info(f"Aguardando {wait_time}s antes de tentar novamente...")
                await asyncio.sleep(wait_time)
            else:
                raise Exception(f"Falha ao baixar {url} após {retries} tentativas: {e}")
        
        except Exception as e:
            logger.error(f"Erro inesperado no download: {e}", exc_info=True)
            if file_path.exists():
                file_path.unlink()
            raise


async def verify_download(
    file_path: Path,
    logger: logging.Logger,
    min_size: int = 1024,
    expected_extension: Optional[Literal['.pdf', '.mp4']] = None
) -> bool:
    """
    Verifica se o download foi bem-sucedido.
    
    Args:
        file_path: Caminho do arquivo
        logger: Logger para mensagens
        min_size: Tamanho mínimo esperado em bytes
        expected_extension: Extensão esperada para validação de magic bytes
    
    Returns:
        True se arquivo é válido
    
    Raises:
        FileNotFoundError: Se arquivo não existe
        ValueError: Se arquivo está vazio, muito pequeno ou corrompido
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    
    size = file_path.stat().st_size
    
    if size == 0:
        raise ValueError(f"Arquivo vazio: {file_path}")
    
    if size < min_size:
        raise ValueError(
            f"Arquivo muito pequeno: {file_path.name} ({size} bytes, esperado >= {min_size})"
        )
    
    # ✅ NOVA FUNCIONALIDADE: Validação de magic bytes
    if expected_extension:
        try:
            with open(file_path, 'rb') as f:
                if expected_extension == '.pdf':
                    header = f.read(4)
                    if header != b'%PDF':
                        raise ValueError(f"Arquivo não é PDF válido: {file_path.name}")
                
                elif expected_extension == '.mp4':
                    # Verifica assinatura MP4
                    f.seek(4)
                    ftyp = f.read(4)
                    if ftyp not in [b'ftyp', b'mdat', b'moov', b'wide', b'free']:
                        raise ValueError(f"Arquivo não é MP4 válido: {file_path.name}")
        
        except (OSError, IOError) as e:
            raise ValueError(f"Erro ao validar arquivo {file_path.name}: {e}")
    
    logger.info(f"✓ Verificado: {file_path.name} ({format_bytes(size)})")
    return True


def format_bytes(size: int) -> str:
    """
    Formata tamanho em bytes para formato legível.
    
    Args:
        size: Tamanho em bytes
    
    Returns:
        String formatada (ex: "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


class QueueHandler(logging.Handler):
    """
    Handler de log que envia mensagens para uma fila de forma não-bloqueante
    """
    
    def __init__(self, log_queue: queue.Queue, max_queue_size: int = 1000):
        """
        Inicializa o handler.
        
        Args:
            log_queue: Fila para enviar mensagens
            max_queue_size: Tamanho máximo da fila
        """
        super().__init__()
        self.log_queue = log_queue
        self.max_queue_size = max_queue_size
        self.dropped_messages = 0
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emite log para a fila de forma não-bloqueante.
        
        Args:
            record: Registro de log
        """
        try:
            # ✅ CORREÇÃO: Envia dicionário estruturado ao invés de string simples
            log_entry = {
                "type": "log",
                "level": record.levelname,
                "message": self.format(record),
                "timestamp": record.created
            }
            self.log_queue.put_nowait(log_entry)
            
        except queue.Full:
            # ✅ MELHORIA: Conta mensagens descartadas
            self.dropped_messages += 1
            
            # Alerta a cada 100 mensagens descartadas
            if self.dropped_messages % 100 == 0:
                try:
                    # Tenta esvaziar um pouco a fila
                    for _ in range(10):
                        try:
                            self.log_queue.get_nowait()
                        except queue.Empty:
                            break
                    
                    # Tenta adicionar mensagem de alerta
                    self.log_queue.put_nowait(
                        f"⚠ {self.dropped_messages} mensagens de log foram descartadas (fila cheia)"
                    )
                except:
                    pass
        
        except Exception:
            self.handleError(record)


class PrintRedirector:
    """Redireciona print() para o logger"""
    
    def __init__(self, logger_instance: logging.Logger):
        """
        Inicializa o redirecionador.
        
        Args:
            logger_instance: Instância do logger
        """
        self.logger = logger_instance
        self.buffer = []
    
    def write(self, message: str) -> None:
        """
        Escreve mensagem no logger.
        
        Args:
            message: Mensagem a ser escrita
        """
        if message.strip():
            self.logger.info(message.strip())
    
    def flush(self) -> None:
        """Flush do buffer (compatibilidade)"""
        pass


def setup_logger(
    name: str,
    log_queue: Optional[queue.Queue] = None,
    level: int = logging.INFO
) -> logging.Logger:
    """
    Configura logger com formatação e handlers apropriados.
    
    Args:
        name: Nome do logger
        log_queue: Fila para enviar mensagens (opcional)
        level: Nível de log
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    # ✅ CORREÇÃO: Previne configuração duplicada e propagação
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    logger.propagate = False  # ✅ Previne duplicação em hierarquia
    
    # Formatter comum
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Handler para arquivo
    try:
        file_handler = logging.FileHandler('downloader.log', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (OSError, IOError) as e:
        # Se não conseguir criar arquivo de log, continua sem ele
        print(f"⚠ Não foi possível criar arquivo de log: {e}")
    
    # Handler para fila (se fornecido)
    if log_queue:
        queue_handler = QueueHandler(log_queue)
        queue_handler.setFormatter(formatter)
        logger.addHandler(queue_handler)
    
    return logger


# ✅ NOVA CLASSE: Métricas de performance
class DownloadMetrics:
    """Rastreia métricas de download para estatísticas"""
    
    def __init__(self):
        """Inicializa as métricas"""
        import time
        self.start_time = time.time()
        self.files_downloaded = 0
        self.bytes_downloaded = 0
        self.files_failed = 0
        self.files_skipped = 0
    
    def add_download(self, size_bytes: int) -> None:
        """
        Adiciona download bem-sucedido.
        
        Args:
            size_bytes: Tamanho do arquivo em bytes
        """
        self.files_downloaded += 1
        self.bytes_downloaded += size_bytes
    
    def add_failure(self) -> None:
        """Adiciona falha de download"""
        self.files_failed += 1
    
    def add_skip(self) -> None:
        """Adiciona arquivo pulado (já baixado)"""
        self.files_skipped += 1
    
    def get_stats(self) -> dict:
        """
        Obtém estatísticas de download.
        
        Returns:
            Dicionário com estatísticas
        """
        import time
        elapsed = time.time() - self.start_time
        
        speed_mbps = (
            self.bytes_downloaded / elapsed / 1024 / 1024
            if elapsed > 0 else 0
        )
        
        return {
            "duration": f"{elapsed:.1f}s",
            "files_ok": self.files_downloaded,
            "files_failed": self.files_failed,
            "files_skipped": self.files_skipped,
            "total_size": format_bytes(self.bytes_downloaded),
            "speed": f"{speed_mbps:.2f} MB/s"
        }
    
    def log_stats(self, logger: logging.Logger) -> None:
        """
        Loga estatísticas.
        
        Args:
            logger: Logger para output
        """
        stats = self.get_stats()
        logger.info("=" * 70)
        logger.info("📊 ESTATÍSTICAS DE DOWNLOAD")
        logger.info("=" * 70)
        logger.info(f"⏱️  Duração: {stats['duration']}")
        logger.info(f"✅ Arquivos baixados: {stats['files_ok']}")
        logger.info(f"⏭️  Arquivos pulados: {stats['files_skipped']}")
        logger.info(f"❌ Arquivos com falha: {stats['files_failed']}")
        logger.info(f"📦 Tamanho total: {stats['total_size']}")
        logger.info(f"⚡ Velocidade média: {stats['speed']}")
        logger.info("=" * 70)
