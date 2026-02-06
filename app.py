"""
Interface Gráfica Principal - Estratégia Downloader Pro v3.1 - Powered by Perplexity - VERSÃO FINAL
Inclui controle de materiais complementares
Parte 5/5 da refatoração (FINAL)
"""
import customtkinter as ctk
from customtkinter import filedialog
import asyncio
import threading
import queue
from pathlib import Path
import sys
import logging

from config_manager import ConfigManager, CourseUrlManager
from downloader import DownloadManager

logger = logging.getLogger(__name__)


class StrategyDownloaderApp(ctk.CTk):
    """Aplicação principal com interface gráfica moderna"""
    
    LOG_PROCESS_INTERVAL = 100  # ms
    MAX_LOG_LINES = 1000        # Máximo de linhas no log
    
    def __init__(self):
        super().__init__()
        
        # Configurações da janela
        self.title("🦉 Estratégia Downloader Pro v3.1 - Powered by Perplexity")
        self.geometry("1200x750")
        self.minsize(900, 650)
        
        # Tema
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Gerenciadores
        self.config_manager = ConfigManager()
        self.url_manager = CourseUrlManager()
        self.log_queue = queue.Queue(maxsize=1000)
        self.download_manager = None
        self.download_thread = None
        
        self._is_downloading = False
        
        # Configuração do grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Tratamento de fechamento de janela
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Cria interface
        self._create_sidebar()
        self._create_frames()
        
        # Inicia processamento de logs
        self.after(self.LOG_PROCESS_INTERVAL, self._process_log_queue)
        
        # Mostra tela inicial
        self.show_home_frame()
    
    # ============ CRIAÇÃO DA INTERFACE ============
    
    def _create_sidebar(self):
        """Cria barra lateral de navegação"""
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)
        
        # Logo
        logo = ctk.CTkLabel(
            self.sidebar,
            text="🦉 Downloader Pro",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        logo.grid(row=0, column=0, padx=20, pady=(30, 20))
        
        # Versão com destaque
        version = ctk.CTkLabel(
            self.sidebar,
            text="v3.1 - Perplexity",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#00BFA5"
        )
        version.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Botões de navegação
        self.nav_buttons = {}
        
        buttons = [
            ("home", "🏠 Início", self.show_home_frame),
            ("courses", "📚 Cursos", self.show_courses_frame),
            ("downloads", "⬇️ Downloads", self.show_downloads_frame),
            ("logs", "📄 Logs", self.show_logs_frame),
            ("settings", "⚙️ Configurações", self.show_settings_frame)
        ]
        
        for i, (key, text, command) in enumerate(buttons, 2):
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=command,
                height=40,
                font=ctk.CTkFont(size=14)
            )
            btn.grid(row=i, column=0, padx=20, pady=8, sticky="ew")
            self.nav_buttons[key] = btn
        
        # Info de recursos
        features = ctk.CTkLabel(
            self.sidebar,
            text="✨ Materiais Extras\n📄 PDFs\n🎥 Vídeos\n📊 Slides",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            justify="left"
        )
        features.grid(row=7, column=0, padx=20, pady=(10, 20))
    
    def _create_frames(self):
        """Cria todos os frames de conteúdo"""
        self.home_frame = self._create_home_frame()
        self.downloads_frame = self._create_downloads_frame()  # ✅ Novo frame
        self.settings_frame = self._create_settings_frame()
        self.courses_frame = self._create_courses_frame()
        self.logs_frame = self._create_logs_frame()
    
    def _create_home_frame(self):
        """Frame da página inicial"""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        
        # Título
        title = ctk.CTkLabel(
            frame,
            text="🦉 Estratégia Downloader Pro",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#1E90FF"
        )
        title.grid(row=0, column=0, pady=(40, 10))
        
        subtitle = ctk.CTkLabel(
            frame,
            text="Download automatizado com materiais complementares",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        subtitle.grid(row=1, column=0, pady=(0, 40))
        
        # Botão principal
        self.start_button = ctk.CTkButton(
            frame,
            text="⏬ INICIAR DOWNLOADS",
            height=60,
            width=300,
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="#00897B",
            hover_color="#00BFA5",
            command=self._start_download
        )
        self.start_button.grid(row=2, column=0, pady=20)
        
        # Botão de cancelar
        self.cancel_button = ctk.CTkButton(
            frame,
            text="⛔ CANCELAR DOWNLOADS",
            height=50,
            width=250,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#C62828",
            hover_color="#E53935",
            command=self._cancel_download
        )
        
        # Progresso
        progress_label = ctk.CTkLabel(
            frame,
            text="📦 Progresso:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        progress_label.grid(row=4, column=0, pady=(40, 10))
        
        self.progress_bar = ctk.CTkProgressBar(frame, width=400, height=20)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=5, column=0, pady=10)
        
        self.progress_label = ctk.CTkLabel(
            frame,
            text="0%",
            font=ctk.CTkFont(size=14)
        )
        self.progress_label.grid(row=6, column=0)
        
        # Estatísticas
        stats_frame = ctk.CTkFrame(frame)
        stats_frame.grid(row=7, column=0, pady=40, sticky="ew", padx=100)
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.stat_courses = self._create_stat_box(stats_frame, "📚 Cursos", "0", 0)
        self.stat_status = self._create_stat_box(stats_frame, "📊 Status", "Pronto", 1)
        self.stat_files = self._create_stat_box(stats_frame, "📁 Arquivos", "0", 2)
        
        return frame
    
    def _create_stat_box(self, parent, title, value, column):
        """Cria uma caixa de estatística"""
        box = ctk.CTkFrame(parent)
        box.grid(row=0, column=column, padx=10, pady=10, sticky="ew")
        
        title_label = ctk.CTkLabel(
            box,
            text=title,
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        title_label.pack(pady=(10, 5))
        
        value_label = ctk.CTkLabel(
            box,
            text=value,
            font=ctk.CTkFont(size=18, weight="bold")
        )
        value_label.pack(pady=(0, 10))
        
        return value_label
    
    def _create_settings_frame(self):
        """Frame de configurações"""
        frame = ctk.CTkScrollableFrame(self, label_text="⚙️ Configurações")
        frame.grid_columnconfigure(0, weight=1)
        
        self.settings_widgets = {}
        
        # Seção: Credenciais
        cred_section = self._create_section(frame, "🔐 Credenciais")
        self._add_setting(cred_section, "Email:", "email", 0)
        self._add_setting(cred_section, "Senha:", "senha", 1, widget_type="password")
        
        # Seção: Geral
        general_section = self._create_section(frame, "🎯 Configurações Gerais")
        self._add_setting(
            general_section,
            "Tipo de Download:",
            "downloadType",
            0,
            widget_type="combo",
            options=["pdf", "video"]
        )
        self._add_setting(
            general_section,
            "Modo Invisível:",
            "headless",
            1,
            widget_type="switch"
        )
        
        # Seção: PDFs
        pdf_section = self._create_section(frame, "📄 Configurações de PDF")
        self._add_folder_setting(pdf_section, "Pasta de PDFs:", "pdf_folder", 0)
        self._add_setting(
            pdf_section,
            "Tipo de PDF:",
            "pdfType",
            1,
            widget_type="combo",
            options=["1: Simplificado", "2: Original", "3: Marcado", "4: Todos"],
            config_path=("pdfConfig",)
        )
        
        # ✅ NOVA CONFIGURAÇÃO: Baixar materiais dos vídeos junto com PDFs
        self._add_setting(
            pdf_section,
            "Baixar Materiais dos Vídeos:",
            "baixarExtrasComPdf",
            2,
            widget_type="switch",
            config_path=("pdfConfig",)
        )
        
        # Info sobre materiais dos vídeos
        extras_pdf_info = ctk.CTkLabel(
            pdf_section,
            text="ℹ️  Inclui Mapas Mentais, Resumos e Slides das aulas em vídeo",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        extras_pdf_info.grid(row=4, column=1, padx=20, pady=(0, 12), sticky="w")
        
        # Seção: Vídeos
        video_section = self._create_section(frame, "🎥 Configurações de Vídeo")
        self._add_folder_setting(video_section, "Pasta de Vídeos:", "video_folder", 0)
        self._add_setting(
            video_section,
            "Resolução:",
            "resolucaoEscolhida",
            1,
            widget_type="combo",
            options=["720p", "480p", "360p"],
            config_path=("videoConfig",)
        )
        
        # ✅ NOVA CONFIGURAÇÃO: Baixar materiais extras
        self._add_setting(
            video_section,
            "Baixar Materiais Extras:",
            "baixarExtras",
            2,
            widget_type="switch",
            config_path=("videoConfig",)
        )
        
        # Info sobre materiais extras
        extras_info = ctk.CTkLabel(
            video_section,
            text="ℹ️  Mapas Mentais, Resumos e Slides",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        extras_info.grid(row=4, column=1, padx=20, pady=(0, 12), sticky="w")
        
        # Botão salvar
        save_btn = ctk.CTkButton(
            frame,
            text="💾 SALVAR CONFIGURAÇÕES",
            height=50,
            width=300,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#1976D2",
            hover_color="#2196F3",
            command=self._save_settings
        )
        save_btn.pack(pady=30)
        
        return frame
    
    def _create_section(self, parent, title):
        """Cria uma seção de configurações"""
        section = ctk.CTkFrame(parent, fg_color="#1E1E1E", corner_radius=10)
        section.pack(fill="x", padx=20, pady=15)
        section.grid_columnconfigure(1, weight=1)
        
        title_label = ctk.CTkLabel(
            section,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#1E90FF"
        )
        title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 10), sticky="w")
        
        return section
    
    def _add_setting(self, parent, label, key, row, widget_type="entry", options=None, config_path=None):
        """Adiciona um campo de configuração"""
        label_widget = ctk.CTkLabel(parent, text=label, anchor="w")
        label_widget.grid(row=row+1, column=0, padx=20, pady=12, sticky="w")
        
        if widget_type == "entry":
            widget = ctk.CTkEntry(parent, width=350)
        elif widget_type == "password":
            widget = ctk.CTkEntry(parent, width=350, show="●")
        elif widget_type == "combo":
            widget = ctk.CTkComboBox(parent, width=350, values=options or [])
        elif widget_type == "switch":
            widget = ctk.CTkSwitch(parent, text="")
        
        widget.grid(row=row+1, column=1, padx=20, pady=12, sticky="ew")
        self.settings_widgets[key] = (widget, config_path)
    
    def _add_folder_setting(self, parent, label, key, row):
        """Adiciona campo de seleção de pasta"""
        label_widget = ctk.CTkLabel(parent, text=label, anchor="w")
        label_widget.grid(row=row+1, column=0, padx=20, pady=12, sticky="w")
        
        folder_frame = ctk.CTkFrame(parent, fg_color="transparent")
        folder_frame.grid(row=row+1, column=1, padx=20, pady=12, sticky="ew")
        folder_frame.grid_columnconfigure(0, weight=1)
        
        entry = ctk.CTkEntry(folder_frame)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        browse_btn = ctk.CTkButton(
            folder_frame,
            text="📁 Procurar",
            width=100,
            command=lambda: self._browse_folder(entry)
        )
        browse_btn.grid(row=0, column=1)
        
        config_path = ("pdfConfig",) if "pdf" in key else ("videoConfig",)
        self.settings_widgets[key] = (entry, config_path)
    
    def _create_courses_frame(self):
        """Frame de gerenciamento de cursos"""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Adicionar novo curso
        add_frame = ctk.CTkFrame(frame)
        add_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        add_frame.grid_columnconfigure(0, weight=1)
        
        self.url_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="📎 Cole aqui a URL do curso (https://www.estrategiaconcursos.com.br/...)"
        )
        self.url_entry.grid(row=0, column=0, padx=(10, 10), pady=10, sticky="ew")
        self.url_entry.bind('<Return>', lambda e: self._add_course())
        
        add_btn = ctk.CTkButton(
            add_frame,
            text="➕ Adicionar",
            width=150,
            command=self._add_course
        )
        add_btn.grid(row=0, column=1, padx=(0, 10), pady=10)
        
        # Lista de cursos
        self.courses_list = ctk.CTkScrollableFrame(
            frame,
            label_text="📚 Cursos na Fila"
        )
        self.courses_list.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.courses_list.grid_columnconfigure(0, weight=1)
        
        return frame
    
    def _create_logs_frame(self):
        """Frame de logs"""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Título e botões
        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        
        title = ctk.CTkLabel(
            header_frame,
            text="📝 Log do Processo",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w")
        
        clear_btn = ctk.CTkButton(
            header_frame,
            text="🗑️ Limpar",
            width=100,
            command=self._clear_logs
        )
        clear_btn.grid(row=0, column=1, padx=(10, 0))
        
        self.log_text = ctk.CTkTextbox(
            frame,
            wrap="word",
            font=("Consolas", 11),
            state="disabled"
        )
        self.log_text.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        # ✅ Configuração de tags de cor
        self.log_text.tag_config("INFO", foreground="#FFFFFF")
        self.log_text.tag_config("SUCCESS", foreground="#00E676")  # Verde
        self.log_text.tag_config("WARNING", foreground="#FFAB40")  # Laranja
        self.log_text.tag_config("ERROR", foreground="#FF5252")    # Vermelho
        
        return frame

    def _create_downloads_frame(self):
        """Frame de downloads ativos"""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Título
        title = ctk.CTkLabel(
            frame,
            text="⬇️ Downloads em Andamento",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Lista de downloads
        self.downloads_list = ctk.CTkScrollableFrame(
            frame,
            label_text="Arquivos"
        )
        self.downloads_list.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.downloads_list.grid_columnconfigure(0, weight=1)
        
        self.active_downloads = {}  # Mapeia nome do arquivo -> widgets
        
        return frame
    
    # ============ NAVEGAÇÃO ============
    
    def _hide_all_frames(self):
        """Oculta todos os frames"""
        self.home_frame.grid_forget()
        self.downloads_frame.grid_forget()  # ✅ Oculta frame de downloads
        self.settings_frame.grid_forget()
        self.courses_frame.grid_forget()
        self.logs_frame.grid_forget()
    
    def show_home_frame(self):
        self._hide_all_frames()
        self._update_stats()
        self.home_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_downloads_frame(self):
        self._hide_all_frames()
        self.downloads_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
    
    def show_settings_frame(self):
        self._load_settings()
        self._hide_all_frames()
        self.settings_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
    
    def show_courses_frame(self):
        self._load_courses()
        self._hide_all_frames()
        self.courses_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
    
    def show_logs_frame(self):
        self._hide_all_frames()
        self.logs_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
    
    # ============ FUNCIONALIDADES ============
    
    def _browse_folder(self, entry_widget):
        """Abre diálogo de seleção de pasta"""
        try:
            folder = filedialog.askdirectory()
            if folder:
                entry_widget.delete(0, "end")
                entry_widget.insert(0, folder)
        except Exception as e:
            self._log_message(f"❌ Erro ao selecionar pasta: {e}")
    
    def _load_settings(self):
        """Carrega configurações na interface"""
        try:
            for key, (widget, config_path) in self.settings_widgets.items():
                if key == "senha":
                    value = self.config_manager.get_password() or ""
                elif key == "pdf_folder":
                    value = self.config_manager.get("pdfConfig", "pastaDownloads")
                elif key == "video_folder":
                    value = self.config_manager.get("videoConfig", "pastaDownloads")
                elif key == "baixarExtras":  # ✅ Nova configuração
                    value = self.config_manager.get("videoConfig", "baixarExtras", default=True)
                elif config_path:
                    if key == "baixarExtrasComPdf":
                        final_key = "baixarExtrasComPdf"
                        # Garante que lê da subseção correta
                        value = self.config_manager.get("pdfConfig", "baixarExtrasComPdf", default=False)
                    else:
                        final_key = key if "_" not in key else "pdfType" if key == "pdfType" else "resolucaoEscolhida"
                        value = self.config_manager.get(*config_path, final_key)
                else:
                    value = self.config_manager.config.get(key)
                
                if isinstance(widget, ctk.CTkEntry):
                    widget.delete(0, "end")
                    if value:
                        widget.insert(0, str(value))
                elif isinstance(widget, ctk.CTkComboBox):
                    if key == "pdfType":
                        mapping = {1: "1: Simplificado", 2: "2: Original", 3: "3: Marcado", 4: "4: Todos"}
                        widget.set(mapping.get(value, "2: Original"))
                    else:
                        widget.set(str(value) if value else "")
                elif isinstance(widget, ctk.CTkSwitch):
                    if value:
                        widget.select()
                    else:
                        widget.deselect()
        
        except Exception as e:
            self._log_message(f"❌ Erro ao carregar configurações: {e}")
    
    def _save_settings(self):
        """Salva configurações"""
        try:
            for key, (widget, config_path) in self.settings_widgets.items():
                if isinstance(widget, ctk.CTkSwitch):
                    value = widget.get() == 1
                elif isinstance(widget, ctk.CTkComboBox) and key == "pdfType":
                    mapping = {"1: Simplificado": 1, "2: Original": 2, "3: Marcado": 3, "4: Todos": 4}
                    value = mapping.get(widget.get(), 2)
                else:
                    value = widget.get()
                
                if key in ["email", "senha"] and not value:
                    continue
                
                if key == "senha":
                    if value:
                        self.config_manager.set_password(value)
                elif key == "pdf_folder":
                    self.config_manager.set("pdfConfig", "pastaDownloads", value=value)
                elif key == "video_folder":
                    self.config_manager.set("videoConfig", "pastaDownloads", value=value)
                elif key == "baixarExtras":  # ✅ Salva nova configuração
                    self.config_manager.set("videoConfig", "baixarExtras", value=value)
                elif config_path:
                    if key == "baixarExtrasComPdf":
                        self.config_manager.set("pdfConfig", "baixarExtrasComPdf", value=value)
                    else:
                        final_key = key if "_" not in key else "pdfType" if key == "pdfType" else "resolucaoEscolhida"
                        self.config_manager.set(*config_path, final_key, value=value)
                else:
                    self.config_manager.config[key] = value
            
            self.config_manager.save_config()
            
            is_valid, errors = self.config_manager.validate()
            
            if is_valid:
                self.nav_buttons["settings"].configure(text="⚙️ Configurações ✓")
                self.after(2000, lambda: self.nav_buttons["settings"].configure(text="⚙️ Configurações"))
                self._log_message("✓ Configurações salvas com sucesso")
            else:
                self._log_message("⚠ Configurações salvas, mas com avisos:")
                for error in errors:
                    self._log_message(f"   - {error}")
        
        except Exception as e:
            self._log_message(f"❌ Erro ao salvar configurações: {e}")
    
    def _load_courses(self):
        """Carrega lista de cursos"""
        for widget in self.courses_list.winfo_children():
            widget.destroy()
        
        urls = self.url_manager.get_all()
        self.stat_courses.configure(text=str(len(urls)))
        
        if not urls:
            empty_label = ctk.CTkLabel(
                self.courses_list,
                text="Nenhum curso adicionado ainda",
                text_color="gray"
            )
            empty_label.pack(pady=20)
            return
        
        for url in urls:
            self._create_course_item(url)
    
    def _create_course_item(self, url):
        """Cria item de curso"""
        item = ctk.CTkFrame(self.courses_list, fg_color="#202020")
        item.pack(fill="x", padx=5, pady=5)
        
        label = ctk.CTkLabel(
            item,
            text=url,
            wraplength=800,
            justify="left"
        )
        label.pack(side="left", padx=15, pady=10, fill="x", expand=True)
        
        remove_btn = ctk.CTkButton(
            item,
            text="❌ Remover",
            width=100,
            fg_color="#C62828",
            hover_color="#E53935",
            command=lambda: self._remove_course(url)
        )
        remove_btn.pack(side="right", padx=10, pady=10)
    
    def _add_course(self):
        """Adiciona novo curso"""
        url = self.url_entry.get().strip()
        
        if not url:
            self._log_message("⚠ Digite uma URL para adicionar")
            return
        
        if self.url_manager.add_url(url):
            self.url_entry.delete(0, "end")
            self._load_courses()
            self._update_stats()
            self._log_message(f"✓ Curso adicionado")
        else:
            self._log_message(f"⚠ URL inválida ou duplicada")
    
    def _remove_course(self, url):
        """Remove curso"""
        if self.url_manager.remove_url(url):
            self._load_courses()
            self._update_stats()
            self._log_message(f"✓ Curso removido")
    
    def _start_download(self):
        """Inicia downloads"""
        if self._is_downloading:
            self._log_message("⚠ Um download já está em andamento")
            return
        
        if self.download_thread and self.download_thread.is_alive():
            self._log_message("⚠ Um download já está em andamento")
            return
        
        if len(self.url_manager.get_all()) == 0:
            self._log_message("⚠ Adicione cursos antes de iniciar o download")
            self.show_courses_frame()
            return
        
        # Limpa logs
        self._clear_logs()
        
        # Reseta progresso
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        
        # Atualiza UI
        self._is_downloading = True
        self.start_button.configure(state="disabled")
        self.start_button.grid_forget()
        self.cancel_button.grid(row=3, column=0, pady=20)
        self.stat_status.configure(text="Baixando...")
        
        # Mostra logs
        self.show_logs_frame()
        
        # Inicia thread
        try:
            self.download_manager = DownloadManager(self.config_manager, self.log_queue)
            self.download_thread = threading.Thread(
                target=self._run_download_async,
                daemon=True
            )
            self.download_thread.start()
        
        except Exception as e:
            self._log_message(f"❌ Erro ao iniciar download: {e}")
            self._on_download_complete()
    
    def _run_download_async(self):
        """Executa download em thread separada"""
        try:
            asyncio.run(
                self.download_manager.start_downloads(self._update_progress)
            )
        except Exception as e:
            self._log_message(f"❌ Erro no download: {e}")
        finally:
            self.after(100, self._on_download_complete)
    
    def _cancel_download(self):
        """Cancela download"""
        if self.download_manager:
            self.download_manager.request_cancel()
            self._log_message("⚠ Cancelamento solicitado...")
            self.cancel_button.configure(state="disabled", text="Cancelando...")
    
    def _update_progress(self, value):
        """Atualiza progresso (thread-safe)"""
        try:
            self.after(0, lambda: self._update_progress_ui(value))
        except Exception as e:
            logger.error(f"Erro ao atualizar progresso: {e}")
    
    def _update_progress_ui(self, value):
        """Atualiza UI de progresso (deve ser chamado na thread principal)"""
        try:
            self.progress_bar.set(value)
            self.progress_label.configure(text=f"{int(value * 100)}%")
        except Exception as e:
            logger.error(f"Erro ao atualizar UI de progresso: {e}")
    
    def _update_stats(self):
        """Atualiza estatísticas na tela inicial"""
        try:
            urls = self.url_manager.get_all()
            self.stat_courses.configure(text=str(len(urls)))
        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas: {e}")
    
    def _process_log_queue(self):
        """Processa fila de logs e status"""
        try:
            processed = 0
            max_process = 20  # Aumentado para processar mais updates
            
            while processed < max_process:
                try:
                    data = self.log_queue.get_nowait()
                    
                    if isinstance(data, dict):
                        msg_type = data.get("type")
                        
                        if msg_type == "log":
                            self._handle_log_message(data)
                            
                            # Verifica fim de processo pelo texto
                            message = data.get("message", "")
                            if "FINALIZADO" in message or "PROCESSO CANCELADO" in message:
                                self.after(500, self._on_download_complete)
                                
                        elif msg_type == "progress":
                            self._handle_progress_update(data)
                            
                    else:
                        # Fallback para string antiga
                        self._log_message(str(data))
                        
                    processed += 1
                
                except queue.Empty:
                    break
        
        except Exception as e:
            logger.error(f"Erro ao processar fila de logs: {e}")
        
        finally:
            self.after(self.LOG_PROCESS_INTERVAL, self._process_log_queue)
    
    def _handle_log_message(self, data):
        """Processa mensagem de log colorida"""
        level = data.get("level", "INFO")
        message = data.get("message", "")
        
        tag = "INFO"
        if level == "ERROR":
            tag = "ERROR"
        elif level == "WARNING":
            tag = "WARNING"
        elif "sucesso" in message.lower() or "concluído" in message.lower():
            tag = "SUCCESS"
        
        self._log_message(message, tag)

    def _handle_progress_update(self, data):
        """Atualiza barra de progresso de um arquivo"""
        file_name = data.get("file")
        current = data.get("current", 0)
        total = data.get("total", 0)
        speed = data.get("speed", 0)
        
        if not file_name:
            return
            
        # Cria widgets se não existirem
        if file_name not in self.active_downloads:
            self._create_download_item(file_name)
            
        widgets = self.active_downloads[file_name]
        
        from utils import format_bytes
        
        if total > 0:
            progress = current / total
            widgets["progress_bar"].set(progress)
            size_str = f"{format_bytes(current)} / {format_bytes(total)}"
        else:
            # Tamanho desconhecido: mostra apenas baixado e mantém barra em 'loading'
            # Simula barra "pulsando" ou cheia para indicar atividade
            widgets["progress_bar"].configure(mode="indeterminate")
            widgets["progress_bar"].start()
            size_str = f"{format_bytes(current)}"
        
        speed_str = f"{format_bytes(speed)}/s"
        
        widgets["status_label"].configure(text=f"{size_str} - {speed_str}")
        
        # Se completou (apenas se total > 0 para garantir)
        if total > 0 and current >= total:
             widgets["status_label"].configure(text_color="#00E676") # Verde
             widgets["progress_bar"].stop()
             widgets["progress_bar"].configure(mode="determinate")
             widgets["progress_bar"].set(1.0)

    def _create_download_item(self, file_name):
        """Cria item na lista de downloads"""
        item = ctk.CTkFrame(self.downloads_list, fg_color="#2b2b2b")
        item.pack(fill="x", padx=5, pady=5)
        
        # Título truncado
        name_label = ctk.CTkLabel(
            item, 
            text=file_name if len(file_name) < 50 else file_name[:47] + "...",
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        name_label.pack(fill="x", padx=10, pady=(5,0))
        
        # Barra
        progress = ctk.CTkProgressBar(item, height=10)
        progress.set(0)
        progress.pack(fill="x", padx=10, pady=5)
        
        # Status
        status_label = ctk.CTkLabel(
            item,
            text="Iniciando...",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        status_label.pack(anchor="e", padx=10, pady=(0,5))
        
        self.active_downloads[file_name] = {
            "frame": item,
            "progress_bar": progress,
            "status_label": status_label
        }

    def _log_message(self, message, tag="INFO"):
        """Adiciona mensagem no log com cor"""
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", message + "\n", tag)
            
            lines = int(self.log_text.index('end-1c').split('.')[0])
            if lines > self.MAX_LOG_LINES:
                self.log_text.delete("1.0", f"{lines - self.MAX_LOG_LINES}.0")
            
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        
        except Exception as e:
            logger.error(f"Erro ao adicionar log: {e}")
    
    def _clear_logs(self):
        """Limpa área de logs e downloads"""
        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")
            
            # Limpa downloads também
            for widget in self.downloads_list.winfo_children():
                widget.destroy()
            self.active_downloads.clear()
            
        except Exception as e:
            logger.error(f"Erro ao limpar logs: {e}")
    
    def _on_download_complete(self):
        """Callback de finalização"""
        try:
            self._is_downloading = False
            self.cancel_button.grid_forget()
            self.start_button.grid(row=2, column=0, pady=20)
            self.start_button.configure(state="normal", text="⏬ INICIAR DOWNLOADS")
            self.stat_status.configure(text="Concluído")
        except Exception as e:
            logger.error(f"Erro ao finalizar download: {e}")
    
    def _on_closing(self):
        """Trata fechamento da janela"""
        if self._is_downloading:
            import tkinter.messagebox as messagebox
            if messagebox.askyesno(
                "Download em Andamento",
                "Um download está em andamento. Deseja cancelar e fechar?"
            ):
                if self.download_manager:
                    self.download_manager.request_cancel()
                self.after(1000, self.destroy)
        else:
            self.destroy()


def main():
    """Função principal"""
    try:
        app = StrategyDownloaderApp()
        app.mainloop()
    except Exception as e:
        print(f"Erro fatal na aplicação: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
