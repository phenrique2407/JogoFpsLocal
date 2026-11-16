"""
FPS MOVIMENTO - 1v1 multiplayer (Python + Ursina)

Instalar:   pip install ursina
Host:       python fps_multiplayer.py host
Amigo:      python fps_multiplayer.py join IP_DO_HOST
(sem argumentos, o jogo pergunta)

CONTROLES
  WASD ........ andar          Mouse ....... olhar
  ESPACO ...... pular / pular da parede
  SHIFT ou C .. deslizar (slide) correndo no chao
  BUNNY HOP ... segure ESPACO ao cair (pula sozinho, sem perder velocidade);
                no ar, mova o mouse para o lado e segure A ou D (strafe) para ganhar velocidade
  Parede + W .. andar na parede (wallrun) quando esta no ar encostado
  E / botao direito .. dash no ar (1 por salto; recarrega no chao ou na parede)
  Botao esquerdo .. atirar (one shot: 1 tiro mata, recarga de 0.75s)
  M ........... menu de opcoes (sensibilidade X e Y)
  ESC ......... fecha o menu / sai
"""
import builtins
import sys

ask = builtins.input  # Ursina sobrescreve "input", entao guardamos o original

# ----------------------------------------------------------------- REDE
role, host_ip, PORT = None, None, 5555
if len(sys.argv) >= 2:
    role = sys.argv[1].lower()
    host_ip = sys.argv[2] if len(sys.argv) >= 3 else None
if role not in ("host", "join"):
    role = "host" if ask("Digite 'host' para hospedar ou 'join' para entrar: ").strip().lower().startswith("h") else "join"
if role == "join" and not host_ip:
    host_ip = ask("IP do host: ").strip()

import glob, json, math, os, random, socket, struct, threading
from ursina import *


class Net:
    def __init__(self):
        self.inbox, self.lock = [], threading.Lock()
        if role == "host":
            srv = socket.socket()
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("0.0.0.0", PORT))
            srv.listen(1)
            print(f"Aguardando seu amigo na porta {PORT}...")
            self.sock, addr = srv.accept()
            print("Amigo conectado:", addr)
        else:
            print("Conectando em", host_ip)
            self.sock = socket.create_connection((host_ip, PORT), timeout=15)
            self.sock.settimeout(None)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        threading.Thread(target=self._recv, daemon=True).start()

    def _recv(self):
        buf = b""
        try:
            while True:
                d = self.sock.recv(4096)
                if not d:
                    break
                buf += d
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    with self.lock:
                        self.inbox.append(json.loads(line))
        except OSError:
            pass
        with self.lock:
            self.inbox.append({"t": "bye"})

    def send(self, m):
        try:
            self.sock.sendall((json.dumps(m) + "\n").encode())
        except OSError:
            pass

    def poll(self):
        with self.lock:
            m, self.inbox = self.inbox, []
        return m


net = Net()

# ----------------------------------------------------------------- MAPA
app = Ursina(title="FPS Movimento", borderless=False)
window.exit_button.visible = False
mouse.locked = True
Sky()

BOXES = []  # (minx,miny,minz,maxx,maxy,maxz)


def add_box(cx, cy, cz, sx, sy, sz, col):
    BOXES.append((cx - sx / 2, cy - sy / 2, cz - sz / 2, cx + sx / 2, cy + sy / 2, cz + sz / 2))
    Entity(model="cube", position=(cx, cy, cz), scale=(sx, sy, sz), color=col,
           texture="white_cube", texture_scale=(max(sx, sz) / 2, sy / 2 + 0.01))


add_box(0, -0.5, 0, 62, 1, 62, color.dark_gray)                     # chao
for args in [(0, 6, -30.5, 62, 12, 1), (0, 6, 30.5, 62, 12, 1),
             (-30.5, 6, 0, 1, 12, 62), (30.5, 6, 0, 1, 12, 62)]:    # paredes externas
    add_box(*args, color.gray)
add_box(0, 4, 0, 1, 8, 24, color.azure)                              # paredes de wallrun
add_box(-14, 4, 12, 14, 8, 1, color.azure)
add_box(14, 4, -12, 14, 8, 1, color.azure)
add_box(-18, 2, -14, 8, 4, 8, color.orange)                          # torres
add_box(18, 2, 14, 8, 4, 8, color.orange)
for c in [(-8, 6), (8, -6)]:
    add_box(c[0], 0.5, c[1], 3, 1, 3, color.olive)                   # degraus
for c in [(-4, -18), (5, 20), (22, -4), (-22, 5)]:
    add_box(c[0], 0.6, c[1], 2, 1.2, 2, color.brown)                 # caixas

SPAWNS = [(-26, 0, 0), (26, 0, 0)]


def box_hit(p, h, dx=0.0, dz=0.0):
    x0, x1 = p[0] - .3 + dx, p[0] + .3 + dx
    y0, y1 = p[1], p[1] + h
    z0, z1 = p[2] - .3 + dz, p[2] + .3 + dz
    for b in BOXES:
        if x1 > b[0] and x0 < b[3] and y1 > b[1] and y0 < b[4] and z1 > b[2] and z0 < b[5]:
            return b
    return None


def probe_wall(p, h):
    if p[1] < 0.2:
        return None
    for dx, dz, n in ((.12, 0, (-1, 0)), (-.12, 0, (1, 0)), (0, .12, (0, -1)), (0, -.12, (0, 1))):
        if box_hit(p, h, dx, dz):
            return n
    return None


def ray_box(o, d, mn, mx):
    tmin, tmax = 0.0, 1e9
    for i in range(3):
        if abs(d[i]) < 1e-9:
            if o[i] < mn[i] or o[i] > mx[i]:
                return None
        else:
            t1, t2 = (mn[i] - o[i]) / d[i], (mx[i] - o[i]) / d[i]
            if t1 > t2:
                t1, t2 = t2, t1
            tmin, tmax = max(tmin, t1), min(tmax, t2)
            if tmin > tmax:
                return None
    return tmin


# ----------------------------------------------------------------- MODELOS 3D (.glb)
# Leitor proprio (sem bibliotecas extras): le malha + cor dos materiais e converte para o Ursina.
def _mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _node_matrix(n):
    if "matrix" in n:
        m = n["matrix"]
        return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    tx, ty, tz = n.get("translation", (0, 0, 0))
    qx, qy, qz, qw = n.get("rotation", (0, 0, 0, 1))
    sx, sy, sz = n.get("scale", (1, 1, 1))
    r = [[1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
         [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
         [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)]]
    return [[r[0][0] * sx, r[0][1] * sy, r[0][2] * sz, tx],
            [r[1][0] * sx, r[1][1] * sy, r[1][2] * sz, ty],
            [r[2][0] * sx, r[2][1] * sy, r[2][2] * sz, tz],
            [0, 0, 0, 1]]


def _accessor(j, blob, idx):
    a = j["accessors"][idx]
    bv = j["bufferViews"][a["bufferView"]]
    nc = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
    fmt = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}[a["componentType"]]
    size = struct.calcsize(fmt) * nc
    stride = bv.get("byteStride") or size
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return [struct.unpack_from("<" + fmt * nc, blob, base + i * stride) for i in range(a["count"])]


def _read_glb(path):
    data = open(path, "rb").read()
    off, j, blob = 12, None, b""
    while off < len(data):
        ln, ct = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + ln]
        off += 8 + ln
        if ct == 0x4E4F534A:
            j = json.loads(chunk)
        elif ct == 0x004E4942:
            blob = chunk
    prims = []

    def walk(ni, parent):
        n = j["nodes"][ni]
        m = _mat_mul(parent, _node_matrix(n))
        if "mesh" in n:
            for pr in j["meshes"][n["mesh"]]["primitives"]:
                pos = _accessor(j, blob, pr["attributes"]["POSITION"])
                nor = (_accessor(j, blob, pr["attributes"]["NORMAL"]) if "NORMAL" in pr["attributes"]
                       else [(0, 1, 0)] * len(pos))
                idx = [i[0] for i in _accessor(j, blob, pr["indices"])] if "indices" in pr else list(range(len(pos)))
                col = [1, 1, 1]
                if "material" in pr:
                    col = j["materials"][pr["material"]].get("pbrMetallicRoughness", {}).get("baseColorFactor", [1, 1, 1, 1])[:3]
                wp = [tuple(sum(m[r][c] * v[c] for c in range(3)) + m[r][3] for r in range(3)) for v in pos]
                wn = []
                for v in nor:
                    t = [sum(m[r][c] * v[c] for c in range(3)) for r in range(3)]
                    l = math.sqrt(sum(x * x for x in t)) or 1
                    wn.append(tuple(x / l for x in t))
                prims.append((wp, wn, col, idx))
        for c in n.get("children", []):
            walk(c, m)

    ident = [[1 if r == c else 0 for c in range(4)] for r in range(4)]
    for sc in j["scenes"][j.get("scene", 0)]["nodes"]:
        walk(sc, ident)
    return prims


def load_glb(path, yaw=0, mode="feet", size=1.8, tint=None):
    """Devolve um Mesh do Ursina. mode='feet': altura=size, pes em y=0, centrado em x/z.
    mode='center': maior dimensao=size, centrado na origem. yaw gira o modelo no eixo Y."""
    prims = _read_glb(path)
    c, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def conv(v):  # glTF (destro) -> Ursina (esquerdo): espelha X; depois gira em Y
        x, y, z = -v[0], v[1], v[2]
        return (x * c + z * sn, y, -x * sn + z * c)

    conv_p = [[conv(v) for v in pr[0]] for pr in prims]
    conv_n = [[conv(v) for v in pr[1]] for pr in prims]
    allp = [v for pl in conv_p for v in pl]
    mn = [min(v[i] for v in allp) for i in range(3)]
    mx = [max(v[i] for v in allp) for i in range(3)]
    if mode == "feet":
        k = size / (mx[1] - mn[1])
        off = ((mn[0] + mx[0]) / 2, mn[1], (mn[2] + mx[2]) / 2)
    else:
        k = size / max(mx[i] - mn[i] for i in range(3))
        off = tuple((mn[i] + mx[i]) / 2 for i in range(3))
    light = (.30, .85, .35)
    ll = math.sqrt(sum(x * x for x in light))
    light = tuple(x / ll for x in light)
    verts, tris, cols = [], [], []
    for pr, pl, nl in zip(prims, conv_p, conv_n):
        base = tint if tint is not None else tuple(max(0, ch) ** (1 / 2.2) for ch in pr[2])  # linear -> sRGB
        start = len(verts)
        for v, n in zip(pl, nl):
            verts.append(((v[0] - off[0]) * k, (v[1] - off[1]) * k, (v[2] - off[2]) * k))
            sh = .5 + .5 * max(0.0, n[0] * light[0] + n[1] * light[1] + n[2] * light[2])
            cols.append(Color(base[0] * sh, base[1] * sh, base[2] * sh, 1))
        idx = pr[3]
        for i in range(0, len(idx) - 2, 3):
            tris.append((start + idx[i], start + idx[i + 2], start + idx[i + 1]))  # espelhar inverte o sentido
    return Mesh(vertices=verts, triangles=tris, colors=cols)


def find_asset(pattern):
    base = os.path.dirname(os.path.abspath(__file__))
    for d in (base, os.path.join(base, "assets")):
        hits = sorted(glob.glob(os.path.join(d, pattern)))
        if hits:
            return hits[0]
    return None


# ----------------------------------------------------------------- AJUSTES DE JOGO
SHOT_CD = .75        # tempo entre tiros (s)
PELLETS = 7          # "chumbinhos" da shotgun (1 no centro + 6 em volta)
SPREAD = 1.6         # dispersao maxima em GRAUS (menor = mais preciso)
AIR_STRAFE_CAP = 1.6     # quanto o strafe no ar consegue somar por vez (bunny hop)
AIR_STRAFE_ACCEL = 70    # velocidade com que isso e somado
MAX_HSPEED = 28          # velocidade horizontal maxima no ar


# ----------------------------------------------------------------- ESTADO
class P:  # jogador local
    p = list(SPAWNS[0 if role == "host" else 1])
    v = [0.0, 0.0, 0.0]
    yaw = 90.0 if role == "host" else -90.0
    pitch = 0.0
    roll = 0.0
    h = 1.8
    eye = 1.6
    ground = False
    sliding = False
    slide_cd = 0.0
    wallrun = False
    wall_n = (0, 0)
    wall_t = 0.0
    wall_cd = 0.0
    dash_ready = True
    dash_t = 0.0
    dash_dir = (0, 0, 1)
    hp = 100
    shoot_cd = 0.0
    kills = 0
    deaths = 0
    net_t = 0.0
    jump_buf = 0.0
    wall_side = 0


class R:  # jogador remoto
    p = list(SPAWNS[1 if role == "host" else 0])
    sp = list(p)
    h = 1.8
    yaw = 0.0
    online = True
    st = 0      # 0 chao, 1 slide, 2 parede, 3 dash, 4 ar
    ws = 0      # lado da parede (+1 direita, -1 esquerda)
    spd = 0.0
    tx = tz = t = 0.0


# Host = AZUL, quem entra = VERMELHO
TEAM = {"host": (color.azure, color.cyan, "AZUL"), "join": (color.red, color.orange, "VERMELHO")}
MY_TEAM = TEAM[role]
OTHER_TEAM = TEAM["join" if role == "host" else "host"]
R.root = Entity()                       # fica na altura do quadril (gira em torno dele)
R.mesh = Entity(parent=R.root, y=-.9)   # pes ficam em y = 0
_cp = find_asset("*Character*.glb")
_char_ok = False
if _cp:
    try:
        _tint = (OTHER_TEAM[0][0] * .9, OTHER_TEAM[0][1] * .9, OTHER_TEAM[0][2] * .9)
        Entity(parent=R.mesh, model=load_glb(_cp, yaw=0, mode="feet", size=1.8, tint=_tint), double_sided=True)
        _char_ok = True
    except Exception as e:
        print("Personagem .glb nao carregou, usando modelo simples:", e)
if not _char_ok:
    Entity(parent=R.mesh, model="cube", color=OTHER_TEAM[0], scale=(.6, 1.8, .6), y=.9)
    Entity(parent=R.mesh, model="sphere", color=OTHER_TEAM[1], scale=.45, y=1.65)

rig = Entity()
head = Entity(parent=rig)
camera.parent = head
camera.position = (0, 0, 0)
camera.rotation = (0, 0, 0)
camera.fov = 90
camera.clip_plane_near = .05
GUN_POS = (.30, -.27, .62)
gun = Entity(parent=camera, position=GUN_POS, rotation_y=-2)
_gp = find_asset("*Shotgun*.glb")
_gun_ok = False
muzzle = Entity(parent=gun, model="sphere", color=Color(1, .85, .4, .9), scale=.14, position=(0, .03, .52), enabled=False)
if _gp:
    try:
        Entity(parent=gun, model=load_glb(_gp, yaw=90, mode="center", size=.85), double_sided=True)
        _gun_ok = True
    except Exception as e:
        print("Shotgun .glb nao carregou, usando modelo simples:", e)
if not _gun_ok:
    Entity(parent=gun, model="cube", scale=(.1, .12, .5), color=color.black66)

# ----------------------------------------------------------------- HUD (estilo hero shooter)
_font = find_asset("hud_font.*")  # opcional: um arquivo hud_font.ttf/.otf ao lado do jogo troca a fonte do HUD
if _font and _font.lower().endswith((".ttf", ".otf")):
    try:
        Text.default_font = _font
    except Exception:
        pass

RX = window.aspect_ratio / 2          # borda direita da tela (coordenadas de UI)
OW_ORANGE = Color(.98, .62, .10, 1)
PANEL_DK = Color(.02, .03, .06, .88)
WHITE = Color(1, 1, 1, 1)
DIM = Color(1, 1, 1, .6)
TEAM_UI = {"host": Color(.20, .58, 1, 1), "join": Color(.94, .24, .27, 1)}
MY_UI = TEAM_UI[role]
OTHER_UI = TEAM_UI["join" if role == "host" else "host"]
hud_root = Entity(parent=camera.ui)   # tudo do HUD fica aqui (some quando o menu abre)


def q(x, y, w, h, col, z=0, parent=None, origin=(-.5, -.5)):
    e = Entity(parent=parent or hud_root, model="quad", origin=origin, color=col, scale=(w, h))
    e.x, e.y, e.z = x, y, z
    return e


def para(x, y, w, h, col, slant=.012, z=0, parent=None):
    """Paralelogramo (painel inclinado)."""
    m = Mesh(vertices=[(0, 0, 0), (w, 0, 0), (w + slant, h, 0), (slant, h, 0)], triangles=[(0, 1, 2), (0, 2, 3)])
    e = Entity(parent=parent or hud_root, model=m, color=col, double_sided=True)
    e.x, e.y, e.z = x, y, z
    return e


def txt(s_, x, y, scale=1.0, col=WHITE, origin=(-.5, 0), parent=None, z=-.01):
    t = Text(s_, parent=parent or hud_root, origin=origin, scale=scale, color=col)
    t.x, t.y, t.z = x, y, z
    return t


def set_txt(t, s_):
    if getattr(t, "_v", None) != s_:
        t.text = s_
        t._v = s_


# ---- mira dinamica (abre com a velocidade e ao atirar)
XH, XH_OL = Color(1, 1, 1, .95), Color(0, 0, 0, .55)
xh_parts = []
for _dx, _dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
    _v = _dx == 0
    _ol = q(0, 0, .0075 if _v else .019, .019 if _v else .0075, XH_OL, z=.002, origin=(0, 0))
    _fg = q(0, 0, .0035 if _v else .015, .015 if _v else .0035, XH, z=.001, origin=(0, 0))
    xh_parts.append((_dx, _dy, _ol, _fg))
q(0, 0, .004, .004, XH, origin=(0, 0))
xh_kick, hm_t, msg_t, hint_t = 0.0, 0.0, 0.0, 14.0


def set_crosshair(gap):
    for dx, dy, ol, fg in xh_parts:
        d = gap + .008
        ol.x = fg.x = dx * d
        ol.y = fg.y = dy * d


# ---- hitmarker (X vermelho quando o tiro mata)
hm = Entity(parent=hud_root, enabled=False)
for _sx, _sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
    Entity(parent=hm, model="quad", x=_sx * .022, y=_sy * .022, scale=(.022, .0045),
           rotation_z=(-45 if _sx * _sy > 0 else 45), color=Color(1, .25, .25, 1))

# ---- faixa de mensagem (centro, no alto)
msg_grp = Entity(parent=hud_root, enabled=False)
para(-.26, .255, .52, .058, PANEL_DK, slant=.014, z=.01, parent=msg_grp)
para(-.26, .255, .52, .004, OW_ORANGE, slant=.014, parent=msg_grp)
msg_text = txt("", 0, .285, scale=1.7, origin=(0, 0), parent=msg_grp)


def show_msg(text, col=OW_ORANGE, dur=1.4):
    global msg_t
    msg_text.text, msg_text.color, msg_t = text, col, dur
    msg_grp.enabled = True


# ---- placar (alto, centro): seu time a esquerda, o outro a direita
para(-.225, .43, .20, .052, PANEL_DK, slant=.012, z=.01)
para(-.225, .43, .20, .006, MY_UI, slant=.012)
para(.025, .43, .20, .052, PANEL_DK, slant=-.012, z=.01)
para(.025, .43, .20, .006, OTHER_UI, slant=-.012)
txt(MY_TEAM[2], -.205, .46, scale=.85, col=MY_UI)
txt(OTHER_TEAM[2], .205, .46, scale=.85, col=OTHER_UI, origin=(.5, 0))
sc_me = txt("0", -.045, .456, scale=2.4, origin=(.5, 0))
sc_ot = txt("0", .045, .456, scale=2.4, origin=(-.5, 0))
_d = q(0, .456, .02, .02, OW_ORANGE, origin=(0, 0))
_d.rotation_z = 45
txt("ELIMINACOES", 0, .41, scale=.7, col=DIM, origin=(0, 0))

# ---- cartao do jogador (canto inferior esquerdo): velocidade + placar pessoal
card = Entity(parent=hud_root, x=-RX + .03, y=-.475)
para(0, 0, .36, .13, PANEL_DK, slant=.012, z=.01, parent=card)
para(0, 0, .007, .13, MY_UI, slant=.012, parent=card)
txt("VOCE", .03, .108, scale=1.2, parent=card)
txt(MY_TEAM[2], .345, .108, scale=.95, col=MY_UI, origin=(.5, 0), parent=card)
card_speed = txt("0", .115, .062, scale=2.0, origin=(.5, 0), parent=card)
txt("M/S", .122, .056, scale=.75, col=DIM, parent=card)
N_SEG = 14
segs = [q(.19 + i * .0115, .050, .0085, .024, DIM, parent=card) for i in range(N_SEG)]
card_kd = txt("", .03, .02, scale=.85, col=DIM, parent=card)


# ---- habilidades (canto inferior direito)
def make_box(x, y, w, h, name, key, big=False):
    d = {"h": h}
    d["border"] = q(x - .003, y - .003, w + .006, h + .006, OW_ORANGE, z=.02)
    q(x, y, w, h, PANEL_DK, z=.015)
    d["fill"] = q(x, y, w, .001, DIM, z=.01)
    if big:
        txt(name, x + .012, y + h - .014, scale=.65, col=DIM)
        d["ammo"] = txt("1", x + w - .02, y + h / 2 - .008, scale=2.8, origin=(.5, 0))
    else:
        txt(name, x + w / 2, y + h / 2, scale=.7, origin=(0, 0))
    q(x + w / 2 - .028, y - .026, .056, .02, PANEL_DK, z=.015)
    txt(key, x + w / 2, y - .016, scale=.75, origin=(0, 0))
    return d


def set_box(d, prog, state):  # state: 0 pronto, 1 carregando, 2 ativo
    d["fill"].scale_y = max(.001, d["h"] * prog)
    if state == 2:
        d["border"].color, d["fill"].color = WHITE, Color(1, 1, 1, .40)
    elif state == 0:
        d["border"].color, d["fill"].color = OW_ORANGE, Color(.98, .62, .10, .10)
    else:
        d["border"].color, d["fill"].color = Color(1, 1, 1, .25), Color(.98, .62, .10, .40)


AX, BOX_Y, BOX_H = RX - .035, -.44, .075
b_gun = make_box(AX - .16, BOX_Y, .16, BOX_H, "SHOTGUN", "CLICK", big=True)
_x = AX - .16 - .012 - .075
b_dash = make_box(_x, BOX_Y, .075, BOX_H, "DASH", "E")
_x -= .087
b_slide = make_box(_x, BOX_Y, .075, BOX_H, "SLIDE", "SHIFT")
_x -= .087
b_wall = make_box(_x, BOX_Y, .075, BOX_H, "PAREDE", "W")

# ---- kill feed (canto superior direito)
feed = []


def add_feed(killer_is_me):
    kc, vc = (MY_UI, OTHER_UI) if killer_is_me else (OTHER_UI, MY_UI)
    kn, vn = (MY_TEAM[2], OTHER_TEAM[2]) if killer_is_me else (OTHER_TEAM[2], MY_TEAM[2])
    e = Entity(parent=hud_root)
    para(0, 0, .43, .036, PANEL_DK, slant=.008, z=.01, parent=e)
    para(0, 0, .43, .003, OW_ORANGE, slant=.008, parent=e)
    para(0, 0, .007, .036, kc, slant=.008, parent=e)
    txt(kn, .03, .019, scale=.85, col=kc, parent=e)
    txt("ELIMINOU", .215, .019, scale=.7, col=DIM, origin=(0, 0), parent=e)
    txt(vn, .41, .019, scale=.85, col=vc, origin=(.5, 0), parent=e)
    feed.insert(0, [e, 5.0])
    while len(feed) > 4:
        destroy(feed.pop()[0])


hint = txt("WASD  |  ESPACO pula (segure = bunny hop)  |  SHIFT desliza  |  E dash  |  CLICK atira  |  M opcoes",
           0, -.492, scale=.8, col=DIM, origin=(0, 0))


def update_hud(dt, hs):
    global xh_kick, hm_t, msg_t, hint_t
    # mira
    xh_kick = max(0.0, xh_kick - dt * .12)
    set_crosshair(.010 + min(hs, MAX_HSPEED) * .0006 + xh_kick)
    prog = 1 - P.shoot_cd / SHOT_CD
    # hitmarker
    if hm_t > 0:
        hm_t -= dt
        hm.enabled = hm_t > 0
        hm.scale = 1 + (.35 - hm_t) * .6
    # mensagem central
    if msg_t > 0:
        msg_t -= dt
        if msg_t <= 0:
            msg_grp.enabled = False
    # placar e cartao
    set_txt(sc_me, str(P.kills))
    set_txt(sc_ot, str(P.deaths))
    set_txt(card_speed, f"{hs:.0f}")
    set_txt(card_kd, f"ELIM {P.kills}     MORTES {P.deaths}")
    n = round(min(hs / MAX_HSPEED, 1) * N_SEG)
    for i, sg in enumerate(segs):
        if i >= n:
            sg.color = Color(1, 1, 1, .12)
        else:
            sg.color = WHITE if i < N_SEG * .5 else OW_ORANGE if i < N_SEG * .8 else Color(1, .35, .1, 1)
    # habilidades
    set_box(b_gun, prog, 0 if prog >= 1 else 1)
    set_txt(b_gun["ammo"], "1" if prog >= 1 else "0")
    sl = 1 - P.slide_cd / .8
    set_box(b_slide, sl, 2 if P.sliding else 0 if sl >= 1 else 1)
    set_box(b_dash, 1 if P.dash_ready else 0, 2 if P.dash_t > 0 else 0 if P.dash_ready else 1)
    wl = max(0.0, 1 - P.wall_t / 2.5)
    set_box(b_wall, wl, 2 if P.wallrun else 0 if wl > 0 else 1)
    # kill feed
    for i, f in enumerate(list(feed)):
        f[1] -= dt
        if f[1] <= 0:
            destroy(f[0])
            feed.remove(f)
    for i, f in enumerate(feed):
        f[0].x, f[0].y = RX - .46, .41 - i * .046
    # dica de controles some depois de um tempo
    if hint_t > 0:
        hint_t -= dt
        hint.color = Color(1, 1, 1, .6 * min(1, hint_t / 3))
        if hint_t <= 0:
            hint.enabled = False


SENS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"sens_{role}.json")
SENS_X, SENS_Y = 40.0, 40.0
try:
    with open(SENS_FILE) as fh:
        _s = json.load(fh)
        SENS_X, SENS_Y = float(_s["x"]), float(_s["y"])
except Exception:
    pass

# ----------------------------------------------------------------- MENU (tecla M)
menu_open = False
menu_items = [Entity(parent=camera.ui, model="quad", scale=(.9, .5), color=Color(.03, .04, .07, .94), z=.1),
              Entity(parent=camera.ui, model="quad", scale=(.9, .006), position=(0, .247), color=OW_ORANGE, z=.09),
              Text("OPCOES", parent=camera.ui, origin=(0, 0), position=(0, .19), scale=1.8, color=OW_ORANGE),
              Text("Vale so para voce   |   M ou ESC para fechar", parent=camera.ui, origin=(0, 0),
                   position=(0, .14), scale=.9, color=DIM)]


def make_slider(label, y, value):
    menu_items.append(Text(label, parent=camera.ui, origin=(-.5, 0), position=(-.35, y + .045), scale=1.1))
    sl = Slider(5, 100, default=int(value), step=1, dynamic=True)
    sl.x, sl.y = -.25, y
    try:
        sl.knob.color = OW_ORANGE
        sl.bg.color = Color(1, 1, 1, .15)
        sl.knob.text_entity.color = Color(1, 1, 1, 0)   # esconde o numero que o Slider desenha na bolinha
    except Exception:
        pass
    vt = Text("", parent=camera.ui, origin=(-.5, 0), position=(.3, y + .012), scale=1.1)
    menu_items.extend([sl, vt])
    return sl, vt


sens_x, sx_text = make_slider("Sensibilidade X (horizontal)", .04, SENS_X)
sens_y, sy_text = make_slider("Sensibilidade Y (vertical)", -.1, SENS_Y)
for _e in menu_items:
    _e.enabled = False


def toggle_menu():
    global menu_open
    menu_open = not menu_open
    for e in menu_items:
        e.enabled = menu_open
    hud_root.enabled = not menu_open
    mouse.locked = not menu_open
    mouse.visible = menu_open
    if not menu_open:
        try:
            with open(SENS_FILE, "w") as fh:
                json.dump({"x": SENS_X, "y": SENS_Y}, fh)
        except OSError:
            pass

def look_dir():
    y, pt = math.radians(P.yaw), math.radians(P.pitch)
    return (math.sin(y) * math.cos(pt), -math.sin(pt), math.cos(y) * math.cos(pt))


def tracer(a, b, col=WHITE):
    a, b = Vec3(*a), Vec3(*b)
    c = Color(col[0] * .6 + .4, col[1] * .6 + .4, col[2] * .6 + .4, 1)  # tom do time, bem claro
    e = Entity(model="cube", color=c, position=(a + b) / 2, scale=(.045, .045, max(.1, (b - a).length())))
    e.look_at(b)
    try:
        e.animate_color(Color(c[0], c[1], c[2], 0), duration=.16)
    except Exception:
        pass
    destroy(e, delay=.18)


def flash_red():
    f = Entity(parent=camera.ui, model="quad", scale=2, color=Color(1, 0, 0, .3))
    destroy(f, delay=.1)


def respawn():
    far = max(SPAWNS, key=lambda s: (s[0] - R.p[0]) ** 2 + (s[2] - R.p[2]) ** 2)
    P.p = list(far)
    P.v = [0, 0, 0]
    P.hp, P.h, P.sliding, P.dash_t = 100, 1.8, False, 0
    P.yaw = 90.0 if far[0] < 0 else -90.0


def shoot():
    P.shoot_cd = SHOT_CD
    o = [rig.x, rig.y, rig.z]
    y, pt = math.radians(P.yaw), math.radians(P.pitch)
    fwd = look_dir()
    right = (math.cos(y), 0, -math.sin(y))
    up = (math.sin(y) * math.sin(pt), math.cos(pt), math.cos(y) * math.sin(pt))
    start = [o[i] + right[i] * .25 - up[i] * .2 + fwd[i] * .5 for i in range(3)]
    spread = math.tan(math.radians(SPREAD))
    lines, killed = [], False
    for i in range(PELLETS):
        ax = ay = 0.0
        if i > 0:  # o 1o chumbinho vai exatamente na mira
            ang, rad = random.random() * math.tau, spread * math.sqrt(random.random())
            ax, ay = rad * math.cos(ang), rad * math.sin(ang)
        d = [fwd[k] + right[k] * ax + up[k] * ay for k in range(3)]
        dl = math.sqrt(sum(x * x for x in d))
        d = [x / dl for x in d]
        tw = min([t for bx in BOXES if (t := ray_box(o, d, bx[:3], bx[3:])) is not None] or [100])
        tp = (ray_box(o, d, (R.p[0] - .35, R.p[1], R.p[2] - .35), (R.p[0] + .35, R.p[1] + R.h, R.p[2] + .35))
              if R.online else None)
        hit = tp is not None and tp < tw
        t = tp if hit else tw
        killed = killed or hit
        lines.append([[round(c, 2) for c in start], [round(o[k] + d[k] * t, 2) for k in range(3)]])
    for a_, b_ in lines:
        tracer(a_, b_, MY_UI)
    net.send({"t": "shot", "l": lines})
    if killed:
        net.send({"t": "hit", "d": 100})  # one shot
    gun.z = GUN_POS[2] - .12
    gun.rotation_x = -7
    muzzle.enabled = True
    invoke(setattr, muzzle, "enabled", False, delay=.05)
    global xh_kick, hm_t
    xh_kick = .025
    if killed:
        hm_t = .35


def air_strafe(wx, wz, dt):
    """Strafe no ar (estilo Quake): permite ganhar velocidade no bunny hop."""
    add = AIR_STRAFE_CAP - (P.v[0] * wx + P.v[2] * wz)
    if add <= 0:
        return
    a = min(AIR_STRAFE_ACCEL * dt, add)
    P.v[0] += wx * a
    P.v[2] += wz * a


def accelerate(wx, wz, maxspeed, accel, dt):
    cur = P.v[0] * wx + P.v[2] * wz
    add = maxspeed - cur
    if add <= 0:
        return
    a = min(accel * maxspeed * dt, add)
    P.v[0] += wx * a
    P.v[2] += wz * a


# ----------------------------------------------------------------- INPUT
def input(key):
    if key == "m":
        toggle_menu()
        return
    if key == "escape":
        if menu_open:
            toggle_menu()
        else:
            application.quit()
        return
    if menu_open:
        return
    if key == "space":
        P.jump_buf = .15  # o pulo no chao acontece no update (permite bunny hop)
        if P.wallrun:
            n = P.wall_n
            P.v[0] += n[0] * 9
            P.v[2] += n[1] * 9
            P.v[1] = 9
            P.wall_cd, P.wallrun, P.jump_buf = .3, False, 0
    elif key in ("left shift", "c"):
        hs = math.hypot(P.v[0], P.v[2])
        if P.ground and not P.sliding and hs > 3 and P.slide_cd <= 0:
            sp = min(max(hs * 1.2, 14), 20)
            P.v[0], P.v[2] = P.v[0] / hs * sp, P.v[2] / hs * sp
            P.sliding, P.slide_cd, P.h = True, .8, 1.0
    elif key in ("e", "right mouse down"):
        if not P.ground and P.dash_ready and P.dash_t <= 0:
            P.dash_ready, P.dash_t, P.dash_dir, P.wallrun = False, .2, look_dir(), False
            P.sliding = False


# ----------------------------------------------------------------- UPDATE
def handle_net(dt):
    for m in net.poll():
        t = m["t"]
        if t == "s":
            R.p, R.yaw, R.h = m["p"], m["y"], m["h"]
            R.st, R.ws, R.spd = m.get("st", 0), m.get("ws", 0), m.get("sp", 0)
        elif t == "shot":
            for a_, b_ in m["l"]:
                tracer(a_, b_, OTHER_UI)
        elif t == "hit":
            P.hp -= m["d"]
            flash_red()
            if P.hp <= 0:
                P.deaths += 1
                add_feed(False)
                show_msg("VOCE FOI ELIMINADO", Color(1, .35, .35, 1))
                net.send({"t": "dead"})
                respawn()
        elif t == "dead":
            P.kills += 1
            add_feed(True)
            show_msg("ELIMINOU " + OTHER_TEAM[2], OW_ORANGE)
        elif t == "bye":
            R.online = False
            show_msg("AMIGO DESCONECTOU", OW_ORANGE, 999)
    P.net_t += dt
    if P.net_t >= 1 / 30:
        P.net_t = 0
        st = 3 if P.dash_t > 0 else 2 if P.wallrun else 1 if P.sliding else 0 if P.ground else 4
        net.send({"t": "s", "p": [round(c, 3) for c in P.p], "y": round(P.yaw, 1), "h": P.h,
                  "st": st, "ws": P.wall_side, "sp": round(math.hypot(P.v[0], P.v[2]), 1)})


def update():
    global SENS_X, SENS_Y
    dt = min(time.dt, .05)
    handle_net(dt)
    p, v = P.p, P.v

    # olhar
    if menu_open:
        SENS_X, SENS_Y = float(sens_x.value), float(sens_y.value)
        sx_text.text = str(int(SENS_X))
        sy_text.text = str(int(SENS_Y))
    else:
        P.yaw += mouse.velocity[0] * SENS_X
        P.pitch = max(-89, min(89, P.pitch - mouse.velocity[1] * SENS_Y))
    y = math.radians(P.yaw)
    fwd, right = (math.sin(y), math.cos(y)), (math.cos(y), -math.sin(y))
    k = 0 if menu_open else 1
    f = (held_keys["w"] - held_keys["s"]) * k
    r = (held_keys["d"] - held_keys["a"]) * k
    wx, wz = fwd[0] * f + right[0] * r, fwd[1] * f + right[1] * r
    l = math.hypot(wx, wz)
    if l > 0:
        wx, wz = wx / l, wz / l

    P.slide_cd = max(0, P.slide_cd - dt)
    P.wall_cd = max(0, P.wall_cd - dt)
    P.shoot_cd = max(0, P.shoot_cd - dt)
    P.jump_buf = max(0, P.jump_buf - dt)
    hs = math.hypot(v[0], v[2])

    # fim do slide / levantar
    if P.sliding and (not (held_keys["left shift"] or held_keys["c"]) or hs < 4.5 or not P.ground):
        P.sliding = False
    if P.sliding:
        P.h = 1.0
    elif P.h < 1.8 and not box_hit(p, 1.8):
        P.h = 1.8

    if P.dash_t > 0:  # ---- DASH
        P.dash_t -= dt
        v[0], v[1], v[2] = (c * 24 for c in P.dash_dir)
        if P.dash_t <= 0:
            v[0] *= .55
            v[1] *= .4
            v[2] *= .55
        P.wallrun = False
    else:
        if P.ground and not menu_open and (held_keys["space"] or P.jump_buf > 0):  # pulo / bunny hop
            v[1] = 8.5                      # pula ANTES do atrito: a velocidade e mantida
            if P.sliding:                   # slide hop: sai do slide ganhando um impulso
                v[0] *= 1.12
                v[2] *= 1.12
                P.sliding = False
            P.ground, P.jump_buf = False, 0
        wall = None if P.ground else probe_wall(p, P.h)
        if P.ground:
            P.dash_ready, P.wall_t = True, 0
        if wall:
            P.dash_ready = True
        P.wallrun = bool(wall and f > 0 and P.wall_cd <= 0 and P.wall_t < 2.5 and hs > 3.5 and not P.sliding)
        if P.wallrun:  # ---- WALLRUN
            P.wall_n = wall
            tx, tz = -wall[1], wall[0]
            if tx * fwd[0] + tz * fwd[1] < 0:
                tx, tz = -tx, -tz
            sp = min(max(hs, 10), 16)
            v[0], v[2] = tx * sp, tz * sp
            v[1] = max(v[1] - 4 * dt, -2)
            P.wall_t += dt
        elif P.ground:  # ---- CHAO / SLIDE
            if hs > 0:
                drop = (hs * .6 + 1.5) * dt if P.sliding else max(hs, 3) * 8 * dt
                ns = max(hs - drop, 0) / hs
                v[0] *= ns
                v[2] *= ns
            accelerate(wx, wz, 9, 1 if P.sliding else 10, dt)
            v[1] -= 25 * dt
        else:  # ---- AR
            accelerate(wx, wz, 9, 3, dt)
            air_strafe(wx, wz, dt)
            v[1] -= 25 * dt
            hs2 = math.hypot(v[0], v[2])
            if hs2 > MAX_HSPEED:
                v[0] *= MAX_HSPEED / hs2
                v[2] *= MAX_HSPEED / hs2

    # ---- movimento + colisao por eixo
    ground = False
    for ax in (0, 2, 1):
        p[ax] += v[ax] * dt
        b = box_hit(p, P.h)
        if b:
            if ax == 1:
                if v[1] < 0:
                    p[1] = b[4]
                    ground = True
                else:
                    p[1] = b[1] - P.h - .001
                v[1] = 0
            else:
                p[ax] = b[ax] - .3 - .001 if v[ax] > 0 else b[ax + 3] + .3 + .001
                v[ax] = 0
    P.ground = ground
    if p[1] < -20:
        respawn()

    # ---- tiro
    if not menu_open and held_keys["left mouse"] and P.shoot_cd <= 0:
        shoot()
    kr = min(1, dt * 14)
    gun.z += (GUN_POS[2] - gun.z) * kr
    gun.rotation_x += (0 - gun.rotation_x) * kr

    # ---- camera
    P.eye += ((.8 if P.h < 1.5 else 1.6) - P.eye) * min(1, dt * 12)
    rig.position = (p[0], p[1] + P.eye, p[2])
    rig.rotation_y = P.yaw
    head.rotation_x = P.pitch
    roll_t = 0
    P.wall_side = 0
    if P.wallrun:
        on_right = P.wall_n[0] * right[0] + P.wall_n[1] * right[1] < 0
        P.wall_side = 1 if on_right else -1     # +1 = parede na direita
        roll_t = -13 * P.wall_side              # parede na esquerda -> camera vira para a direita
    P.roll += (roll_t - P.roll) * min(1, dt * 8)
    head.rotation_z = P.roll
    hs = math.hypot(v[0], v[2])
    camera.fov += (90 + min(hs, 25) * .6 + (15 if P.dash_t > 0 else 0) - camera.fov) * min(1, dt * 8)

    # ---- jogador remoto (suavizado + pose por estado)
    for i in range(3):
        R.sp[i] += (R.p[i] - R.sp[i]) * min(1, dt * 20)
    R.root.enabled = R.online
    R.t += dt * (6 + R.spd * .7)
    tx_t = tz_t = bob = 0.0
    if R.st == 1:        # slide: deitado para tras
        tx_t = -70
    elif R.st == 3:      # dash: inclinado para frente
        tx_t = 70
    elif R.st == 2:      # parede: inclina para longe da parede
        tz_t, tx_t = -18 * R.ws, 8
    elif R.st == 4:
        tx_t = 12
    elif R.spd > 1:      # correndo: inclina, balanca e quica
        tx_t, tz_t = min(R.spd, 12) * 1.3, math.sin(R.t) * 3
        bob = abs(math.sin(R.t)) * .05
    kk = min(1, dt * 12)
    R.tx += (tx_t - R.tx) * kk
    R.tz += (tz_t - R.tz) * kk
    hip = .9 * math.cos(math.radians(R.tx)) * math.cos(math.radians(R.tz))
    R.root.position = (R.sp[0], R.sp[1] + hip + bob, R.sp[2])
    R.root.rotation = (R.tx, R.yaw, R.tz)

    update_hud(dt, hs)


app.run()