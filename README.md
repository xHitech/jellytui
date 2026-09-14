# jellytui

Reprodutor exclusivamente musical para terminal Linux. Biblioteca Jellyfin, interface textual discreta em Textual e reprodução por mpv, sem janela gráfica ou capas.

## Executar

Python 3.11+ e mpv devem estar disponíveis. Neste ambiente foram encontrados Python 3.14.7 e mpv 0.41.0; a `.venv` já foi criada e as dependências instaladas. Nenhum pacote de sistema foi instalado.

```bash
cd ~/jellyfin-terminal
source .venv/bin/activate
jellytui
```

Também funciona sem ativar o ambiente:

```bash
.venv/bin/python -m jellytui
```

Na primeira execução, informe servidor (padrão `http://127.0.0.1:8096`), usuário e senha. Digite a senha no terminal: ela não aparece nem é salva. Após autenticar, a TUI abre automaticamente.

```bash
jellytui --setup   # configurar novamente ou trocar de servidor/usuário; depois encerra
jellytui --check   # validar autenticação, contar biblioteca e negociar um stream original
jellytui --check-play # validar também áudio real com mpv e saída silenciosa
jellytui --demo    # dados fictícios, sem rede e sem reprodução
```

Para instalar em outro checkout:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

No Arch, se **faltarem** dependências de sistema, instale-as você mesmo: `sudo pacman -S python mpv`. O programa nunca chama pacman.

## Interface e teclas

A tabela ocupa toda a largura e começa em **Biblioteca**: Artistas, Álbuns, Pastas, Playlists e Favoritos. Enter abre a seleção; Backspace volta um nível e restaura a posição anterior. O caminho do contexto aparece na barra de informações. Não há painel lateral.

Fluxo típico: Biblioteca → Artistas → artista → álbum → faixas. Um artista também permite acessar suas faixas. Pastas parte das bibliotecas de música do Jellyfin; playlists de vídeo não aparecem. Consultas continuam paginadas.

No topo, Now Playing e Letra dividem um painel compacto. O Now Playing mantém título, artista, álbum, posição, duração, progresso, pausa, volume, Direct Play e metadados técnicos. `l` oculta/mostra letras; ocultas, o Now Playing ocupa a largura superior inteira. O indicador `▶` identifica a faixa atual na tabela.

| Tecla | Ação |
| --- | --- |
| ↑ / k, ↓ / j | Subir / descer |
| Enter | Abrir item ou reproduzir a partir da faixa selecionada |
| Backspace | Voltar um nível |
| PageUp / PageDown | Página anterior / próxima |
| Home / End | Primeiro / último item |
| Tab / Shift+Tab | Alternar foco disponível |
| Space | Play/pause |
| n / p | Próxima / anterior na fila |
| ← / → | Seek de −5 / +5 segundos |
| + ou = / − | Aumentar / diminuir volume em 5%, limitado a 0–100% |
| / | Buscar faixas, artistas e álbuns |
| Enter / Escape na busca | Confirmar / fechar busca |
| f | Alternar favorito do item selecionado |
| Q (maiúsculo) | Mostrar fila local |
| l | Mostrar / ocultar letras |
| h | Abrir / fechar ajuda |
| Escape | Fechar ajuda ou busca |
| q | Sair e encerrar o mpv do aplicativo |

`h` abre ajuda central rolável, organizada por categorias, gerada pela mesma definição dos bindings em `controls.py`. A ajuda não pausa a música nem impede o avanço automático. O rodapé mostra somente Space, n, p, /, l, h e q. Dentro da busca, letras e espaço são texto, não controles do player.

**Contexto de reprodução:** Enter na faixa 3 de uma lista de cinco cria a fila `[faixa 3, faixa 4, faixa 5]`, com índice inicial zero. Entradas não musicais são ignoradas; ordem e repetições são preservadas. Isso vale para álbum, playlist, favoritos, busca e listas de artista. O fim de uma faixa avança automaticamente; o fim da fila para a reprodução. `p` volta dentro desse contexto, não para faixas anteriores à seleção inicial. Navegar por outras listas não muda a fila até tocar outra seleção. A fila permanece apenas na memória.

## Letras sincronizadas

A especificação OpenAPI do servidor Jellyfin **10.11.11** confirma `GET /Audio/{itemId}/Lyrics` (`GetLyrics`). A resposta é um `LyricDto` com `Lyrics[].Text` e `Lyrics[].Start`; `Start` usa ticks de 100 nanossegundos, convertidos para segundos dividindo por 10.000.000. `Metadata` pode estar vazio: timestamps válidos bastam para detectar sincronização. Em uma consulta real, **Duvet retornou 46 linhas**, com primeiros tempos 6,94 s, 12,04 s, 17,01 s e 22,05 s.

O aplicativo usa a letra já fornecida/indexada pelo Jellyfin. Não lê o filesystem remoto, não pesquisa provedores externos, não faz upload e não baixa letras para a biblioteca. HTTP 404 significa letra ausente; falhas de rede aparecem discretamente no painel e não impedem o áudio.

`lyrics.py` também contém parser LRC com timestamps simples, múltiplos timestamps por linha, frações de segundo, metadados e offset em milissegundos. A API já fornece linhas estruturadas: o aplicativo não reconstrói um arquivo LRC nem reaplica offsets aos timestamps devolvidos pelo servidor.

A seleção da linha usa busca binária na posição **real do mpv** (`time-pos`), sem relógio de reprodução próprio. A atualização visual usa o ciclo já existente de 250 ms; o painel só redesenha ao mudar de linha/tamanho/estado. Mostra duas linhas anteriores, a atual destacada e duas próximas. Seek consulta a posição do mpv; pausa mantém a seleção. Ao trocar de faixa, limpa a letra e carrega a nova em segundo plano; resultados atrasados de outra faixa são descartados.

Sem timestamps, mostra um trecho identificado como letra sem sincronização. Sem letra, mostra “Letra não disponível”. O suporte é por linha; cues por palavra do Jellyfin não são usados.

## Configuração e credenciais

`~/.config/jellytui/config.toml` (ou `$XDG_CONFIG_HOME/jellytui/config.toml`) armazena somente URL, ID do usuário, token de acesso e ID aleatório do dispositivo. A gravação é atômica e o arquivo fica com permissão `0600`. Um arquivo existente com permissões abertas é recusado; corrija com `chmod 600 ~/.config/jellytui/config.toml`.

A senha existe somente durante a autenticação via `POST /Users/AuthenticateByName`. Token e senha não são exibidos em mensagens/logs; o token chega ao mpv por IPC, nunca na linha de comando. O socket fica em diretório temporário privado e é removido no encerramento normal. Trocar configuração não altera o servidor nem revoga sessões de outros clientes.

## Reprodução e qualidade

O cliente negocia `POST /Items/{itemId}/PlaybackInfo` com um perfil de áudio para mpv e transcodificação desabilitada. Se o Jellyfin permite Direct Play, usa um stream estático original em `/Audio/{itemId}/stream?static=true` (ou URL estática fornecida pelo servidor). Não converte FLAC nem força codec, sample rate ou quantidade de canais. Se o servidor exigir transcodificação, mostra uma mensagem e não inicia uma conversão silenciosa.

`mpv` roda com `--no-config --no-video --audio-display=no --idle=yes`, controlado por JSON IPC Unix com IDs de requisição, timeouts, propriedades observadas e eventos de fim de arquivo. A saída de áudio é a padrão do sistema. Não há download permanente, cache em disco, filtros de áudio impostos, escrita na biblioteca ou alterações de configuração do servidor. `f` altera somente o favorito do usuário.

Direct Play preserva o arquivo transmitido. Volume digital e a configuração do mixer/dispositivo de áudio do Linux continuam podendo afetar a saída; o aplicativo não promete reprodução bit-perfect nem modifica PipeWire/ALSA.

## Arquitetura

```text
jellytui/
  __init__.py
  __main__.py           CLI e setup interativo
  app.py                TUI, navegação, fila e controles
  config.py             TOML privado e validação
  jellyfin.py           autenticação, biblioteca, favoritos e stream
  player.py             processo mpv e IPC assíncrono
  models.py             itens e fila por contexto
  lyrics.py             parser LRC e modelo temporal
  controls.py           fonte única dos atalhos e da ajuda
  demo.py               biblioteca offline explícita
  widgets/
    browser.py          entradas da Biblioteca (sem widget lateral)
    now_playing.py      metadados, estado e progresso
    track_list.py       lista e navegação principal
    lyrics.py           janela de letras sincronizadas
    help.py             modal de ajuda
 tests/                 API simulada, TUI e mpv real
 pyproject.toml         pacote, comando jellytui e dependências
```

Dependências de execução: `textual>=8.2,<9`, `httpx>=0.28,<0.29`; testes: pytest e pytest-asyncio. Não depende de libmpv nem implementa decodificação de áudio em Python.

## Testes e diagnóstico

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m jellytui --check
.venv/bin/python -m jellytui --check-play
JELLYTUI_LIVE_TEST=1 .venv/bin/python -m pytest tests/test_live.py -q
```

Resultado da validação em 11/09/2026: **47 testes automatizados passaram**, com **1 teste real omitido por padrão**; executado separadamente, **esse teste opt-in contra o servidor real também passou**. A suíte local final levou 23,78 s; o smoke test real, 10,01 s. `pip check` não encontrou conflitos de dependências.

Os testes de mpv usam áudio temporário e saída `null`, sem tocar som nos alto-falantes. Precisam de permissão para sockets Unix; o teste HTTP também precisa de loopback. O restante usa `httpx.MockTransport` e o piloto headless do Textual, sem credenciais reais.

Se não conectar, confira o Tailscale, a URL e se o Jellyfin está acessível. Em HTTP 401/403, use `--setup` para autenticar novamente ou confira permissões da conta. Erros de rede e reprodução aparecem na TUI sem revelar respostas de autenticação. Uma faixa com erro não desencadeia tentativas infinitas: selecione outra ou use `n`. Se o processo mpv morrer, reinicie jellytui.

## Escopo e limites

Implementados: navegação musical hierárquica, autenticação persistente, busca, favoritos, playlists, fila local, controles mpv e painel Now Playing. A API pública e a especificação do servidor Jellyfin 10.11.11 foram consultadas durante a implementação. A validação autenticada no servidor foi concluída: 28 artistas, 73 álbuns e 797 faixas. Um stream FLAC 16-bit / 44,1 kHz / Stereo foi reproduzido em Direct Play por mpv real. O teste integrado da TUI abre Biblioteca → Álbuns → faixas e verifica pausa, seek, volume, próxima/anterior, busca por Duvet, letras reais, ajuda e ocultação do painel. Nenhum favorito é alterado durante os testes reais. Todos os testes de reprodução usaram saída silenciosa; a saída física dos alto-falantes não foi avaliada.

Não implementados: transcodificação de fallback, download, capas, reprodução gapless, embaralhar/repetir, edição de playlists, persistência da fila e relatório de histórico/progresso para o servidor. Os contextos anteriores são restaurados da memória ao voltar; reabra a categoria para consultar mudanças externas. Letras longas são truncadas à largura do painel; letras não sincronizadas mostram apenas um trecho. Bibliotecas muito grandes são carregadas por páginas, mas a lista final permanece em memória.

Referências utilizadas: [OpenAPI oficial do Jellyfin](https://api.jellyfin.org/openapi/jellyfin-openapi-stable.json), a especificação `/api-docs/openapi.json` do próprio servidor e [manual oficial de IPC do mpv](https://mpv.io/manual/stable/#json-ipc).

## License

MIT License. See LICENSE.
