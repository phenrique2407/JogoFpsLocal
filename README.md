# FPS Movimento — 1v1 multiplayer em Python

Um FPS 1v1 de movimentação rápida feito em **Python + Ursina**. Um tiro mata, e o foco do jogo é o movimento: **andar na parede**, **dash no ar**, **pulo duplo** e **bunny hop**. Dois jogadores jogam pela rede (mesma rede local, VPN ou porta liberada no roteador), sem servidor dedicado.

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
- **Movimentação:** wallrun com inclinação da câmera, **dash em qualquer direção com até 3 cargas**, **pulo duplo**, pulo de parede, bunny hop e strafe no ar.
- **Times por cor (degradê):** o host é o **Time 1 (azul)** e quem entra é o **Time 2 (laranja)**, cada um com seu degradê de cima para baixo.
- **Modelos 3D** (`.glb`): a shotgun na mão e o **outro jogador com esqueleto e animações** (parado, andando, correndo, no ar, pulo duplo...), pintado com o degradê do time. Personagem e shotgun usam **cel shading** (luz em faixas e contorno escuro). Se os arquivos não existirem, o jogo usa formas simples.
- **HUD estilizada** com a fonte **Jaro**: KD, kill feed animado, mira dinâmica, **velocímetro em km/h (velocidade real) com os itens embaixo (shotgun, dash com cargas e pulo duplo)** e hitmarker.
- **Menu de opções (`M`)** com sensibilidade X e Y separadas, salva por jogador.

---

## Organização da pasta

Deixe **tudo junto**, nos dois computadores (o jogo procura os arquivos a partir da pasta do script):

```
fps-movimento/
├── fps_multiplayer.py          ← o jogo (todo o código)
├── README.md                   ← este arquivo
│
├── assets/
│   ├── fonts/
│   │   ├── Jaro-VariableFont_opsz.ttf   ← fonte do HUD (Google Fonts)
│   │   └── OFL.txt                      ← licença da fonte
│   ├── models/
│   │   ├── Shotgun_by_Quaternius_-_DcNE0HVdW8.glb                      ← arma na mão
│   │   └── Animated_Base_Character_by_Quaternius_-_cwYvO5UauX.glb      ← outro jogador (com animações)
│   ├── items/
│   │   ├── shotgun.png  dash.png  double_jump.png   ← ícones dos itens (150 x 100, em 2x)
│   │   ├── dash_x1_time1.png ... dash_x3_time2.png  ← selos "x1/x2/x3" do dash (um por time)
│   │   └── svg/                                     ← os SVGs originais dos selos
│   ├── speedometer/
│   │   ├── barra_ativa_time1.png  barra_ativa_time2.png   ← barra acesa (degradê do time)
│   │   ├── barra_inativa.png                              ← barra apagada (cinza)
│   │   ├── sublinhado_time1.png   sublinhado_time2.png    ← linha embaixo do medidor
│   │   └── svg/                                           ← os SVGs originais (vetoriais)
│   ├── killfeed/
│   │   ├── killfeed_time1.png  killfeed_time2.png   ← "P1 [arma] P2" e "P2 [arma] P1"
│   │   └── svg/
│   └── kd/
│       ├── icone_kills.png  icone_mortes.png        ← ícones do KD (branco, 24 x 24 em 4x)
│       └── svg/
│
├── sens_host.json        (gerado) sensibilidade salva de quem hospeda
└── sens_join.json        (gerado) sensibilidade salva de quem entra
```

Observações:

- O jogo acha a fonte e os modelos **pelo nome** (`Jaro*.ttf`, `*Shotgun*.glb`, `*Animated*Character*.glb`), na pasta do script ou em qualquer subpasta de `assets/`. Você pode reorganizar, desde que os nomes continuem contendo essas palavras.
- **Imagens do HUD:** tudo foi desenhado em **SVG** (vetorial) e o jogo carrega os **PNGs em 4x** gerados a partir deles (o Ursina não lê SVG), então ficam nítidos mesmo em telas grandes. Os SVGs originais estão nas pastas `svg/` de cada item. Para trocar o visual, edite o SVG, exporte o PNG com o mesmo nome e substitua.
- **Velocímetro:** é montado em tempo real com **20 barras**: cada barra usa `barra_ativa_*` (acesa) ou `barra_inativa` (apagada), mais o `sublinhado_*`. Cada jogador usa as peças do **seu** time (`time1` = host, `time2` = quem entra).
- Se algo estiver faltando, o jogo **não quebra**: sem fonte usa a padrão, sem modelos usa cubos, sem as imagens do velocímetro mostra só o número em texto, sem os ícones usa caixas cinza e sem as imagens do kill feed escreve só o nome do time. O motivo aparece no terminal.
- Os arquivos `sens_*.json` são criados quando você fecha o menu de opções pela primeira vez. Pode apagá-los para voltar à sensibilidade padrão.
- Cada jogador precisa ter a pasta completa. Tudo é só visual e local; não há troca de arquivos pela rede.

---

## Dependências

| O quê | Versão | Observação |
|---|---|---|
| **Python** | 3.9 a 3.12 recomendado | Foi testado com 3.12. Versões muito novas podem não ter pacote do Panda3D ainda. |
| **ursina** | a mais recente | Instala sozinho o Panda3D e as outras bibliotecas que ele usa. |

Não há mais nada para instalar. O **Pillow** (usado para gerar o número do velocímetro) já vem junto com o ursina. O leitor de `.glb` (incluindo esqueleto e animações) é do próprio jogo (sem `numpy`, `panda3d-gltf` ou outras bibliotecas), e o multiplayer usa apenas a biblioteca padrão do Python (`socket`, `threading`, `json`, `struct`).

O personagem animado usa um shader simples (OpenGL 3.0 ou mais novo, o que qualquer placa de vídeo atual tem). Se ele não funcionar no seu computador, o jogo avisa no terminal e mostra o outro jogador com formas simples, sem travar.

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

**Quem entra (jogador laranja):**

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
| Pulo duplo | `Espaço` de novo, **no ar** |
| Andar na parede | `W` encostado na parede, no ar |
| Pulo de parede | `Espaço` durante o wallrun |
| Dash no ar | `E` ou botão direito do mouse (sozinho = para onde você olha) |
| Dash para os lados / trás | `E` + `A`, `D` ou `S` (e `W` + `A`/`D` para diagonal) |
| Atirar | Botão esquerdo do mouse |
| Menu de opções | `M` |
| Fechar menu / sair | `Esc` |

---

## Mecânicas

**One shot.** Um tiro acerta e mata. Depois de atirar, há 0,75 s de recarga. Quem morre renasce no ponto de spawn mais distante do inimigo.

**Shotgun.** Cada tiro dispara 7 chumbinhos: o primeiro vai exatamente onde a mira aponta, e os outros 6 se espalham em um cone pequeno (1,6° por padrão). Acertar **qualquer** chumbinho já mata.

**Pulo duplo.** No ar, aperte `Espaço` de novo para dar um segundo impulso (um por salto). Ele volta **quando você toca o chão ou uma parede**. Se você apertar `Espaço` já bem perto do chão, o jogo entende como um pulo normal adiantado (para o bunny hop) e **não gasta** o pulo duplo.

**Wallrun.** No ar, encostado numa parede e segurando `W`, você corre pela parede com gravidade reduzida por até 2,5 s. A câmera inclina **para longe da parede** (parede à esquerda, câmera vira para a direita). `Espaço` faz um pulo para fora da parede.

**Dash no ar.** Você guarda até **3 cargas** de dash. Cada carga leva **3 segundos** para voltar (uma de cada vez) e, depois de cada dash, há **0,1 s de recuperação** antes de poder usar a próxima. O dash **não** recarrega ao tocar o chão ou a parede, só com o tempo. A direção depende das teclas: **sem tecla (ou só `W`) o dash vai para onde você está olhando**, inclusive para cima ou para baixo (é exclusivo do dash para frente); com `A`/`D`/`S` ele vai para o lado ou para trás, na horizontal; `W` + `A`/`D` faz diagonal para frente. O dash só funciona **no ar**.

**Bunny hop e momento.** O pulo acontece **antes** do atrito do chão, então, **segurando `Espaço`**, você pula assim que pousa e **mantém a velocidade**. Para ganhar velocidade extra, faça strafe no ar: segure `W` + `A` (ou `D`) e gire o mouse para o mesmo lado. Existe um limite de velocidade **total** (`MAX_SPEED`, 28 m/s por padrão): é a velocidade máxima do jogo e também o que enche todas as barras do velocímetro.

**Velocidades do jogo:** correr no chão = 9 m/s (32 km/h); andar na parede = até 16 m/s (58 km/h); dash = 24 m/s (86 km/h); limite máximo (bunny hop/strafe e queda) = 28 m/s (100,8 km/h).

---

## HUD

Design original, inspirado no estilo de hero shooters (sem assets de terceiros), com a fonte **Jaro**:

- **Cores dos times:** degradês de cima para baixo. **Time 1 (host):** `#17B8F3` → `#162FAD`. **Time 2 (quem entra):** `#F37E17` → `#AD1616`. A cor de destaque do HUD (bordas, faixas, mensagens, menu) é a do **seu** time. O personagem do adversário também é pintado com o degradê do time dele.
- **Topo, direita (colado na quina):** o **KD**, com ícone de alvo + suas eliminações e ícone de caveira + suas mortes. Quando um número sobe, ele dá um **"pop"** (cresce e volta). Logo abaixo, o **kill feed** (`P1 [arma] P2` ou `P2 [arma] P1`, conforme quem matou), com fundo preto quase transparente. Cada entrada **entra pela direita, vindo de fora da tela, com ease-out de 250 ms**, e some depois de 5 s.
- **Centro:** mira dinâmica que abre com a velocidade e ao atirar, e hitmarker vermelho quando o tiro mata. Uma faixa de mensagem aparece ao eliminar alguém, ser eliminado ou se o amigo desconectar.
- **Embaixo, esquerda:** o **velocímetro**: 20 caixinhas que vão enchendo, com o número em **km/h** ao lado. Ele mostra a **velocidade real** do personagem (a total, incluindo a vertical: queda e pulo), convertida de m/s para km/h (1 m/s = 3,6 km/h). A escala vai de 0 até a **velocidade máxima permitida** do jogo (28 m/s = 100,8 km/h): cada barra vale cerca de 5 km/h e acende ao chegar no valor dela; com todas acesas você está no limite. Para contar só a velocidade horizontal, mude `SPEED_3D` para `False`.
- **Embaixo do velocímetro:** os três **itens**: shotgun, dash e pulo duplo. Ao usar um item, ele **aumenta um pouquinho e acende**. Enquanto recarrega, uma **faixa escura desce de cima para baixo** sobre o ícone. A shotgun recarrega em 0,75 s e o pulo duplo volta ao tocar o chão ou a parede. O **dash** mostra um selo **x1 / x2 / x3** na quina de cima do ícone, com as cargas disponíveis; **quando ganha uma carga, o selo dá um "pop"**. Enquanto alguma carga ainda está recarregando, a faixa escura aparece (mais clara se ainda houver carga para usar, e mais escura quando não há nenhuma).
- **Menu (`M`):** sensibilidade X e Y. O valor vale só para quem mexeu e fica salvo em `sens_host.json` ou `sens_join.json`.

**Mudar nomes e cores dos times:** edite o dicionário `TEAM` no código (cor de cima, cor de baixo e nome de cada time). Os PNGs do velocímetro têm as cores desenhadas, então precisam ser trocados junto.

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
| `MAX_SPEED` | `28` | Velocidade máxima do jogo, em m/s (limite do bunny hop e fundo de escala do velocímetro) |
| `SPEED_3D` | `True` | O velocímetro conta também a velocidade vertical (`False` = só a horizontal) |
| `MOSTRAR_DEBUG` | `True` | Mostra os contadores de FPS e de entidades do Ursina (`False` esconde) |
| `DJUMP_SPEED` | `8.5` | Impulso do pulo duplo |
| `DASH_MAX_CHARGES` | `3` | Cargas de dash guardadas |
| `DASH_RECHARGE` | `3.0` | Segundos para recuperar cada carga de dash |
| `DASH_GAP` | `0.1` | Recuperação (s) depois de cada dash, antes de poder usar a próxima carga |
| `SPD_W` | `0.50` | Tamanho do velocímetro e dos itens (maior = conjunto maior) |
| `FEED_IN` / `FEED_LIFE` / `FEED_BG` | `.25` / `5.0` / `Color(0,0,0,.20)` | Entrada (s), tempo na tela (s) e fundo do kill feed |
| `OUTLINE_CHAR` / `OUTLINE_GUN` | `0.014` / `0.0045` | Espessura do contorno (cel shading) do personagem e da shotgun |
| `CHAR_YAW` | `90` | Giro do modelo do personagem (se ele aparecer olhando para o lado errado, mude aqui) |

Outros valores úteis: `PORT` (porta da conexão, `5555`), `SPAWNS` (pontos de nascimento) e a lista de caixas do mapa (chamadas `add_box`).

---

## Desempenho

O jogo foi otimizado para rodar bem em computadores simples:

- **Mapa em uma única malha:** todas as caixas do mapa viram 1 objeto e 1 chamada de desenho (antes eram 16). A colisão continua usando a lista de caixas (`BOXES`).
- **Objetos reaproveitados:** rastros dos tiros, flash de dano, clarão do cano e kill feed usam objetos criados uma vez só e reutilizados. Nada é criado nem destruído durante a partida, então o número de entidades fica **constante**. (Uma versão anterior deixava 6 entidades "órfãs" a cada morte por causa do kill feed.)
- **HUD com cache:** a mira, as barras do velocímetro, os itens, o KD e os textos só são atualizados quando o valor muda.
- **Cel shading:** é feito na placa de vídeo (faixas de luz no shader e o contorno é uma segunda cópia da malha), então quase não pesa no processador.

- **Personagem animado na placa de vídeo:** o jogo calcula as poses das animações uma vez na abertura (cerca de 1 segundo) e guarda numa textura; depois, quem deforma a malha é a GPU. O custo por frame em Python é praticamente zero.

Para acompanhar, deixe `MOSTRAR_DEBUG = True`: o contador de entidades do Ursina deve ficar parado durante a partida (o valor inicial é maior que antes porque os objetos reutilizáveis já nascem criados).

---

## Como o multiplayer funciona

- **Conexão:** uma única conexão TCP entre os dois jogadores. O host escuta na porta 5555 e o outro conecta. Uma thread em segundo plano recebe as mensagens, enquanto o jogo roda normalmente.
- **Mensagens:** linhas de JSON.

| Mensagem | Conteúdo |
|---|---|
| `s` | Posição, direção (yaw), altura, estado (chão, parede, dash, ar), lado da parede, velocidade, contador de pulos duplos e direção do dash (para a animação). Enviada 30 vezes por segundo. |
| `shot` | Linhas dos tiros, para desenhar os rastros no outro lado. |
| `hit` | Dano (100). Enviada por quem atirou quando algum chumbinho acerta. |
| `dead` | Enviada por quem morreu, para o outro somar a eliminação. |

- **Acerto:** calculado por **quem atira** (raios contra a caixa de colisão do inimigo e contra o mapa), e o outro apenas aceita o resultado.
- **Remoto:** o outro jogador é suavizado e a animação é escolhida pelo estado e pela velocidade: parado (idle), andando, trotando ou correndo (sprint), no ar, pulo duplo, e inclinado na parede e no dash.

---

## Estrutura do código

Tudo está em `fps_multiplayer.py`, na seguinte ordem:

1. **Rede:** leitura dos argumentos (`host` / `join`) e a classe `Net`.
2. **Mapa:** `add_box` (chão, paredes, torres, caixas), `build_map` (junta tudo numa malha só), `SPAWNS` e a colisão por caixas (`box_hit`, `probe_wall`, `ray_box`).
3. **Modelos 3D:** leitor de `.glb` estático (`load_glb_np`, usado na shotgun), personagem animado (`build_char`, `AnimChar`), shaders de cel shading e `find_asset`.
4. **Ajustes de jogo:** as constantes.
5. **Estado:** classes `P` (jogador local) e `R` (jogador remoto), times e modelos.
6. **HUD:** helpers (`q`, `para`, `txt`), mira, velocímetro, itens (com o selo de cargas do dash), KD, kill feed animado e `update_hud`.
7. **Menu:** sliders de sensibilidade e `toggle_menu`.
8. **Ações:** `shoot`, `tracer` (com pool de objetos), `respawn`, `air_strafe`, `ground_close`, `dash_direction` e `input` (incluindo o pulo duplo e o dash acumulado).
9. **Loop principal:** `handle_net` (rede) e `update` (física, câmera, tiro, remoto, HUD).

---

## Solução de problemas

| Problema | O que fazer |
|---|---|
| `ModuleNotFoundError: No module named 'ursina'` | Instale com `pip install ursina` (no Windows: `py -3.12 -m pip install ursina`). Confirme que o Python usado para rodar é o mesmo em que instalou. |
| Erro ao instalar (`No matching distribution found for panda3d`) | O Python é muito novo. Instale o **Python 3.12** e use `py -3.12`. |
| A janela não abre no host | É o esperado: ela só abre quando o amigo conecta. |
| O amigo não consegue conectar | Confira se o host iniciou primeiro, se o IP está certo, se o Firewall permitiu o Python e se estão na mesma rede (ou use VPN). Teste com `ping`. |
| O outro jogador aparece como cubos | O personagem animado não carregou (arquivo `*Animated*Character*.glb` ausente ou placa de vídeo sem suporte ao shader). O terminal mostra o motivo. |
| A arma aparece como um bloco simples | Os `.glb` não estão na pasta do jogo (ou `assets/`) ou estão com outro nome. Veja a mensagem no terminal. |
| A fonte do HUD não é a Jaro | O arquivo `Jaro-VariableFont_opsz.ttf` não foi encontrado (precisa estar na pasta do jogo ou em `assets/`). O jogo usa a fonte padrão e avisa no terminal. |
| O velocímetro aparece só como texto | As imagens de `assets/speedometer` (`barra_ativa_*`, `barra_inativa`, `sublinhado_*`) não foram encontradas. |
| O mouse está muito rápido ou lento | Aperte `M` e ajuste a sensibilidade X e Y. |
| Aparece "AMIGO DESCONECTOU" | A conexão caiu ou o outro jogador saiu. Feche e reinicie os dois (host primeiro) para jogar de novo. |

---

## Limitações conhecidas

- Apenas **2 jogadores** (1v1).
- Sem anti-cheat: o acerto é calculado por quem atira, então só jogue com quem você confia.
- O personagem do adversário não segura a arma (só a sua shotgun aparece, em primeira pessoa) e não tem animação de atirar.
- Colisão por caixas simples (o mapa é feito de blocos).
- Não há som, partidas com fim definido nem tela de reconexão.
- A faca (`Bayonet`) ainda não foi implementada.

---

## Créditos

- **Ursina Engine** e **Panda3D**: motor do jogo.
- **Personagem:** [Animated Base Character](https://poly.pizza/m/cwYvO5UauX) by [Quaternius](https://poly.pizza/u/Quaternius) [[CC-BY](https://creativecommons.org/licenses/by/3.0/)] via Poly Pizza. O jogo lê o modelo e as animações do arquivo original e **altera apenas as cores** (aplica o degradê do time). Essa atribuição também aparece no menu do jogo (`M`).
- **Shotgun** — Quaternius (confira a licença na página de origem do modelo).
- **Jaro** — fonte do Google Fonts, licença SIL Open Font License 1.1 (`assets/fonts/OFL.txt`).
- **Ícones, selos, velocímetro, kill feed e KD:** arte própria do projeto (SVG).

Confira a licença de cada modelo na página de onde foi baixado antes de redistribuir o projeto. O modelo do personagem é **CC-BY**: se você redistribuir o jogo, mantenha a atribuição acima.
