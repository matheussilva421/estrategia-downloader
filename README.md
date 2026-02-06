# 🦉 Estratégia Downloader Pro v3.1 - Powered by Perplexity

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.1-green.svg)](https://github.com/seu-usuario/estrategia-downloader-pro)

Downloader automatizado, seguro e profissional para cursos da plataforma Estratégia Concursos com **suporte completo a materiais complementares**.

## ✨ Novidades da Versão 3.1

### 🎁 **NOVO: Download de Materiais Complementares**
- ✅ **Mapas Mentais** - Baixa automaticamente
- ✅ **Resumos** - Baixa automaticamente  
- ✅ **Slides** - Baixa automaticamente
- ✅ **Controle via Interface** - Ative/desative facilmente

### 🔧 Melhorias da Versão 2.0
- **Senhas criptografadas** com AES-128 (Fernet)
- **Arquitetura profissional** - 8 módulos especializados
- **Rate limiting** - Previne sobrecarga do servidor
- **Validação de arquivos** - Magic bytes (PDF/MP4)
- **Thread-safe** - Cancelamento com asyncio.Event
- **Health check** - Valida sistema antes de iniciar
- **Métricas de performance** - Rastreia velocidade e progresso
- **Interface moderna** - Dark mode com CustomTkinter

## 📋 Sumário

- [Instalação](#-instalação)
- [Como Usar](#-como-usar)
- [Materiais Complementares](#-materiais-complementares)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Configurações](#-configurações)
- [FAQ](#-perguntas-frequentes)
- [Documentação Completa](#-documentação-completa)

## 🔧 Instalação

### Pré-requisitos

- Python 3.8 ou superior
- Google Chrome instalado
- Windows 10/11 (compatível com Linux/Mac com ajustes)

### Passo 1: Extraia o arquivo

```bash
# Windows
# Clique com botão direito > Extrair tudo

# Linux/Mac
unzip estrategia-downloader-pro-v3.1.zip
cd estrategia-downloader-pro-v3.1
```

### Passo 2: Instale as dependências

```bash
pip install -r requirements.txt
```

### Passo 3: Instale o navegador Playwright

```bash
playwright install chromium
```

## 🚀 Como Usar

### Interface Gráfica (Recomendado)

```bash
python app.py
```

### Linha de Comando

```bash
python downloader.py
```

### Primeiro Uso - Guia Rápido

1. **Configure credenciais** (Aba "Configurações")
   - Email: seu@email.com
   - Senha: sua_senha (será criptografada)

2. **Configure downloads de vídeo** (Aba "Configurações" → Vídeo)
   - ✅ Marque "Baixar Materiais Extras"
   - Escolha resolução: 720p (recomendado)

3. **Adicione cursos** (Aba "Cursos")
   - Cole a URL: `https://www.estrategiaconcursos.com.br/.../aulas`
   - Clique em "Adicionar"

4. **Inicie downloads** (Aba "Início")
   - Clique em "INICIAR DOWNLOADS"
   - Acompanhe em "Logs"

## 🎁 Materiais Complementares

### O que é baixado automaticamente?

Quando você ativa "Baixar Materiais Extras" nas configurações de vídeo:

```
📁 Curso/
  └── 📁 Aula 01/
      ├── 🎥 Vídeo 1 - Introdução [720p].mp4
      ├── 📄 Vídeo 1 - Introdução - Mapa Mental.pdf      ← NOVO
      ├── 📄 Vídeo 1 - Introdução - Resumo.pdf           ← NOVO
      └── 📄 Vídeo 1 - Introdução - Slides.pdf           ← NOVO
```

### Como ativar/desativar?

**Via Interface:**
1. Vá em "⚙️ Configurações"
2. Seção "🎥 Configurações de Vídeo"
3. Marque/desmarque "Baixar Materiais Extras"

**Via config.json:**
```json
{
  "videoConfig": {
    "baixarExtras": true  ← true = baixa extras, false = apenas vídeos
  }
}
```

### Inteligência Automática

- ✅ Detecta **automaticamente** quais materiais existem
- ✅ Pula materiais que não existem (sem erro)
- ✅ Valida PDFs com magic bytes (`%PDF`)
- ✅ Rastreia progresso individual de cada material
- ✅ Continua de onde parou se cancelar

## 📁 Estrutura do Projeto

```
estrategia-downloader-pro-v3.1/
│
├── app.py                      # Interface gráfica principal
├── downloader.py               # Gerenciador de downloads (CLI)
├── config_manager.py           # Configurações + suporte a extras
├── auth.py                     # Sistema de autenticação
├── base_processor.py           # Classe base para processadores
├── pdf_processor.py            # Processador de PDFs
├── video_processor.py          # Processador de vídeos + extras
├── utils.py                    # Funções utilitárias
│
├── requirements.txt            # Dependências Python
├── LICENSE                     # Licença MIT
├── README.md                   # Este arquivo
├── MELHORIAS.md                # Changelog detalhado v2.0
└── GUIA_MATERIAIS_EXTRAS.md    # Guia completo de extras
```

## ⚙️ Configurações

### Configurações de Vídeo (ATUALIZADAS)

| Opção | Valores | Padrão | Descrição |
|-------|---------|--------|-----------|
| **Pasta de Vídeos** | Caminho | `~/Downloads/Estrategia_Videos` | Onde salvar |
| **Resolução** | `720p`, `480p`, `360p` | `720p` | Qualidade |
| **✨ Baixar Extras** | `true`, `false` | `true` | Mapas/Resumos/Slides |

### Configurações de PDF

| Opção | Valores | Padrão | Descrição |
|-------|---------|--------|-----------|
| **Pasta de PDFs** | Caminho | `~/Downloads/Estrategia_PDFs` | Onde salvar |
| **Tipo de PDF** | `1`, `2`, `3`, `4` | `2` | Qual versão |

**Tipos de PDF:**
- `1` - Versão Simplificada
- `2` - Versão Original (recomendado)
- `3` - Marcação dos Aprovados
- `4` - Todos os tipos

## 📊 Comparação de Versões

| Recurso | v1.0 | v2.0 | v3.1 |
|---------|------|------|------|
| Download de PDFs | ✅ | ✅ | ✅ |
| Download de Vídeos | ✅ | ✅ | ✅ |
| **Mapas Mentais** | ❌ | ❌ | ✅ |
| **Resumos** | ❌ | ❌ | ✅ |
| **Slides** | ❌ | ❌ | ✅ |
| Senha Criptografada | ❌ | ✅ | ✅ |
| Rate Limiting | ❌ | ✅ | ✅ |
| Validação de Arquivos | ❌ | ✅ | ✅ |
| Health Check | ❌ | ✅ | ✅ |
| Métricas | ❌ | ✅ | ✅ |
| Interface Moderna | ⚠️ | ✅ | ✅ |

## ❓ Perguntas Frequentes

### P: Os materiais extras aumentam muito o tempo de download?

**R:** Sim, em cerca de 40%. Exemplo:
- Apenas vídeos: ~5 min por curso
- Vídeos + extras: ~7-10 min por curso

Mas **vale muito a pena** ter todo o material organizado!

### P: Posso baixar apenas os extras sem os vídeos?

**R:** Não diretamente. Mas você pode:
1. Baixar tudo
2. Deletar os arquivos `.mp4`
3. Manter apenas os PDFs

### P: E se um vídeo não tiver mapa mental?

**R:** Normal! O sistema detecta automaticamente e pula sem erro:
```
ℹ️  Sem mapa mental para 'Vídeo X'
ℹ️  Sem resumo para 'Vídeo X'
```

### P: Os extras consomem muito espaço em disco?

**R:** PDFs são pequenos. Geralmente 20-30% a mais que apenas vídeos.

### P: Posso baixar extras de cursos já baixados?

**R:** Sim! Execute novamente com `baixarExtras: true`. O sistema:
- ✅ Pula vídeos já baixados
- ✅ Baixa apenas extras faltantes

## 📖 Documentação Completa

- **MELHORIAS.md** - Changelog detalhado da v2.0 (32 melhorias!)
- **GUIA_MATERIAIS_EXTRAS.md** - Guia completo sobre materiais complementares

---

<div align="center">

**Desenvolvido com ❤️ e ☕**

**v3.1 - Agora com materiais complementares! 🎉**

</div>