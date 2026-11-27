"""
FPS MOVIMENTO - 1v1 multiplayer (Python + Ursina)

Creditos: personagem "Animated Base Character" by Quaternius (https://poly.pizza/m/cwYvO5UauX), CC-BY 3.0, via Poly Pizza.
          Fonte Jaro (Google Fonts, OFL). Detalhes no README.md e em assets/models/CREDITS.txt.

Instalar:   pip install ursina
Host:       python fps_multiplayer.py host
Amigo:      python fps_multiplayer.py join IP_DO_HOST
(sem argumentos, o jogo pergunta)

CONTROLES
  WASD ........ andar          Mouse ....... olhar
  ESPACO ...... pular / pular da parede
  ESPACO no ar . pulo duplo (1 por salto; volta ao tocar o chao ou a parede)
  BUNNY HOP ... segure ESPACO ao cair (pula sozinho, sem perder velocidade);
                no ar, mova o mouse para o lado e segure A ou D (strafe) para ganhar velocidade
  Parede + W .. andar na parede (wallrun) quando esta no ar encostado
  E / botao direito .. dash no ar: sozinho = para onde voce olha; + WASD = lados/tras/diagonal
                       (ate 3 cargas, 3 s por carga; so recarrega com o tempo)
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

import bisect, glob, json, math, os, random, socket, struct, threading
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


MAP_DATA = []  # (caixa, cor) - usado para montar a malha do mapa


def add_box(cx, cy, cz, sx, sy, sz, col):
    b = (cx - sx / 2, cy - sy / 2, cz - sz / 2, cx + sx / 2, cy + sy / 2, cz + sz / 2)
    BOXES.append(b)
    MAP_DATA.append((b, col))


def build_map():
    """Junta o mapa inteiro em UMA malha (1 entidade e 1 chamada de desenho, em vez de uma por caixa)."""
    verts, uvs, cols, tris = [], [], [], []
    for (x0, y0, z0, x1, y1, z1), col in MAP_DATA:
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        faces = (((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1), dx, dz),   # topo
                 ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), dx, dz),   # base
                 ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), dx, dy),   # lado -z
                 ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), dx, dy),   # lado +z
                 ((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0), dz, dy),   # lado -x
                 ((x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0), dz, dy))   # lado +x
        for *corners, w, h in faces:
            i = len(verts)
            verts.extend(corners)
            uvs.extend(((0, 0), (w / 2, 0), (w / 2, h / 2), (0, h / 2)))  # grade de 2 em 2 metros
            cols.extend([col] * 4)
            tris.extend(((i, i + 1, i + 2), (i, i + 2, i + 3)))
    Entity(model=Mesh(vertices=verts, triangles=tris, uvs=uvs, colors=cols), texture="white_cube", double_sided=True)


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
build_map()

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


def load_glb_np(path, yaw=0, mode="center", size=1.0):
    """Le um .glb estatico e devolve um NodePath do Panda com posicao, normal e cor base de cada vertice,
    pronto para o shader de cel shading. mode='center': maior dimensao = size, centrado na origem.
    yaw gira o modelo no eixo Y."""
    from array import array
    from panda3d.core import Geom, GeomNode, GeomTriangles, GeomVertexArrayFormat, GeomVertexData, GeomVertexFormat
    prims = _read_glb(path)
    c, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def conv(v):  # glTF (destro) -> Ursina (esquerdo): espelha X; depois gira em Y
        x, y, z = -v[0], v[1], v[2]
        return (x * c + z * sn, y, -x * sn + z * c)

    pts = [conv(v) for pr in prims for v in pr[0]]
    mn = [min(v[i] for v in pts) for i in range(3)]
    mx = [max(v[i] for v in pts) for i in range(3)]
    k = size / max(mx[i] - mn[i] for i in range(3))
    off = [(mn[i] + mx[i]) / 2 for i in range(3)]
    verts, tris, base = array("f"), [], 0
    for pr in prims:
        col = tuple(max(0, ch) ** (1 / 2.2) for ch in pr[2])              # cor base do material (linear -> sRGB)
        for v, n in zip(pr[0], pr[1]):
            pp, nn = conv(v), conv(n)
            verts.extend(((pp[0] - off[0]) * k, (pp[1] - off[1]) * k, (pp[2] - off[2]) * k,
                          nn[0], nn[1], nn[2], col[0], col[1], col[2], 1.0))
        idx = pr[3]
        for i in range(0, len(idx) - 2, 3):
            tris.append((base + idx[i], base + idx[i + 2], base + idx[i + 1]))  # espelhar inverte o sentido
        base += len(pr[0])
    af = GeomVertexArrayFormat()
    af.addColumn("vertex", 3, Geom.NT_float32, Geom.C_point)
    af.addColumn("normal", 3, Geom.NT_float32, Geom.C_normal)
    af.addColumn("color", 4, Geom.NT_float32, Geom.C_color)
    fmt = GeomVertexFormat()
    fmt.addArray(af)
    vd = GeomVertexData("static", GeomVertexFormat.registerFormat(fmt), Geom.UH_static)
    vd.uncleanSetNumRows(base)
    vd.modifyArray(0).modifyHandle().copyDataFrom(verts.tobytes())
    prim = GeomTriangles(Geom.UH_static)
    for a_, b_, c_ in tris:
        prim.addVertices(a_, b_, c_)
    prim.closePrimitive()
    g = Geom(vd)
    g.addPrimitive(prim)
    gn = GeomNode("static")
    gn.addGeom(g)
    return NodePath(gn)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def find_asset(pattern):
    """Procura um arquivo ao lado do script ou em qualquer subpasta de assets/."""
    for d in (BASE_DIR, os.path.join(BASE_DIR, "assets", "**")):
        hits = sorted(glob.glob(os.path.join(d, pattern), recursive=True))
        if hits:
            return hits[0]
    return None



# ----------------------------------------------------------------- PERSONAGEM ANIMADO (esqueleto + animacoes)
# O .glb do personagem tem esqueleto e animacoes. O jogo le o arquivo, calcula as poses de algumas animacoes
# e as guarda numa textura; um shader (na placa de video) deforma a malha. Nao precisa de nenhuma biblioteca extra.
def _m4mul(a, b):
    return [a[r * 4] * b[c] + a[r * 4 + 1] * b[4 + c] + a[r * 4 + 2] * b[8 + c] + a[r * 4 + 3] * b[12 + c]
            for r in range(4) for c in range(4)]


def _trs(t, q, s):
    x, y, z, w = q
    r00, r01, r02 = 1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)
    r10, r11, r12 = 2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)
    r20, r21, r22 = 2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)
    return [r00 * s[0], r01 * s[1], r02 * s[2], t[0],
            r10 * s[0], r11 * s[1], r12 * s[2], t[1],
            r20 * s[0], r21 * s[1], r22 * s[2], t[2],
            0.0, 0.0, 0.0, 1.0]


def _sample(times, vals, t, is_quat):
    if t <= times[0]:
        return vals[0]
    if t >= times[-1]:
        return vals[-1]
    i = bisect.bisect_right(times, t) - 1
    f = (t - times[i]) / (times[i + 1] - times[i])
    a, b = vals[i], vals[i + 1]
    if is_quat:
        if a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3] < 0:
            b = (-b[0], -b[1], -b[2], -b[3])
        q = [a[k] + (b[k] - a[k]) * f for k in range(4)]
        l = math.sqrt(sum(c * c for c in q)) or 1.0
        return (q[0] / l, q[1] / l, q[2] / l, q[3] / l)
    return tuple(a[k] + (b[k] - a[k]) * f for k in range(len(a)))


ANIM_FPS = 20     # amostras por segundo guardadas na textura de poses


def build_char(path, anim_names, top, bot):
    """Le o .glb (malha + esqueleto + animacoes) e devolve (NodePath da malha, textura de poses, info das animacoes)."""
    from panda3d.core import (BoundingSphere, Geom, GeomNode, GeomTriangles, GeomVertexArrayFormat, GeomVertexData,
                              GeomVertexFormat, Point3, Texture as PTexture)
    from array import array
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

    def acc(idx):
        a = j["accessors"][idx]
        bv = j["bufferViews"][a["bufferView"]]
        nc = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
        fmt = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}[a["componentType"]]
        stride = bv.get("byteStride") or struct.calcsize(fmt) * nc
        base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        out = [struct.unpack_from("<" + fmt * nc, blob, base + i * stride) for i in range(a["count"])]
        if a.get("normalized") and fmt in "BH":
            mx = 255.0 if fmt == "B" else 65535.0
            out = [tuple(c / mx for c in v) for v in out]
        return out

    nodes = j["nodes"]
    skin = j["skins"][0]
    joints = skin["joints"]
    ibms = [[v[c * 4 + r] for r in range(4) for c in range(4)] for v in acc(skin["inverseBindMatrices"])]  # -> linha
    # --- hierarquia (inclui ancestrais do esqueleto, ex.: o no "Rig" com escala 100)
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    order = []

    def dfs(i):
        order.append(i)
        for c in nodes[i].get("children", []):
            dfs(c)
    for r in j["scenes"][j.get("scene", 0)]["nodes"]:
        dfs(r)
    rest = {}
    for i, n in enumerate(nodes):
        rest[i] = (tuple(n.get("translation", (0, 0, 0))), tuple(n.get("rotation", (0, 0, 0, 1))),
                   tuple(n.get("scale", (1, 1, 1))))

    def globals_at(over):
        G = {}
        for i in order:
            t, q, s = over.get(i, rest[i]) if i in over else rest[i]
            loc = _trs(t, q, s)
            G[i] = _m4mul(G[parent[i]], loc) if i in parent else loc
        return G

    # --- animacoes escolhidas -> textura de poses
    anim_by_name = {a["name"]: a for a in j["animations"]}
    rows, info = [], {}
    for name in anim_names:
        a = anim_by_name[name]
        chans = {}
        dur = 0.0
        for ch in a["channels"]:
            sm = a["samplers"][ch["sampler"]]
            times = [v[0] for v in acc(sm["input"])]
            vals = acc(sm["output"])
            dur = max(dur, times[-1])
            chans.setdefault(ch["target"]["node"], {})[ch["target"]["path"]] = (times, vals)
        n_fr = max(2, int(math.ceil(dur * ANIM_FPS)) + 1)
        info[name] = (len(rows), n_fr, ANIM_FPS, dur)
        for f in range(n_fr):
            t = min(f / ANIM_FPS, dur)
            over = {}
            for node, cc in chans.items():
                tr, ro, sc = rest[node]
                if "translation" in cc:
                    tr = _sample(*cc["translation"], t, False)
                if "rotation" in cc:
                    ro = _sample(*cc["rotation"], t, True)
                if "scale" in cc:
                    sc = _sample(*cc["scale"], t, False)
                over[node] = (tr, ro, sc)
            G = globals_at(over)
            row = array("f")
            for ji, jn in enumerate(joints):
                B = _m4mul(G[jn], ibms[ji])
                B[0], B[1], B[2], B[3] = -B[0], -B[1], -B[2], -B[3]      # espelha X (glTF destro -> Ursina esquerdo)
                for c in range(4):                                        # 4 texels = 4 colunas
                    row.extend((B[c], B[4 + c], B[8 + c], B[12 + c]))
            rows.append(row)
    W, H = len(joints) * 4, len(rows)
    tex = PTexture("char_poses")
    tex.setup2dTexture(W, H, PTexture.T_float, PTexture.F_rgba32)
    flat = array("f")
    for r in rows:
        flat.extend(r)
    tex.setRamImage(flat.tobytes())
    tex.setMagfilter(PTexture.FT_nearest)
    tex.setMinfilter(PTexture.FT_nearest)

    # --- malha (posicoes originais; a GPU aplica as poses)
    G0 = globals_at({})
    rig_m = G0[parent[joints[0]]] if joints[0] in parent else _trs((0, 0, 0), (0, 0, 0, 1), (1, 1, 1))
    verts = array("f")
    tris = []
    ymin, ymax = 1e9, -1e9
    mats = []
    base_i = 0
    prims = []
    for m in j["meshes"]:
        for p in m["primitives"]:
            prims.append(p)
    for p in prims:
        pos, nor = acc(p["attributes"]["POSITION"]), acc(p["attributes"]["NORMAL"])
        jn_, wt_ = acc(p["attributes"]["JOINTS_0"]), acc(p["attributes"]["WEIGHTS_0"])
        for v in pos:
            y = rig_m[4] * v[0] + rig_m[5] * v[1] + rig_m[6] * v[2] + rig_m[7]
            ymin, ymax = min(ymin, y), max(ymax, y)
    for pi, p in enumerate(prims):
        pos, nor = acc(p["attributes"]["POSITION"]), acc(p["attributes"]["NORMAL"])
        jn_, wt_ = acc(p["attributes"]["JOINTS_0"]), acc(p["attributes"]["WEIGHTS_0"])
        dark = 1.0 if pi == 0 else .6                                  # 2o material (juntas) = tom mais escuro
        for v, n, jj, ww in zip(pos, nor, jn_, wt_):
            y = rig_m[4] * v[0] + rig_m[5] * v[1] + rig_m[6] * v[2] + rig_m[7]
            t = (y - ymin) / (ymax - ymin)
            col = [(bot[k] + (top[k] - bot[k]) * t) * dark for k in range(3)]
            verts.extend((v[0], v[1], v[2], n[0], n[1], n[2], col[0], col[1], col[2], 1.0,
                          float(jj[0]), float(jj[1]), float(jj[2]), float(jj[3]), ww[0], ww[1], ww[2], ww[3]))
        idx = [i[0] for i in acc(p["indices"])]
        for k in range(0, len(idx) - 2, 3):
            tris.append((base_i + idx[k], base_i + idx[k + 1], base_i + idx[k + 2]))
        base_i += len(pos)
    af = GeomVertexArrayFormat()
    af.addColumn("vertex", 3, Geom.NT_float32, Geom.C_point)
    af.addColumn("normal", 3, Geom.NT_float32, Geom.C_normal)
    af.addColumn("color", 4, Geom.NT_float32, Geom.C_color)
    af.addColumn("joints", 4, Geom.NT_float32, Geom.C_other)
    af.addColumn("weights", 4, Geom.NT_float32, Geom.C_other)
    fmt = GeomVertexFormat()
    fmt.addArray(af)
    fmt = GeomVertexFormat.registerFormat(fmt)
    vd = GeomVertexData("char", fmt, Geom.UH_static)
    vd.uncleanSetNumRows(base_i)
    vd.modifyArray(0).modifyHandle().copyDataFrom(verts.tobytes())
    prim = GeomTriangles(Geom.UH_static)
    for a_, b_, c_ in tris:
        prim.addVertices(a_, b_, c_)
    prim.closePrimitive()
    g = Geom(vd)
    g.addPrimitive(prim)
    g.setBounds(BoundingSphere(Point3(0, 0, 0), 4.0))   # o Geom tambem precisa do volume (senao o culling o esconde)
    gn = GeomNode("char")
    gn.addGeom(g)
    gn.setBounds(BoundingSphere(Point3(0, 0, 0), 4.0))   # a malha original e minuscula: define o volume a mao
    gn.setFinal(True)
    return NodePath(gn), tex, info, len(joints), ymin, ymax


CHAR_VERT = """#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform sampler2D poses;
uniform vec4 poseA;   // pose anterior: (linha0, linha1, fracao, PESO DA POSE NOVA)
uniform vec4 poseB;   // pose atual:    (linha0, linha1, fracao, -)
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec4 p3d_Color;
in vec4 joints;
in vec4 weights;
out vec4 col;
out vec3 nrm;

mat4 bone(int j, float r0, float r1, float f) {
    int x = j * 4;
    int y0 = int(r0 + 0.5);
    int y1 = int(r1 + 0.5);
    mat4 a = mat4(texelFetch(poses, ivec2(x, y0), 0), texelFetch(poses, ivec2(x + 1, y0), 0),
                  texelFetch(poses, ivec2(x + 2, y0), 0), texelFetch(poses, ivec2(x + 3, y0), 0));
    mat4 b = mat4(texelFetch(poses, ivec2(x, y1), 0), texelFetch(poses, ivec2(x + 1, y1), 0),
                  texelFetch(poses, ivec2(x + 2, y1), 0), texelFetch(poses, ivec2(x + 3, y1), 0));
    return a * (1.0 - f) + b * f;
}

void main() {
    mat4 skin = mat4(0.0);
    for (int k = 0; k < 4; k++) {
        float w = weights[k];
        if (w > 0.0) {
            int j = int(joints[k] + 0.5);
            mat4 ba = bone(j, poseA.x, poseA.y, poseA.z);
            mat4 bb = bone(j, poseB.x, poseB.y, poseB.z);
            skin += w * (ba * (1.0 - poseA.w) + bb * poseA.w);
        }
    }
    gl_Position = p3d_ModelViewProjectionMatrix * (skin * p3d_Vertex);
    nrm = mat3(p3d_ModelMatrix) * (mat3(skin) * p3d_Normal);
    col = p3d_Color;
}
"""

# --- CEL SHADING: a luz vira 3 faixas (sombra / meio / luz) em vez de um degrade suave
TOON_BANDS = """
float toon(float l) {
    return 0.52 + 0.24 * smoothstep(0.02, 0.07, l) + 0.24 * smoothstep(0.50, 0.55, l);
}
"""
CHAR_FRAG = """#version 130
in vec4 col;
in vec3 nrm;
out vec4 fragColor;
""" + TOON_BANDS + """
void main() {
    float l = dot(normalize(nrm), normalize(vec3(0.30, 0.85, 0.35)));
    fragColor = vec4(col.rgb * toon(l), 1.0);
}
"""
# --- CONTORNO: segunda copia da malha, "inflada" ao longo das normais e desenhada so por tras, em cor escura
OUTLINE_CHAR = 0.014    # espessura do contorno do personagem (metros)
OUTLINE_GUN = 0.0045    # espessura do contorno da shotgun
OUTLINE_COLOR = "vec4(0.03, 0.04, 0.07, 1.0)"
CHAR_FRAG_OL = "#version 130\nout vec4 fragColor;\nvoid main() { fragColor = " + OUTLINE_COLOR + "; }\n"
STATIC_VERT = """#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat3 p3d_NormalMatrix;
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec4 p3d_Color;
out vec4 col;
out vec3 nrm;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    nrm = p3d_NormalMatrix * p3d_Normal;
    col = p3d_Color;
}
"""
STATIC_FRAG = """#version 130
in vec4 col;
in vec3 nrm;
out vec4 fragColor;
""" + TOON_BANDS + """
void main() {
    float l = dot(normalize(nrm), normalize(vec3(-0.35, 0.75, 0.55)));   // luz fixa em relacao a camera
    fragColor = vec4(col.rgb * toon(l), 1.0);
}
"""
STATIC_VERT_OL = STATIC_VERT.replace("gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;",
                                     "gl_Position = p3d_ModelViewProjectionMatrix * vec4(p3d_Vertex.xyz + normalize(p3d_Normal) * %s, 1.0);" % OUTLINE_GUN)
from panda3d.core import CullFaceAttrib as _CFA


def make_shader(vert, frag):
    from panda3d.core import Shader as _PS
    sh = _PS.make(_PS.SL_GLSL, vert, frag)
    if sh is None or sh.getErrorFlag():
        raise RuntimeError("shader nao compilou")
    return sh


OUTLINE_CULL = _CFA.MCullClockwise       # qual lado da copia inflada fica escondido (se o contorno cobrir o modelo, troque por MCullCounterClockwise)

CHAR_VERT_OL = CHAR_VERT.replace("gl_Position = p3d_ModelViewProjectionMatrix * (skin * p3d_Vertex);",
    "vec4 sp = skin * p3d_Vertex;\n    vec3 sn = normalize(mat3(skin) * p3d_Normal);\n    gl_Position = p3d_ModelViewProjectionMatrix * vec4(sp.xyz + sn * %s, 1.0);" % OUTLINE_CHAR)
CHAR_YAW = 90   # o modelo original olha para +X; girar 90 graus faz ele olhar para +Z
CHAR_ANIMS = {"idle": "Rig|Idle_Loop", "walk": "Rig|Walk_Loop", "jog": "Rig|Jog_Fwd_Loop", "sprint": "Rig|Sprint_Loop",
              "air": "Rig|Jump_Loop", "jump": "Rig|Jump_Start"}
NON_LOOP = ("jump",)


class AnimChar:
    """Personagem com esqueleto: poses pre-calculadas numa textura e deformacao feita na GPU (shader)."""

    def __init__(self, path, top, bot, parent=None, height=1.8):
        from panda3d.core import Shader as PShader
        np_, self.tex, info, self.nj, ymin, ymax = build_char(path, list(CHAR_ANIMS.values()), top, bot)
        self.info = {k: info[v] for k, v in CHAR_ANIMS.items()}
        k = height / (ymax - ymin)
        self.pivot = Entity(parent=parent, rotation_y=CHAR_YAW)     # gira o modelo para ele olhar para +Z
        self.np = np_
        self.np.reparentTo(self.pivot)
        self.np.setScale(k)
        self.np.setPos(0, -ymin * k, 0)                              # pes em y = 0
        self.np.setTwoSided(True)
        sh = PShader.make(PShader.SL_GLSL, CHAR_VERT, CHAR_FRAG)
        if sh is None or sh.getErrorFlag():
            raise RuntimeError("shader do personagem nao compilou")
        self.np.setShader(sh)
        self.np.setShaderInput("poses", self.tex)
        self.np_ol = self.np.copyTo(self.pivot)                      # copia "inflada" = contorno do cel shading
        self.np_ol.setTwoSided(False)
        self.np_ol.setAttrib(_CFA.make(OUTLINE_CULL))
        self.np_ol.setShader(make_shader(CHAR_VERT_OL, CHAR_FRAG_OL))
        self.np_ol.setShaderInput("poses", self.tex)
        self.cur = self.prev = None
        self.t = self.pt = 0.0
        self.rate = self.prate = 1.0
        self.fade = 1.0

    def play(self, name, rate=1.0):
        if name != self.cur:                       # troca de animacao: faz a transicao suave (fade)
            self.prev, self.pt, self.prate = self.cur, self.t, self.rate
            self.cur, self.t = name, 0.0
            self.fade = 0.0 if self.prev else 1.0
        self.rate = rate

    def _rows(self, name, t):
        start, n, fps, dur = self.info[name]
        f = t * fps
        f = min(f, n - 1.001) if name in NON_LOOP else f % (n - 1)
        i = int(f)
        return start + i, start + min(i + 1, n - 1), f - i

    def update(self, dt):
        if self.cur is None:
            return
        self.t += dt * self.rate
        self.pt += dt * self.prate
        self.fade = min(1.0, self.fade + dt / .18)
        b0, b1, bf = self._rows(self.cur, self.t)
        if self.prev and self.fade < 1.0:
            a0, a1, af = self._rows(self.prev, self.pt)
        else:
            a0, a1, af = b0, b1, bf
        for n_ in (self.np, self.np_ol):
            n_.setShaderInput("poseA", Vec4(a0, a1, af, self.fade))
            n_.setShaderInput("poseB", Vec4(b0, b1, bf, 0))



# ----------------------------------------------------------------- AJUSTES DE JOGO
SHOT_CD = .75        # tempo entre tiros (s)
PELLETS = 7          # "chumbinhos" da shotgun (1 no centro + 6 em volta)
SPREAD = 1.6         # dispersao maxima em GRAUS (menor = mais preciso)
AIR_STRAFE_CAP = 1.6     # quanto o strafe no ar consegue somar por vez (bunny hop)
AIR_STRAFE_ACCEL = 70    # velocidade com que isso e somado
MAX_SPEED = 28           # velocidade MAXIMA permitida (m/s) = 100,8 km/h. E o limite do jogo e o fundo de escala do velocimetro
SPEED_3D = True          # o velocimetro conta tambem a velocidade vertical (queda, pulo). False = so a horizontal
DJUMP_SPEED = 8.5        # impulso do pulo duplo (o pulo normal tambem e 8.5)
DASH_MAX_CHARGES = 3     # cargas de dash guardadas ao mesmo tempo
DASH_RECHARGE = 3.0      # segundos para recuperar CADA carga
DASH_GAP = 0.1           # recuperacao interna (s) depois de cada dash, antes de poder usar a proxima carga
MOSTRAR_DEBUG = True     # contadores de FPS / entidades do Ursina (False = esconde)
if not MOSTRAR_DEBUG:
    for _n in ("fps_counter", "entity_counter", "collider_counter"):
        try:
            getattr(window, _n).enabled = False
        except Exception:
            pass


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
    djump_ready = True   # pulo duplo disponivel (volta ao tocar o chao)
    dj_count = 0         # quantos pulos duplos ja deu (o outro jogador usa para animar)
    wallrun = False
    wall_n = (0, 0)
    wall_t = 0.0
    wall_cd = 0.0
    dash_charges = 3     # cargas de dash disponiveis
    dash_timer = 0.0     # progresso (s) da proxima carga
    dash_gap = 0.0       # recuperacao interna depois de um dash
    dash_key = (1, 0)    # (frente/tras, direita/esquerda) do ultimo dash
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
    st = 0      # 0 chao, 2 parede, 3 dash, 4 ar
    dk = (1, 0)  # direcao do dash do outro jogador: (frente/tras, direita/esquerda)
    dj = 0      # contador de pulos duplos do outro jogador (muda = ele acabou de pular de novo)
    dj_t = 0.0  # tempo restante da animacao de pulo duplo
    char = None  # personagem animado (se o modelo carregar)
    ws = 0      # lado da parede (+1 direita, -1 esquerda)
    spd = 0.0
    tx = tz = t = 0.0


# Host = AZUL, quem entra = VERMELHO
def hexc(h):
    return Color(int(h[1:3], 16) / 255, int(h[3:5], 16) / 255, int(h[5:7], 16) / 255, 1)


# Cada time: (cor de cima, cor de baixo, nome). O degrade vai de cima para baixo.
# Time 1 = quem hospeda (host) | Time 2 = quem entra (join)
TEAM = {"host": (hexc("#17B8F3"), hexc("#162FAD"), "AZUL"),
        "join": (hexc("#F37E17"), hexc("#AD1616"), "LARANJA")}
MY_TEAM = TEAM[role]
OTHER_TEAM = TEAM["join" if role == "host" else "host"]
R.root = Entity()                       # fica na altura do quadril (gira em torno dele)
R.mesh = Entity(parent=R.root, y=-.9)   # pes ficam em y = 0
_cp = find_asset("*Animated*Character*.glb") or find_asset("*Character*.glb")
if _cp:
    try:
        R.char = AnimChar(_cp, tuple(OTHER_TEAM[0][i] for i in range(3)), tuple(OTHER_TEAM[1][i] for i in range(3)),
                          parent=R.mesh)
        R.char.play("idle")
    except Exception as e:
        R.char = None
        print("Personagem animado nao carregou, usando modelo simples:", e)
if R.char is None:
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
        _g = load_glb_np(_gp, yaw=90, mode="center", size=.85)
        _sh_main, _sh_ol = make_shader(STATIC_VERT, STATIC_FRAG), make_shader(STATIC_VERT_OL, CHAR_FRAG_OL)
        _g.reparentTo(gun)
        _g.setTwoSided(True)
        _g.setShader(_sh_main)
        _go = _g.copyTo(gun)                         # contorno
        _go.setTwoSided(False)
        _go.setAttrib(_CFA.make(OUTLINE_CULL))
        _go.setShader(_sh_ol)
        _gun_ok = True
    except Exception as e:
        print("Shotgun .glb nao carregou, usando modelo simples:", e)
if not _gun_ok:
    Entity(parent=gun, model="cube", scale=(.1, .12, .5), color=color.black66)

# ----------------------------------------------------------------- HUD (estilo hero shooter)
# Fonte do HUD: Jaro (Google Fonts). Se nao achar, tenta hud_font.ttf; se nao houver nenhuma, usa a padrao.
FONT_FILE = find_asset("Jaro*.ttf") or find_asset("hud_font.*")
if FONT_FILE and FONT_FILE.lower().endswith((".ttf", ".otf")):
    _old_font = Text.default_font
    try:
        Text.default_font = os.path.basename(FONT_FILE)   # o Ursina procura pelo NOME do arquivo dentro da pasta do jogo
        _probe = Text("A")
        if _probe.font is None:
            raise RuntimeError("arquivo de fonte nao encontrado/legivel")
        destroy(_probe)
    except Exception as e:
        Text.default_font = _old_font
        FONT_FILE = None
        print("Fonte nao carregou, usando a padrao:", e)

RX = window.aspect_ratio / 2          # borda direita da tela (coordenadas de UI)
PANEL_DK = Color(.02, .03, .06, .88)
WHITE = Color(1, 1, 1, 1)
DIM = Color(1, 1, 1, .6)
MY_UI, OTHER_UI = MY_TEAM[0], OTHER_TEAM[0]    # tom claro de cada time (textos, rastros)
ACCENT = MY_UI                                  # cor de destaque do HUD = cor do SEU time


def ca(c, a):
    """Mesma cor com outra transparencia."""
    return Color(c[0], c[1], c[2], a)

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


def para_grad(x, y, w, h, top, bot, slant=.012, z=0, parent=None):
    """Paralelogramo com degrade vertical (cor de cima -> cor de baixo)."""
    m = Mesh(vertices=[(0, 0, 0), (w, 0, 0), (w + slant, h, 0), (slant, h, 0)], triangles=[(0, 1, 2), (0, 2, 3)],
             colors=[bot, bot, top, top])
    e = Entity(parent=parent or hud_root, model=m, double_sided=True)
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
muzzle_t, flash_t = 0.0, 0.0


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
para(-.26, .255, .52, .004, ACCENT, slant=.014, parent=msg_grp)
msg_text = txt("", 0, .285, scale=1.7, origin=(0, 0), parent=msg_grp)


def show_msg(text, col=ACCENT, dur=1.4):
    global msg_t
    msg_text.text, msg_text.color, msg_t = text, col, dur
    msg_grp.enabled = True


# ---- velocimetro (montado com pecas vetoriais): 20 barras + sublinhado + numero em km/h
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

N_BOX, MS_TO_KMH = 20, 3.6
SPEED_MAX_KMH = MAX_SPEED * MS_TO_KMH         # velocidade maxima permitida = todas as barras cheias
BOX_STEP = SPEED_MAX_KMH / N_BOX              # quantos km/h vale cada barra

SPD_W = .50                                   # largura do medidor (muda o tamanho de todo o conjunto: medidor + itens)
SC = SPD_W / 617                              # 1 "pixel" do desenho original, em unidades de tela
SPD_H = 115 * SC
ITEM_W, ITEM_H, ITEM_GAP = 150 * SC, 100 * SC, 17 * SC
ITEM_Y = -.485                                # itens (embaixo do medidor)
SPD_X, SPD_Y = -RX + .03, ITEM_Y + ITEM_H + 18 * SC   # medidor logo acima dos itens


def _load_png(path):
    t = Texture(Image.open(path).convert("RGBA"))
    try:
        t.filtering = "mipmap"
    except Exception:
        pass
    return t


_tm = "time1" if role == "host" else "time2"
_sp_dir = os.path.join(BASE_DIR, "assets", "speedometer")
speed_ok = False
try:
    tex_on = _load_png(os.path.join(_sp_dir, f"barra_ativa_{_tm}.png"))
    tex_off = _load_png(os.path.join(_sp_dir, "barra_inativa.png"))
    tex_line = _load_png(os.path.join(_sp_dir, f"sublinhado_{_tm}.png"))
    speed_ok = True
except Exception as e:
    print("Imagens do velocimetro nao carregaram, usando texto simples:", e)

LBL_W, LBL_H = 560, 170   # (imagem do numero; exibida em tamanho proporcional ao medidor)
_lbl_cache = {}


def _pil_font(size, opsz=None):
    try:
        f = ImageFont.truetype(FONT_FILE, size)
        if opsz:
            try:
                f.set_variation_by_axes([opsz])   # Jaro e variavel: 72 = versao "display" (numeros grandes)
            except Exception:
                pass
        return f
    except Exception:
        return ImageFont.load_default()


def _render_speed_label(kmh):
    """Numero grande + 'Km/h' pequeno, com degrade do time e sombra (igual ao desenho de referencia)."""
    top = tuple(int(MY_TEAM[0][i] * 255) for i in range(3))
    bot = tuple(int(MY_TEAM[1][i] * 255) for i in range(3))
    img = Image.new("RGBA", (LBL_W, LBL_H), (0, 0, 0, 0))
    big, small = _pil_font(170, 72), _pil_font(64, 14)
    num = str(kmh)
    base_y = LBL_H - 22
    parts = [(num, big, 8), ("Km/h", small, 8 + int(ImageDraw.Draw(img).textlength(num, font=big)) + 10)]
    for text, fnt, x0 in parts:
        mask = Image.new("L", (LBL_W, LBL_H), 0)
        ImageDraw.Draw(mask).text((x0, base_y), text, font=fnt, fill=255, anchor="ls")
        shadow = ImageChops.offset(mask, 5, 5)
        img.paste((0, 0, 0, 215), (0, 0), shadow)
        box = mask.getbbox()
        if box:
            grad = ImageOps.colorize(Image.linear_gradient("L").resize((box[2] - box[0], box[3] - box[1])),
                                     black=top, white=bot)
            img.paste(grad, (box[0], box[1]), mask.crop(box))
    return img


def speed_label_tex(kmh):
    t = _lbl_cache.get(kmh)
    if t is None:
        t = _lbl_cache[kmh] = Texture(_render_speed_label(kmh))
    return t


if speed_ok:
    bar_on = [False] * N_BOX
    speed_bars = []
    for i in range(N_BOX):                    # barra desligada: baixa e cinza | ligada: alta, com o degrade do time
        e = Entity(parent=hud_root, model="quad", texture=tex_off, origin=(-.5, -.5), scale=(28 * SC, 78 * SC))
        e.x, e.y = SPD_X + 31 * i * SC, SPD_Y + 12 * SC
        speed_bars.append(e)
    _ul = Entity(parent=hud_root, model="quad", texture=tex_line, origin=(-.5, -.5), scale=(617 * SC, 7 * SC))
    _ul.x, _ul.y = SPD_X, SPD_Y
    LBL_K = .5236 * SC                        # tamanho de 1 pixel da imagem do numero
    speed_lbl = Entity(parent=hud_root, model="quad", texture=speed_label_tex(0), origin=(-.5, -.5),
                       scale=(LBL_W * LBL_K, LBL_H * LBL_K))
    speed_lbl.x, speed_lbl.y = SPD_X + 639 * SC, SPD_Y + 3.4 * SC
else:   # plano B: so o numero em texto
    speed_txt = txt("0 KM/H", SPD_X, SPD_Y + .03, scale=2.2, col=MY_UI)


def set_bars(n):
    """Acende as n primeiras barras (so mexe nas que mudaram)."""
    for i in range(N_BOX):
        on = i < n
        if bar_on[i] != on:
            bar_on[i] = on
            e = speed_bars[i]
            e.texture = tex_on if on else tex_off
            e.scale_y = (103 if on else 78) * SC


# ---- itens (embaixo do medidor): shotgun, dash e pulo duplo
# Ao usar: o item "da uma aumentada" e acende um pouquinho. Enquanto recarrega, uma faixa escura
# vai descendo de cima para baixo e, quando chega no fim, o item esta pronto de novo.
item_pulse = {"gun": 0.0, "dash": 0.0, "dj": 0.0}


def _load_item(name):
    try:
        return _load_png(os.path.join(BASE_DIR, "assets", "items", name + ".png"))
    except Exception as e:
        print("Icone do item nao carregou:", name, e)
        return None


def make_item(key, png, i):
    cx = SPD_X + ITEM_W / 2 + i * (ITEM_W + ITEM_GAP)
    root = Entity(parent=hud_root)
    root.x, root.y = cx, ITEM_Y + ITEM_H / 2
    tex = _load_item(png)
    if tex is not None:
        Entity(parent=root, model="quad", texture=tex, scale=(ITEM_W, ITEM_H))
    else:                                              # plano B: caixa cinza simples
        q(-ITEM_W / 2, -ITEM_H / 2, ITEM_W, ITEM_H, Color(.28, .28, .28, 1), parent=root)
    cover = q(-ITEM_W / 2, -ITEM_H / 2, ITEM_W, .001, Color(0, 0, 0, .68), z=-.01, parent=root)   # faixa escura
    glow = q(-ITEM_W / 2, -ITEM_H / 2, ITEM_W, ITEM_H, Color(1, 1, 1, 0), z=-.02, parent=root)      # brilho do uso
    return {"root": root, "cover": cover, "glow": glow, "key": key}


items = {"gun": make_item("gun", "shotgun", 0), "dash": make_item("dash", "dash", 1),
         "dj": make_item("dj", "double_jump", 2)}


POP_TIME = .30                                    # duracao da animacao de "pop"
pops = {"dash": 0.0, "k": 0.0, "d": 0.0}


def pop_scale(t):
    """t vai de 1 a 0. O numero cresce rapido e volta ao normal, passando um pouquinho do tamanho (efeito "pop")."""
    u = 1.0 - t
    return 1.0 + .60 * math.sin(math.pi * u) * (1.0 - .35 * u)


def set_item(it, cover_frac, dt, alpha=.68):
    """cover_frac: 1 = totalmente escuro ... 0 = livre. O topo da faixa escura desce ate sumir."""
    k = (int(cover_frac * 50), int(alpha * 100))
    if it.get("_k") != k:
        it["_k"] = k
        it["cover"].scale_y = max(.0005, ITEM_H * cover_frac)
        it["cover"].color = Color(0, 0, 0, alpha)
        it["cover"].enabled = cover_frac > 0
    pl = item_pulse[it["key"]]
    if pl > 0:
        pl = max(0.0, pl - dt * 4.5)
        item_pulse[it["key"]] = pl
        it["root"].scale = 1 + .10 * pl                # aumenta bem pouco
        it["glow"].color = Color(1, 1, 1, .45 * pl)    # e acende
        it["_pulsing"] = True
    elif it.get("_pulsing"):
        it["_pulsing"] = False
        it["root"].scale = 1
        it["glow"].color = Color(1, 1, 1, 0)


# ---- selo de cargas do dash (x1 / x2 / x3): fica na quina de cima, a direita, do item do dash
dash_badge_w = {1: 26, 2: 32, 3: 32}               # largura de cada selo no desenho original (a altura e 24)
dash_badge_tex = {}
for _n in (1, 2, 3):
    try:
        dash_badge_tex[_n] = _load_png(os.path.join(BASE_DIR, "assets", "items", f"dash_x{_n}_{_tm}.png"))
    except Exception as e:
        print("Selo do dash nao carregou:", _n, e)
dash_badge_root = Entity(parent=items["dash"]["root"], enabled=False)
dash_badge = Entity(parent=dash_badge_root, model="quad", z=-.03)


def update_dash_item(dt):
    ch = P.dash_charges
    last = _hud.get("dch")
    if ch != last:
        _hud["dch"] = ch
        if last is not None and ch > last:
            pops["dash"] = 1.0                      # ganhou uma carga: "pop"
        if ch > 0 and ch in dash_badge_tex:
            w = dash_badge_w[ch]
            dash_badge.texture = dash_badge_tex[ch]
            dash_badge.scale = (w * SC, 24 * SC)
            dash_badge_root.x = ITEM_W / 2 - 17 * SC + w * SC / 2     # centro do selo
            dash_badge_root.y = ITEM_H / 2                            # na borda de cima do item
        dash_badge_root.enabled = ch > 0 and ch in dash_badge_tex
    if pops["dash"] > 0:
        pops["dash"] = max(0.0, pops["dash"] - dt / POP_TIME)
        dash_badge_root.scale = pop_scale(pops["dash"])
    # faixa escura: enquanto QUALQUER carga esta recarregando ela desce (mais clara se ainda ha carga para usar)
    frac = 0.0 if ch >= DASH_MAX_CHARGES else 1.0 - P.dash_timer / DASH_RECHARGE
    set_item(items["dash"], frac, dt, .68 if ch == 0 else .42)


# ---- KD (canto superior direito, colado na quina): eliminacoes e mortes; o numero da "pop" quando sobe
TS = 1 / 1024                                      # tamanho de 1 pixel do desenho original (canto superior direito)
KD_W, KD_H = 198 * TS, 50 * TS
KD_X, KD_Y = RX - KD_W, .5 - KD_H
q(KD_X, KD_Y, KD_W, KD_H, Color(71 / 255, 71 / 255, 71 / 255, 1), z=.01)
for _png, _px in (("icone_kills", 24), ("icone_mortes", 107)):
    try:
        _ic = Entity(parent=hud_root, model="quad", texture=_load_png(os.path.join(BASE_DIR, "assets", "kd", _png + ".png")),
                     scale=(24 * TS, 24 * TS))
        _ic.x, _ic.y = KD_X + (_px + 12) * TS, KD_Y + KD_H / 2
    except Exception as e:
        print("Icone do KD nao carregou:", _png, e)

_kd_font, _kd_cache = None, {}


def kd_number_tex(text):
    """Imagem do numero em branco, na fonte Jaro (algarismos de 21 px de altura, em 4x). Guardada em cache."""
    global _kd_font
    if text not in _kd_cache:
        if _kd_font is None:
            f0 = _pil_font(100, 72)
            bb = f0.getbbox("0")
            _kd_font = _pil_font(int(100 * 84 / max(1, bb[3] - bb[1])), 72)
        mask = Image.new("L", (500, 200), 0)
        ImageDraw.Draw(mask).text((10, 10), text, font=_kd_font, fill=255)
        mask = mask.crop(mask.getbbox())
        img = Image.new("RGBA", mask.size, (255, 255, 255, 255))
        img.putalpha(mask)
        _kd_cache[text] = (Texture(img), mask.size[0], mask.size[1])
    return _kd_cache[text]


kd_nums = {"k": {"left": 64, "val": None}, "d": {"left": 147, "val": None}}
for _k_, _d_ in kd_nums.items():
    _d_["e"] = Entity(parent=hud_root, model="quad")


def update_kd(dt):
    for key, val in (("k", P.kills), ("d", P.deaths)):
        d_ = kd_nums[key]
        if d_["val"] != val:
            if d_["val"] is not None and val > d_["val"]:
                pops[key] = 1.0                      # o numero subiu: "pop"
            d_["val"] = val
            tex, w, h = kd_number_tex(str(val))
            d_["e"].texture = tex
            d_["w"], d_["h"] = w / 4 * TS, h / 4 * TS
            d_["e"].x = KD_X + d_["left"] * TS + d_["w"] / 2
            d_["e"].y = KD_Y + KD_H / 2
            d_["e"].scale = (d_["w"], d_["h"])
        if pops[key] > 0:
            pops[key] = max(0.0, pops[key] - dt / POP_TIME)
            sc_ = pop_scale(pops[key])
            d_["e"].scale = (d_["w"] * sc_, d_["h"] * sc_)


# ---- kill feed (canto superior direito, abaixo do KD): entra pela direita, de fora da tela, com ease-out
FW, FH = 153 * TS, 47 * TS
FEED_IN, FEED_LIFE, FEED_BG = .25, 5.0, Color(0, 0, 0, .20)   # 250 ms de entrada | 5 s na tela | fundo preto quase transparente
feed_tex = {}
for _key in ("time1", "time2"):
    try:
        feed_tex[_key] = _load_png(os.path.join(BASE_DIR, "assets", "killfeed", f"killfeed_{_key}.png"))
    except Exception as e:
        print("Imagem do kill feed nao carregou:", _key, e)
FEED_N = 3
feed_slots = []
for _i in range(FEED_N):          # vagas criadas uma vez e reaproveitadas
    _e = Entity(parent=hud_root, enabled=False)
    q(0, 0, FW, FH, FEED_BG, z=.01, parent=_e)
    _spr = Entity(parent=_e, model="quad", origin=(-.5, -.5), scale=(FW, FH))
    _fb = None
    if feed_tex:
        _spr.texture = feed_tex["time1"]
    else:
        _fb = txt("", FW / 2, FH / 2, scale=1.0, origin=(0, 0), parent=_e)
    feed_slots.append({"e": _e, "spr": _spr, "fb": _fb})
feed = []   # entradas ativas, da mais nova para a mais antiga: {"slot", "t" (vida restante), "age" (tempo na tela)}


def feed_place(f):
    i = feed.index(f)
    u = min(1.0, f["age"] / FEED_IN)
    ease = 1.0 - (1.0 - u) ** 3                       # ease-out
    f["slot"]["e"].x = (RX - FW) + (1.0 - ease) * (FW + .01)   # comeca fora da tela, a direita
    f["slot"]["e"].y = .5 - (66 + 57 * i + 47) * TS            # posicoes do exemplo de HUD


def add_feed(killer_is_me):
    kteam = role if killer_is_me else ("join" if role == "host" else "host")
    if len(feed) >= FEED_N:                      # cheio: reaproveita a vaga da mais antiga
        slot = feed.pop()["slot"]
    else:
        used = [f["slot"] for f in feed]
        slot = next(sl for sl in feed_slots if all(sl is not u for u in used))
    if feed_tex:
        slot["spr"].texture = feed_tex["time1" if kteam == "host" else "time2"]   # P1 mata P2 / P2 mata P1
    elif slot["fb"] is not None:
        slot["fb"].text = f"{TEAM[kteam][2]} ELIMINOU"
    f = {"slot": slot, "t": FEED_LIFE, "age": 0.0}
    feed.insert(0, f)
    slot["e"].enabled = True
    for ff in feed:
        feed_place(ff)


hint = txt("WASD  |  ESPACO pula (segure = bunny hop; no ar = pulo duplo)  |  E dash (+ WASD = direcao)  |  CLICK atira  |  M opcoes",
           0, .47, scale=.8, col=DIM, origin=(0, 0))
_hud = {}   # ultimos valores aplicados (evita refazer o que nao mudou)


def update_hud(dt, hs):
    global xh_kick, hm_t, msg_t, hint_t, muzzle_t, flash_t
    # mira
    xh_kick = max(0.0, xh_kick - dt * .12)
    gap = round(.010 + min(hs, MAX_SPEED) * .0006 + xh_kick, 3)
    if gap != _hud.get("gap"):
        _hud["gap"] = gap
        set_crosshair(gap)
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
    update_kd(dt)
    spd = math.sqrt(P.v[0] ** 2 + (P.v[1] ** 2 if SPEED_3D else 0.0) + P.v[2] ** 2)   # velocidade real
    kmh = spd * MS_TO_KMH
    shown = int(kmh + .5)
    if speed_ok:
        n = min(N_BOX, int(kmh / BOX_STEP + 1e-6))   # a barra acende ao chegar no valor dela
        if n != _hud.get("n"):
            _hud["n"] = n
            set_bars(n)
        if shown != _hud.get("kmh"):
            _hud["kmh"] = shown
            speed_lbl.texture = speed_label_tex(min(shown, 999))
    else:
        set_txt(speed_txt, f"{shown} KM/H")
    # itens
    set_item(items["gun"], P.shoot_cd / SHOT_CD, dt)
    update_dash_item(dt)
    set_item(items["dj"], 0.0 if P.djump_ready else 1.0, dt)
    # kill feed: anima a entrada (vindo da direita) e tira as entradas antigas
    for f in list(feed):
        f["t"] -= dt
        f["age"] += dt
        if f["t"] <= 0:
            f["slot"]["e"].enabled = False
            feed.remove(f)
        elif f["age"] < FEED_IN + dt:
            feed_place(f)
    for f in feed:
        if f["age"] >= FEED_IN:
            feed_place(f)
    # efeitos curtos: clarao do cano, flash de dano e rastros dos tiros
    if muzzle_t > 0:
        muzzle_t -= dt
        if muzzle_t <= 0:
            muzzle.enabled = False
    if flash_t > 0:
        flash_t -= dt
        if flash_t <= 0:
            dmg_flash.enabled = False
    if tracer_live:
        for t in tracer_live:
            t[1] -= dt
            if t[1] <= 0:
                t[0].enabled = False
            else:
                c = t[2]
                t[0].color = Color(c[0], c[1], c[2], t[1] / .18)
        tracer_live[:] = [t for t in tracer_live if t[1] > 0]
    # dica de controles: some devagar depois de um tempo
    if hint_t > 0:
        hint_t -= dt
        if hint_t < 3:
            a_ = round(.6 * max(hint_t, 0) / 3, 2)
            if a_ != _hud.get("ha"):
                _hud["ha"] = a_
                hint.color = Color(1, 1, 1, a_)
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
              Entity(parent=camera.ui, model="quad", scale=(.9, .006), position=(0, .247), color=ACCENT, z=.09),
              Text("OPCOES", parent=camera.ui, origin=(0, 0), position=(0, .19), scale=1.8, color=ACCENT),
              Text("Vale so para voce   |   M ou ESC para fechar", parent=camera.ui, origin=(0, 0),
                   position=(0, .14), scale=.9, color=DIM),
              Text("Personagem: Animated Base Character, por Quaternius (CC-BY 3.0), via Poly Pizza",
                   parent=camera.ui, origin=(0, 0), position=(0, -.225), scale=.7, color=DIM)]


def make_slider(label, y, value):
    menu_items.append(Text(label, parent=camera.ui, origin=(-.5, 0), position=(-.35, y + .045), scale=1.1))
    sl = Slider(5, 100, default=int(value), step=1, dynamic=True)
    sl.x, sl.y = -.25, y
    try:
        sl.knob.color = ACCENT
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

def dash_direction():
    """Direcao do dash: sem tecla (ou so W) = para onde voce esta olhando (inclusive para cima/baixo).
    Com A/D/S = para o lado / para tras, na horizontal. W + A/D = diagonal para frente."""
    f = int(held_keys["w"] - held_keys["s"])
    r = int(held_keys["d"] - held_keys["a"])
    if f == 0 and r == 0:
        f = 1                                         # padrao: para frente
    y = math.radians(P.yaw)
    right = (math.cos(y), 0.0, -math.sin(y))
    base = look_dir() if f > 0 else (math.sin(y), 0.0, math.cos(y))
    d = [base[k] * f + right[k] * r for k in range(3)]
    l = math.sqrt(sum(c * c for c in d)) or 1.0
    return tuple(c / l for c in d), f, r


def look_dir():
    y, pt = math.radians(P.yaw), math.radians(P.pitch)
    return (math.sin(y) * math.cos(pt), -math.sin(pt), math.cos(y) * math.cos(pt))


# Tiros e flashes reaproveitam objetos ja criados (nada e criado/destruido durante o jogo)
TRACER_N = 16
tracer_pool = [Entity(model="cube", color=WHITE, enabled=False) for _ in range(TRACER_N)]
tracer_live = []   # [entidade, tempo restante, cor]
_tr_i = 0
dmg_flash = Entity(parent=camera.ui, model="quad", scale=2, color=Color(1, 0, 0, .3), z=-.2, enabled=False)


def tracer(a, b, col=WHITE):
    global _tr_i
    a, b = Vec3(*a), Vec3(*b)
    e = tracer_pool[_tr_i]
    _tr_i = (_tr_i + 1) % TRACER_N
    tracer_live[:] = [t for t in tracer_live if t[0] is not e]
    c = Color(col[0] * .6 + .4, col[1] * .6 + .4, col[2] * .6 + .4, 1)  # tom do time, bem claro
    e.enabled = True
    e.position = (a + b) / 2
    e.scale = (.045, .045, max(.1, (b - a).length()))
    e.color = c
    e.look_at(b)
    tracer_live.append([e, .18, c])


def flash_red():
    global flash_t
    dmg_flash.enabled = True
    flash_t = .1


def respawn():
    far = max(SPAWNS, key=lambda s: (s[0] - R.p[0]) ** 2 + (s[2] - R.p[2]) ** 2)
    P.p = list(far)
    P.v = [0, 0, 0]
    P.hp, P.h, P.dash_t, P.djump_ready = 100, 1.8, 0, True
    P.dash_charges, P.dash_timer, P.dash_gap = DASH_MAX_CHARGES, 0.0, 0.0
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
    item_pulse["gun"] = 1.0
    global xh_kick, hm_t, muzzle_t
    muzzle_t = .05
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


def ground_close(dist=.5):
    """True se o chao esta logo abaixo (ai o ESPACO conta como pulo normal adiantado, nao como pulo duplo)."""
    return P.v[1] < 0 and box_hit([P.p[0], P.p[1] - dist, P.p[2]], P.h) is not None


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
        elif (not P.ground) and P.djump_ready and P.dash_t <= 0 and not ground_close():
            P.v[1] = DJUMP_SPEED                 # PULO DUPLO: 1 por salto; volta quando tocar o chao
            P.djump_ready, P.jump_buf = False, 0
            P.dj_count += 1
            item_pulse["dj"] = 1.0
    elif key in ("e", "right mouse down"):
        if not P.ground and P.dash_charges > 0 and P.dash_t <= 0 and P.dash_gap <= 0:
            d_, f_, r_ = dash_direction()
            P.dash_charges -= 1
            P.dash_t, P.dash_dir, P.wallrun = .2, d_, False
            P.dash_key = (f_, r_)
            item_pulse["dash"] = 1.0


# ----------------------------------------------------------------- UPDATE
def handle_net(dt):
    for m in net.poll():
        t = m["t"]
        if t == "s":
            R.p, R.yaw, R.h = m["p"], m["y"], m["h"]
            R.st, R.ws, R.spd = m.get("st", 0), m.get("ws", 0), m.get("sp", 0)
            R.dk = tuple(m.get("dk", (1, 0)))
            if m.get("dj", 0) != R.dj:
                R.dj, R.dj_t = m.get("dj", 0), .45   # o outro jogador deu pulo duplo
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
            show_msg("ELIMINOU " + OTHER_TEAM[2], ACCENT)
        elif t == "bye":
            R.online = False
            show_msg("AMIGO DESCONECTOU", ACCENT, 999)
    P.net_t += dt
    if P.net_t >= 1 / 30:
        P.net_t = 0
        st = 3 if P.dash_t > 0 else 2 if P.wallrun else 0 if P.ground else 4
        net.send({"t": "s", "p": [round(c, 3) for c in P.p], "y": round(P.yaw, 1), "h": P.h,
                  "st": st, "ws": P.wall_side, "sp": round(math.hypot(P.v[0], P.v[2]), 1), "dj": P.dj_count, "dk": list(P.dash_key)})


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

    P.wall_cd = max(0, P.wall_cd - dt)
    P.shoot_cd = max(0, P.shoot_cd - dt)
    P.jump_buf = max(0, P.jump_buf - dt)
    P.dash_gap = max(0.0, P.dash_gap - dt)
    if P.dash_charges < DASH_MAX_CHARGES:        # recarrega uma carga de dash a cada DASH_RECHARGE segundos
        P.dash_timer += dt
        if P.dash_timer >= DASH_RECHARGE:
            P.dash_charges += 1
            P.dash_timer = 0.0
    hs = math.hypot(v[0], v[2])

    if P.dash_t > 0:  # ---- DASH
        P.dash_t -= dt
        v[0], v[1], v[2] = (c * 24 for c in P.dash_dir)
        if P.dash_t <= 0:
            v[0] *= .55
            v[1] *= .4
            v[2] *= .55
            P.dash_gap = DASH_GAP                # pequena recuperacao antes de poder usar outra carga
        P.wallrun = False
    else:
        if P.ground and not menu_open and (held_keys["space"] or P.jump_buf > 0):  # pulo / bunny hop
            v[1] = 8.5                      # pula ANTES do atrito: a velocidade e mantida
            P.ground, P.jump_buf = False, 0
        wall = None if P.ground else probe_wall(p, P.h)
        if P.ground:
            P.wall_t = 0
        if wall:
            P.djump_ready = True   # encostou na parede: o pulo duplo volta
        P.wallrun = bool(wall and f > 0 and P.wall_cd <= 0 and P.wall_t < 2.5 and hs > 3.5)
        if P.wallrun:  # ---- WALLRUN
            P.wall_n = wall
            tx, tz = -wall[1], wall[0]
            if tx * fwd[0] + tz * fwd[1] < 0:
                tx, tz = -tx, -tz
            sp = min(max(hs, 10), 16)
            v[0], v[2] = tx * sp, tz * sp
            v[1] = max(v[1] - 4 * dt, -2)
            P.wall_t += dt
        elif P.ground:  # ---- CHAO
            if hs > 0:
                drop = max(hs, 3) * 8 * dt
                ns = max(hs - drop, 0) / hs
                v[0] *= ns
                v[2] *= ns
            accelerate(wx, wz, 9, 10, dt)
            v[1] -= 25 * dt
        else:  # ---- AR
            accelerate(wx, wz, 9, 3, dt)
            air_strafe(wx, wz, dt)
            v[1] -= 25 * dt

    # ---- limite de velocidade: nada passa da velocidade maxima (a mesma que enche o velocimetro)
    sp_ = math.sqrt(v[0] * v[0] + (v[1] * v[1] if SPEED_3D else 0.0) + v[2] * v[2])
    if sp_ > MAX_SPEED:
        k_ = MAX_SPEED / sp_
        v[0] *= k_
        v[2] *= k_
        if SPEED_3D:
            v[1] *= k_

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
    if ground:
        P.djump_ready = True   # tocou o chao: o pulo duplo volta (o dash recarrega so com o tempo)
    elif probe_wall(p, P.h):
        P.djump_ready = True   # encostou na parede
    if p[1] < -20:
        respawn()

    # ---- tiro
    if not menu_open and held_keys["left mouse"] and P.shoot_cd <= 0:
        shoot()
    kr = min(1, dt * 14)
    gun.z += (GUN_POS[2] - gun.z) * kr
    gun.rotation_x += (0 - gun.rotation_x) * kr

    # ---- camera
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
    R.dj_t = max(0.0, R.dj_t - dt)
    tx_t = tz_t = bob = 0.0
    if R.char:                                   # personagem animado: escolhe a animacao pelo estado
        if R.dj_t > 0:
            name, rate = "jump", 1.7             # pulo duplo
        elif R.st == 3:                          # dash: o corpo se inclina para o lado em que ele vai
            name, rate = "air", 1.0
            tx_t = 55 if R.dk[0] > 0 else -35 if R.dk[0] < 0 else 0
            tz_t = 30 * R.dk[1]
        elif R.st == 2:
            name, rate, tz_t = "sprint", 1.0, -18 * R.ws    # parede: corre inclinado para longe dela
        elif R.st == 4:
            name, rate = "air", 1.0
        elif R.spd < 1:
            name, rate = "idle", 1.0
        elif R.spd < 4:
            name, rate = "walk", max(.6, R.spd / 2.6)
        elif R.spd < 8:
            name, rate = "jog", R.spd / 6
        else:
            name, rate = "sprint", R.spd / 9
        R.char.play(name, rate)
        R.char.update(dt)
    elif R.st == 3:      # (modelo simples) dash: inclinado para frente
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
