# 📚 Guia de Uso - Download de Materiais Complementares

## Estratégia Downloader Pro v3.1 - Powered by Perplexity - Expansão de Recursos

---

## 🎯 Nova Funcionalidade

O **Estratégia Downloader Pro** agora baixa automaticamente **TODOS** os materiais complementares disponíveis em cada vídeo-aula:

- ✅ **Vídeos** (como antes)
- ✅ **Mapas Mentais** 🆕
- ✅ **Resumos** 🆕
- ✅ **Slides** 🆕

---

## 📦 Arquivos Modificados

Para ativar a nova funcionalidade, substitua os seguintes arquivos:

### 1. `video_processor.py` → `video_processor_expandido.py`

Renomeie o arquivo expandido:
```bash
mv video_processor_expandido.py video_processor.py
```

### 2. `config_manager.py` → `config_manager_expandido.py`

Renomeie o arquivo expandido:
```bash
mv config_manager_expandido.py config_manager.py
```

---

## ⚙️ Configuração

A nova opção `baixarExtras` foi adicionada à configuração de vídeos.

### Via Interface Gráfica

1. Abra o **Estratégia Downloader Pro**
2. Vá em **⚙️ Configurações**
3. Na seção **🎥 Configurações de Vídeo**, você verá:
   - Pasta de Vídeos
   - Resolução
   - **✨ Baixar Extras** (NOVO) - Checkbox para ativar/desativar

### Via Arquivo `config.json`

```json
{
  "email": "seu@email.com",
  "downloadType": "video",
  "headless": false,
  "pdfConfig": {
    "pastaDownloads": "C:\\Users\\Você\\Downloads\\Estrategia_PDFs",
    "pdfType": 2
  },
  "videoConfig": {
    "pastaDownloads": "C:\\Users\\Você\\Downloads\\Estrategia_Videos",
    "resolucaoEscolhida": "720p",
    "baixarExtras": true  ← NOVA OPÇÃO
  }
}
```

**Valores:**
- `true` = Baixa vídeos + materiais complementares ✅
- `false` = Baixa apenas vídeos (comportamento antigo)

---

## 📁 Estrutura de Arquivos

Com a nova funcionalidade, os arquivos são organizados assim:

```
Estrategia_Videos/
└── Auditoria Governamental/
    ├── Aula 01 - Introdução/
    │   ├── Aula 01 - Introdução - Vídeo 1 Planejamento Da Auditoria [720p].mp4
    │   ├── Aula 01 - Introdução - Vídeo 1 Planejamento Da Auditoria - Mapa Mental.pdf  ← NOVO
    │   ├── Aula 01 - Introdução - Vídeo 1 Planejamento Da Auditoria - Resumo.pdf      ← NOVO
    │   ├── Aula 01 - Introdução - Vídeo 1 Planejamento Da Auditoria - Slides.pdf      ← NOVO
    │   ├── Aula 01 - Introdução - Vídeo 2 Documentação De Auditoria [720p].mp4
    │   ├── Aula 01 - Introdução - Vídeo 2 Documentação De Auditoria - Resumo.pdf      ← NOVO
    │   └── Aula 01 - Introdução - Vídeo 3 NBC TA e NBC PA [720p].mp4
    │       └── Aula 01 - Introdução - Vídeo 3 NBC TA e NBC PA - Mapa Mental.pdf       ← NOVO
    └── Aula 02 - Normas/
        └── ...
```

**Observações:**
- Nem todo vídeo tem todos os materiais
- O downloader só baixa os materiais que **existem**
- Se um vídeo não tem Mapa Mental, ele não será baixado (óbvio!)
- Cada material é validado individualmente

---

## 🔍 Como Funciona

### Fluxo de Download

1. **Clica no vídeo** para abrir a página de visualização
2. **Aguarda o player carregar** (1.2 segundos)
3. **Baixa o vídeo** na resolução escolhida
4. **Procura materiais complementares:**
   - Procura botão "Baixar Mapa Mental"
   - Procura botão "Baixar Resumo"
   - Procura botão "Baixar Slides"
5. **Baixa cada material encontrado**
6. **Marca no progresso** para não baixar novamente

### Detecção Inteligente

O sistema detecta os materiais de **3 formas**:

1. **Via atributo `href`** - Link direto no botão
2. **Via click** - Clica no botão se não tiver `href`
3. **Via link de download** - Procura `<a download>` que aparece após click

### Validação de Arquivos

Todos os PDFs (mapas, resumos, slides) são validados:
- ✅ Tamanho mínimo: 10KB
- ✅ Magic bytes: `%PDF` (confirma que é PDF válido)
- ✅ Arquivo completo (não corrompido)

---

## 📊 Logs e Progresso

### Exemplo de Log

```
🎬 Processando aula: Aula 01 - Introdução
✓ Encontrados 3 vídeo(s)
✓ Vídeo selecionado: Planejamento Da Auditoria
⬇️  Baixando: Aula 01 - Introdução - Vídeo 1 Planejamento Da Auditoria [720p].mp4
✅ Concluído: Planejamento Da Auditoria
📚 Buscando materiais complementares de 'Planejamento Da Auditoria'...
   ⬇️  Baixando mapa mental...
   ✅ Mapa mental baixado
   ⬇️  Baixando resumo...
   ✅ Resumo baixado
   ⬇️  Baixando slides...
   ✅ Slides baixados
```

### Progresso Rastreado

O arquivo `progress.json` agora rastreia:

```json
{
  "aula01-Planejamento Da Auditoria-1": true,
  "aula01-Planejamento Da Auditoria-1-mapa": true,
  "aula01-Planejamento Da Auditoria-1-resumo": true,
  "aula01-Planejamento Da Auditoria-1-slides": true
}
```

Isso garante que:
- ✅ Materiais já baixados não são baixados novamente
- ✅ Se você cancelar, pode continuar de onde parou
- ✅ Mesmo que o vídeo já exista, extras faltantes serão baixados

---

## 🎛️ Controle Fino

### Desabilitar Download de Extras

Se você quiser baixar **APENAS** os vídeos (sem extras):

```json
"videoConfig": {
  "baixarExtras": false
}
```

### Baixar Apenas Extras (Sem Vídeos)

**Não suportado diretamente**, mas você pode:

1. Baixar tudo normalmente
2. Deletar os arquivos `.mp4`
3. Manter apenas os PDFs

Ou configurar manualmente o código para pular vídeos.

---

## ⚡ Performance

### Tempo Estimado

Com extras habilitados, o tempo de download aumenta:

| Cenário | Tempo Estimado |
|---------|----------------|
| **Apenas vídeos** (antes) | ~5 min por curso |
| **Vídeos + extras** (novo) | ~7-10 min por curso |

**Motivo**: Cada vídeo pode ter 2-3 materiais extras

### Otimizações Aplicadas

✅ **Rate limiting** - Máximo 3 downloads simultâneos  
✅ **Cache de progresso** - Não baixa arquivos duplicados  
✅ **Detecção rápida** - Pula materiais inexistentes em 0.5s  
✅ **Validação** - Evita redownloads de arquivos corrompidos

---

## 🐛 Troubleshooting

### "Nenhum material complementar encontrado"

**Normal!** Nem todos os vídeos têm extras.

Veja o log:
```
ℹ️  Sem mapa mental para 'Vídeo X'
ℹ️  Sem resumo para 'Vídeo X'
ℹ️  Sem slides para 'Vídeo X'
```

### "Erro ao baixar mapa mental"

**Possíveis causas:**
1. Material não existe (página mudou)
2. Link quebrado no site
3. Problema de rede

**Solução:** O downloader continua normalmente. Verifique manualmente no site.

### Extras sendo baixados mesmo com `baixarExtras: false`

**Solução:** Delete `progress.json` e reinicie o download.

### Arquivo corrompido

Se um PDF estiver corrompido:
1. Delete o arquivo manualmente
2. Delete a entrada correspondente em `progress.json`
3. Execute novamente

---

## 💡 Dicas e Boas Práticas

### ✅ Recomendado

1. **Mantenha `baixarExtras: true`** - Vale a pena baixar tudo
2. **Use resolução 720p** - Melhor custo-benefício
3. **Deixe rodar à noite** - Cursos grandes demoram
4. **Verifique logs** - Identifica problemas rapidamente

### ⚠️ Atenção

1. **Espaço em disco** - Materiais extras podem ocupar 20-30% a mais
2. **Tempo de download** - Aumenta ~40% com extras
3. **Progresso** - Não delete `progress.json` durante downloads

---

## 🔧 Customização Avançada

### Baixar Apenas Mapas Mentais

Edite `video_processor_expandido.py`:

```python
async def _download_video_extras(...):
    # Comenta as linhas de resumo e slides:
    await self._download_mapa_mental(...)
    # await self._download_resumo(...)      ← Comentado
    # await self._download_slides(...)      ← Comentado
```

### Alterar Timeout de Detecção

```python
MATERIAL_LOAD_TIMEOUT = 10000  # Aumenta se conexão lenta
```

---

## 📈 Estatísticas

Com a nova funcionalidade, você terá:

- **3-4x mais arquivos** por curso
- **Organização perfeita** por aula e vídeo
- **Materiais prontos** para estudo offline
- **Sincronização** com progresso do curso

---

## 🚀 Exemplos Práticos

### Cenário 1: Estudante Preparando para Concurso

```
1. Configura: baixarExtras = true
2. Adiciona 5 cursos na fila
3. Inicia download à noite
4. Manhã seguinte: Todos os materiais prontos!
```

**Resultado:**
- 15 aulas × 3 vídeos = 45 vídeos
- 45 × 2 extras (média) = 90 PDFs
- Total: **135 arquivos organizados**

### Cenário 2: Revisão Rápida

```
1. Já tem os vídeos baixados
2. Configura: baixarExtras = true
3. Executa novamente
```

**Resultado:**
- Vídeos são pulados (já existem)
- Apenas extras são baixados
- Tempo: **2-3 minutos por curso**

---

## 📞 Suporte

Encontrou um problema?

1. Verifique os **logs** em `downloader.log`
2. Confira `progress.json` para ver o que foi baixado
3. Tente com `baixarExtras: false` para isolar o problema
4. Reporte no GitHub com logs anexados

---

## 🎉 Conclusão

A nova funcionalidade torna o **Estratégia Downloader Pro** ainda mais completo:

- ✅ Download automático de **TODOS** os materiais
- ✅ Organização perfeita de arquivos
- ✅ Rastreamento inteligente de progresso
- ✅ Validação robusta de arquivos
- ✅ Configurável via interface ou JSON

**Agora você tem TUDO do curso offline! 🚀**

---

*Guia criado em: 04/02/2026*  
*Estratégia Downloader Pro v3.1 - Powered by Perplexity - Expandido*
