# FPS Movimento — 1v1 multiplayer em Python

Um FPS 1v1 de movimentação rápida feito em **Python + Ursina**. Um tiro mata, e o foco do jogo é o movimento: **slide**, **andar na parede**, **dash no ar** e **bunny hop**. Dois jogadores jogam pela rede (mesma rede local, VPN ou porta liberada no roteador), sem servidor dedicado.

---

## Índice

1. [Recursos](#recursos)
2. [Organização da pasta](#organização-da-pasta)
3. [Dependências](#dependências)
4. [Como executar](#como-executar)
5. [Como conectar com o amigo](#como-conectar-com-o-amigo)
6. [Controles](#controles)
7. [Mecânicas](#mecânicas)
8. [HUD](#hud)
9. [Configurações no código](#configurações-no-código)
10. [Como o multiplayer funciona](#como-o-multiplayer-funciona)
11. [Estrutura do código](#estrutura-do-código)
12. [Solução de problemas](#solução-de-problemas)
13. [Limitações conhecidas](#limitações-conhecidas)
14. [Créditos](#créditos)

---

## Recursos

- **1v1 online** com host e cliente, pelo mesmo arquivo.
- **One shot:** um tiro mata, com recarga de 0,75 s.
- **Shotgun** com 7 chumbinhos e dispersão pequena (o do centro vai exatamente na mira).
- **Movimentação:** slide no chão, wallrun com inclinação da câmera, dash no ar, pulo de parede, bunny hop e strafe no ar.
- **Times por cor:** o host é **azul**, quem entra é **vermelho**.
- **Modelos 3D** (`.glb`) para a arma e para o outro jogador, com fallback para formas simples se os arquivos não existirem.
- **HUD estilizada:** placar, mira dinâmica, medidor de velocidade, habilidades, kill feed e hitmarker.
- **Menu de opções (`M`)** com sensibilidade X e Y separadas, salva por jogador.

---

## Organização da pasta

Deixe **tudo na mesma pasta**, nos dois computadores:

```
fps-movimento/
├── fps_multiplayer.py                              ← o jogo (todo o código)
├── Shotgun_by_Quaternius_-_DcNE0HVdW8.glb          ← modelo da arma na mão
├── Character_Base_by_madtrollstudio_-_qbDLeTtb8K.glb ← modelo do outro jogador
├── README.md                                       ← este arquivo
│
├── hud_font.ttf          (opcional) fonte própria para o HUD
├── sens_host.json        (gerado) sensibilidade salva de quem hospeda
└── sens_join.json        (gerado) sensibilidade salva de quem entra
```

Observações:

- O jogo procura os modelos pelo nome (`*Shotgun*.glb` e `*Character*.glb`) **na pasta do script** ou numa subpasta `assets/`. Você pode renomear os arquivos ou movê-los para `assets/`, desde que o nome continue contendo `Shotgun` ou `Character`.
- Se os `.glb` não forem encontrados (ou falharem ao carregar), o jogo **não quebra**: usa cubos no lugar e mostra um aviso no terminal.
- Os arquivos `sens_*.json` são criados quando você fecha o menu de opções pela primeira vez. Pode apagá-los para voltar à sensibilidade padrão.
- Cada jogador precisa ter a pasta completa. Os modelos são só visuais e cada um vê os seus; não há troca de arquivos pela rede.

---

## Dependências

| O quê | Versão | Observação |
|---|---|---|
| **Python** | 3.9 a 3.12 recomendado | Foi testado com 3.12. Versões muito novas podem não ter pacote do Panda3D ainda. |
| **ursina** | a mais recente | Instala sozinho o Panda3D e as outras bibliotecas que ele usa. |

Não há mais nada para instalar. O leitor de `.glb` é do próprio jogo (sem `numpy`, `panda3d-gltf` ou outras bibliotecas), e o multiplayer usa apenas a biblioteca padrão do Python (`socket`, `threading`, `json`, `struct`).

Instalação:

```
pip install ursina
```

No Windows, para garantir que instala no Python certo:

```
py -3.12 -m pip install ursina
```

---

## Como executar

Os dois jogadores rodam o **mesmo arquivo**. Um hospeda e o outro entra.

**Quem hospeda (host, jogador azul):**

```
python fps_multiplayer.py host
```

O terminal mostra `Aguardando seu amigo...`. A janela do jogo só abre depois que o amigo conectar.

**Quem entra (jogador vermelho):**

```
python fps_multiplayer.py join IP_DO_HOST
```

Exemplo: `python fps_multiplayer.py join 192.168.0.15`

Se rodar sem argumentos, o jogo pergunta no terminal se você quer `host` ou `join` (e o IP).

> **Ordem:** o host precisa iniciar primeiro e estar aguardando antes de o amigo tentar entrar.

No Windows, se `python` não funcionar, use `py -3.12 fps_multiplayer.py host` (ou `join IP`). No VS Code, você também pode abrir o arquivo e usar o botão de executar, desde que o interpretador selecionado seja o Python onde o ursina foi instalado.

---

## Como conectar com o amigo

A conexão é direta (TCP, porta **5555**), então o amigo precisa conseguir alcançar o computador do host.

1. **Mesma rede (casa, escola, Wi-Fi):** o host descobre o IP com `ipconfig` (Windows) e procura o **Endereço IPv4** do adaptador que tem Gateway Padrão. O amigo usa esse IP no `join`.
2. **Redes diferentes:** o jeito mais fácil é uma VPN de jogos como **Radmin VPN**, **Tailscale** ou **ZeroTier**. Os dois entram na mesma rede virtual e usam o IP virtual do host no `join`.
3. **Sem VPN:** o host precisa liberar/encaminhar a porta **TCP 5555** no roteador para o computador dele.

Se o Firewall do Windows perguntar quando o host iniciar, clique em **Permitir acesso**. Algumas redes (principalmente de escolas e empresas) isolam os computadores entre si; nesse caso, use VPN. Para testar a conexão antes, o amigo pode rodar `ping IP_DO_HOST`.

---

## Controles

| Ação | Tecla |
|---|---|
| Andar | `W` `A` `S` `D` |
| Olhar | Mouse |
| Pular | `Espaço` (segure para bunny hop) |
| Slide | `Shift` ou `C` (correndo, no chão) |
| Andar na parede | `W` encostado na parede, no ar |
| Pulo de parede | `Espaço` durante o wallrun |
| Dash no ar | `E` ou botão direito do mouse |
| Atirar | Botão esquerdo do mouse |
| Menu de opções | `M` |
| Fechar menu / sair | `Esc` |

---

## Mecânicas

**One shot.** Um tiro acerta e mata. Depois de atirar, há 0,75 s de recarga. Quem morre renasce no ponto de spawn mais distante do inimigo.

**Shotgun.** Cada tiro dispara 7 chumbinhos: o primeiro vai exatamente onde a mira aponta, e os outros 6 se espalham em um cone pequeno (1,6° por padrão). Acertar **qualquer** chumbinho já mata.

**Slide.** Correndo no chão, aperte `Shift`. Você ganha um impulso de velocidade e fica mais baixo (hitbox menor). Segure `Shift` para continuar deslizando; o slide termina quando a velocidade cai ou você solta a tecla. Pular durante o slide dá um impulso extra (**slide hop**).

**Wallrun.** No ar, encostado numa parede e segurando `W`, você corre pela parede com gravidade reduzida por até 2,5 s. A câmera inclina **para longe da parede** (parede à esquerda, câmera vira para a direita). `Espaço` faz um pulo para fora da parede.

**Dash no ar.** `E` lança você na direção para onde está olhando (inclusive para cima ou para baixo). Há **um dash por salto**: ele recarrega ao tocar o chão ou uma parede.

**Bunny hop e momento.** O pulo acontece **antes** do atrito do chão, então, **segurando `Espaço`**, você pula assim que pousa e **mantém a velocidade**. Para ganhar velocidade extra, faça strafe no ar: segure `W` + `A` (ou `D`) e gire o mouse para o mesmo lado. Existe um limite de velocidade horizontal no ar (28 m/s por padrão).

---

## HUD

Inspirada no estilo de hero shooters (design original, sem assets de terceiros):

- **Topo, centro:** placar com as eliminações de cada time.
- **Topo, direita:** kill feed com as últimas eliminações (5 s).
- **Centro:** mira dinâmica que abre com a velocidade e ao atirar, e hitmarker vermelho quando o tiro mata. Uma faixa de mensagem aparece ao eliminar alguém, ser eliminado ou se o amigo desconectar.
- **Embaixo, esquerda:** cartão do jogador com time, velocidade (número e medidor em segmentos), eliminações e mortes.
- **Embaixo, direita:** caixas das habilidades (shotgun com munição e recarga, dash, slide, parede). A borda é laranja quando está pronta, branca quando está em uso e cinza quando está carregando.
- **Menu (`M`):** sensibilidade X e Y. O valor vale só para quem mexeu e fica salvo em `sens_host.json` ou `sens_join.json`.

**Fonte do HUD (opcional):** coloque um arquivo `hud_font.ttf` (ou `.otf`) na pasta do jogo e ele será usado automaticamente.

---

## Configurações no código

As constantes ficam no início do arquivo, na seção `AJUSTES DE JOGO`:

| Constante | Padrão | O que faz |
|---|---|---|
| `SHOT_CD` | `0.75` | Tempo entre tiros, em segundos |
| `PELLETS` | `7` | Número de chumbinhos por tiro |
| `SPREAD` | `1.6` | Dispersão máxima, em graus (menor = mais preciso) |
| `AIR_STRAFE_CAP` | `1.6` | Quanto o strafe no ar soma por vez (bunny hop) |
| `AIR_STRAFE_ACCEL` | `70` | Rapidez com que o strafe soma velocidade |
| `MAX_HSPEED` | `28` | Velocidade horizontal máxima no ar |
| `MOSTRAR_DEBUG` | `True` | Mostra os contadores de FPS e de entidades do Ursina (`False` esconde) |

Outros valores úteis: `PORT` (porta da conexão, `5555`), `SPAWNS` (pontos de nascimento) e a lista de caixas do mapa (chamadas `add_box`).

---

## Desempenho

O jogo foi otimizado para rodar bem em computadores simples:

- **Mapa em uma única malha:** todas as caixas do mapa viram 1 objeto e 1 chamada de desenho (antes eram 16). A colisão continua usando a lista de caixas (`BOXES`).
- **Objetos reaproveitados:** rastros dos tiros, flash de dano, clarão do cano e kill feed usam objetos criados uma vez só e reutilizados. Nada é criado nem destruído durante a partida, então o número de entidades fica **constante**. (Uma versão anterior deixava 6 entidades "órfãs" a cada morte por causa do kill feed.)
- **HUD com cache:** a mira, o medidor de velocidade, as caixas de habilidade e os textos só são atualizados quando o valor muda.

Para acompanhar, deixe `MOSTRAR_DEBUG = True`: o contador de entidades do Ursina deve ficar parado durante a partida (o valor inicial é maior que antes porque os objetos reutilizáveis já nascem criados).

---

## Como o multiplayer funciona

- **Conexão:** uma única conexão TCP entre os dois jogadores. O host escuta na porta 5555 e o outro conecta. Uma thread em segundo plano recebe as mensagens, enquanto o jogo roda normalmente.
- **Mensagens:** linhas de JSON.

| Mensagem | Conteúdo |
|---|---|
| `s` | Posição, direção (yaw), altura, estado (chão, slide, parede, dash, ar), lado da parede e velocidade. Enviada 30 vezes por segundo. |
| `shot` | Linhas dos tiros, para desenhar os rastros no outro lado. |
| `hit` | Dano (100). Enviada por quem atirou quando algum chumbinho acerta. |
| `dead` | Enviada por quem morreu, para o outro somar a eliminação. |

- **Acerto:** calculado por **quem atira** (raios contra a caixa de colisão do inimigo e contra o mapa), e o outro apenas aceita o resultado.
- **Remoto:** o outro jogador é suavizado e animado por estado (correndo, deitado no slide, inclinado na parede, esticado no dash), porque o modelo não tem esqueleto.

---

## Estrutura do código

Tudo está em `fps_multiplayer.py`, na seguinte ordem:

1. **Rede:** leitura dos argumentos (`host` / `join`) e a classe `Net`.
2. **Mapa:** `add_box` (chão, paredes, torres, caixas), `build_map` (junta tudo numa malha só), `SPAWNS` e a colisão por caixas (`box_hit`, `probe_wall`, `ray_box`).
3. **Modelos 3D:** leitor de `.glb` (`load_glb`) e `find_asset`.
4. **Ajustes de jogo:** as constantes.
5. **Estado:** classes `P` (jogador local) e `R` (jogador remoto), times e modelos.
6. **HUD:** helpers (`q`, `para`, `txt`), mira, placar, cartão, habilidades, kill feed e `update_hud`.
7. **Menu:** sliders de sensibilidade e `toggle_menu`.
8. **Ações:** `shoot`, `tracer` (com pool de objetos), `respawn`, `air_strafe` e `input`.
9. **Loop principal:** `handle_net` (rede) e `update` (física, câmera, tiro, remoto, HUD).

---

## Solução de problemas

| Problema | O que fazer |
|---|---|
| `ModuleNotFoundError: No module named 'ursina'` | Instale com `pip install ursina` (no Windows: `py -3.12 -m pip install ursina`). Confirme que o Python usado para rodar é o mesmo em que instalou. |
| Erro ao instalar (`No matching distribution found for panda3d`) | O Python é muito novo. Instale o **Python 3.12** e use `py -3.12`. |
| A janela não abre no host | É o esperado: ela só abre quando o amigo conecta. |
| O amigo não consegue conectar | Confira se o host iniciou primeiro, se o IP está certo, se o Firewall permitiu o Python e se estão na mesma rede (ou use VPN). Teste com `ping`. |
| Os personagens/arma aparecem como cubos | Os `.glb` não estão na mesma pasta do script (ou com outro nome). Veja a mensagem no terminal. |
| O mouse está muito rápido ou lento | Aperte `M` e ajuste a sensibilidade X e Y. |
| Aparece "AMIGO DESCONECTOU" | A conexão caiu ou o outro jogador saiu. Feche e reinicie os dois (host primeiro) para jogar de novo. |

---

## Limitações conhecidas

- Apenas **2 jogadores** (1v1).
- Sem anti-cheat: o acerto é calculado por quem atira, então só jogue com quem você confia.
- O personagem não tem esqueleto, então não anda nem mexe os braços: a animação é por inclinação do corpo.
- Colisão por caixas simples (o mapa é feito de blocos).
- Não há som, partidas com fim definido nem tela de reconexão.
- A faca (`Bayonet`) ainda não foi implementada.

---

## Créditos

- **Ursina Engine** e **Panda3D**: motor do jogo.
- **Shotgun** e **Bayonet** — Quaternius.
- **Character Base** — madtrollstudio.

Confira a licença de cada modelo na página de onde foi baixado antes de redistribuir o projeto. Os modelos da Quaternius costumam ser de uso livre (CC0).
