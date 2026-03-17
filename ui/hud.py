"""
HUD — Transformers Universe UI
Optimus = pixel art (default)
All others = animated GIF
"""
import tkinter as tk
from PIL import Image, ImageTk
import os

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# ── Agent → GIF filename mapping ──
AGENT_GIF = {
    "browser":  "bumblebee.gif",
    "code":     "wheeljack.gif",
    "memory":   "perceptor.gif",
    "reminder": "ironhide.gif",
}

# ── HUD state palettes ──
HUD_PALETTES = {
    "STANDBY_EN":  {"primary": "#00eaff", "secondary": "#0077aa", "visor": "#00eaff", "glow": "#004466"},
    "STANDBY_HI":  {"primary": "#ff9900", "secondary": "#cc6600", "visor": "#ff9900", "glow": "#663300"},
    "STANDBY_GU":  {"primary": "#00ff9c", "secondary": "#00aa66", "visor": "#00ff9c", "glow": "#004433"},
    "LISTENING":   {"primary": "#ff2d2d", "secondary": "#aa0000", "visor": "#ff2d2d", "glow": "#550000"},
    "PROCESSING":  {"primary": "#ffd500", "secondary": "#aa8800", "visor": "#ffd500", "glow": "#665500"},
    "SPEAKING":    {"primary": "#00ff9c", "secondary": "#00aa66", "visor": "#00ff9c", "glow": "#004433"},
    "REMEMBERING": {"primary": "#cc44ff", "secondary": "#880099", "visor": "#cc44ff", "glow": "#440066"},
    "BROWSING":    {"primary": "#ff6600", "secondary": "#aa3300", "visor": "#ff6600", "glow": "#662200"},
    "CODING":      {"primary": "#00ff88", "secondary": "#00aa55", "visor": "#00ff88", "glow": "#004422"},
    "REMINDER":    {"primary": "#ff44aa", "secondary": "#aa0066", "visor": "#ff44aa", "glow": "#660033"},
}

# ── Optimus pixel art ──
_HEAD_GRID = [
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
    "1115311111111111111111111111111111131111",
    "1115318111111111111111111111111118131111",
    "1115318111111111154331111111111118131111",
    "1115318111111111111221111111111118131111",
    "1115318111111111153112211111111118131111",
    "1135318111111111135333211111111118131111",
    "1125328111111115551111312111111118131111",
    "1125325111115555188888832222111118131111",
    "1125325115555555581111832222221118131111",
    "1125325115555544581111811222222118231111",
    "1155115155544112111111181112222218111811",
    "1154118154312111111111182111122218111811",
    "1153111541555441811111181222221121111811",
    "1152155354333335811111181222222211111811",
    "1152533433333331811111118222222221111811",
    "1151433433333318111111118122222221111811",
    "1151433433333311111111118122222221111811",
    "1151433433333318111111118122222221111811",
    "1141433433333338818888111222222221111111",
    "1151431333333331811111188222222221111811",
    "1151431333333333811111111222222221111811",
    "1151431333333333181881882222222221111811",
    "1131431333333333381881112222222221111111",
    "1581331333333333388881822222222221111811",
    "5581411333333332281881812222222221121111",
    "4381181883333333218888112222232181811111",
    "3381188858111113388888822111118888811111",
    "3381188811221118181881818111121118811811",
    "3381188881611166181181811611161118811811",
    "3381188181812111818888111111111118811811",
    "3381158881881111188888111111111118811111",
    "3318181118881888888888188881188111818111",
    "3381858818888888811888188888888818888811",
    "2388888817877778718888188888818818111811",
    "2288888818777777771881881888881818188821",
    "1111188818777777877888888888881818811111",
    "1111188817777778577888888888888888811111",
    "1111188815777777777118888888888888811111",
    "1111111118777777777888888888888811111111",
    "1111118111777777777888888888881818111111",
    "1111118118187777777888888888118818111111",
    "1111118118888775777888888888888118111111",
    "1111118118818775577888888881181818111111",
    "1111118118851588777888881881888118111111",
    "1111111111818888887888888881181811111111",
    "1111188818881188877888818811188188811111",
    "1111111111111111111111111111111111111111",
]

_COLOR_MAP = {
    "1": None,       "2": "#081428",  "3": "#102a6e",
    "4": "#1a4898",  "5": "#2d6fc0",  "6": "#00ccff",
    "7": "#c8d8e8",  "8": "#606878",
}


def draw_optimus(canvas, cx: int, cy: int, palette: dict, pulse: int = 0):
    PS           = 10
    COLS         = len(_HEAD_GRID[0])
    ROWS         = len(_HEAD_GRID)
    ox           = cx - (COLS * PS) // 2
    oy           = cy - (ROWS * PS) // 2
    visor_color  = palette["visor"]
    glow_color   = palette["glow"]

    for ri, row in enumerate(_HEAD_GRID):
        for ci, cell in enumerate(row):
            if cell == "1":
                continue
            x0 = ox + ci * PS
            y0 = oy + ri * PS
            x1 = x0 + PS
            y1 = y0 + PS
            if cell == "6":
                if pulse > 0:
                    canvas.create_rectangle(x0-2, y0-2, x1+2, y1+2,
                                            fill=glow_color, outline="")
                fill = visor_color
            else:
                fill = _COLOR_MAP.get(cell)
                if fill is None:
                    continue
            canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="")


# ================================================================
# BUMBLEBEE — Browser Agent
# Extracted from clean reference — yellow armour, blue eyes
# Y=bright yellow  D=dark gold  O=shadow gold  K=dark grey
# G=mid grey  B=black  6=blue eyes
# ================================================================
_BB_GRID = [
    "11111KKK111111111111111111111GBG11111111",
    "1111BODD111111111111111111111K1DK1111111",
    "111BDDDDDB11111111GKKKKKKG111GBDDK111111",
    "11GODDDDDG11111GBBBODDDDD11K11BOYOG11111",
    "11GBDDDDD1111KBBBBB1ODDDDDYD1G1BOD111111",
    "111KBBODDD1BBBODDDOBBODDDDDDYDKB1DB11111",
    "11111GK1DDDDBBBB1ODDBBODDDDDDDOBBD1G1111",
    "1111111B1DDDDBBBBBBDD1BDYYYYYDY11BBG1111",
    "111111KBBODD1BBKBBBKYYKB1111111111BB1111",
    "11111KBBBBBBBBKKKBBB11OKD111111111KBG111",
    "1111G1DOO1BBBBKKKKBBKYDKBY111111111BB111",
    "1111BDOODDD1BBBBBBBBKDD1KDDDOOODO1DBBB11",
    "111KOOOODDDDOBBBBBBKDDDOBOO1OOOOO1D1BB11",
    "111BB1OO1DDDDOKK11DDDDDDB1DOODDODKODD1G1",
    "111B1BBOOODDDYYDDDDDDDDDBBDOODDDD1DDDDK1",
    "111BBBBBBO1DDDYDDDDDDDDDOBOOOOO1O1DDDYB1",
    "111BBBBBB1OODDDYDDDDDDDDOBODDOODD1ODDYB1",
    "11BB1B11BBO1DDDYDDDDDDDDDB1DOOOOD1ODDDB1",
    "1BBBBKKO1B1OODD1KKKKK11ODBBDDDDDDKOOKBB1",
    "GBBBOBGKDBBO1OBBBBBBBBBBBBBODDDDOBBBBBBK",
    "B1BBB1KG11B1OBBBBKK1BBBBBBBKB1OBBBBBKB1K",
    "BBBBB1KK11BBBBDOBBKB6116BBBBBBBBB116BBOB",
    "BBBBBBBB11B1OODDBBKB6116BBBOO1OO6116BB1B",
    "BBBBBBBBB1BOOOODDBBBB66BBBBODDDYKB6BBO1B",
    "KB1BB1BBBBBBOOODYD1BBBBBKK1DDDDYDBBBBD1B",
    "1BB1OBBBBBBBBOOODYYD1111DDDDDYDYYDDBOYB1",
    "1KBBBBBBBBBKKBOOODD1O1DDDDDDO1111DDOBBB1",
    "11BBBBBBBBBKBBOOODDBBBODDDOBBODD11DBBB11",
    "11GBBBBBBBBBBBOOODDBB1B1O1B1BB111OBBBBK1",
    "111BBBKBBBBBBBBOODDBB1OO111BBODDDBBBBBK1",
    "111GBBKKBBBBBBBBBOD1BB1OOB11BBBB111BBB11",
    "1111BBBBBBBBBOOBBBBOO1B1DBBBOODDDBBB1B11",
    "11111BBBBBBBBOBBBB1BBBBBD1OOBBBBB1BBBO11",
    "11111GBBBBBBBOBBBDDBGKGKBOBB1DDDBBKGKB11",
    "1111111BBBBBBBDBBOOBKKBBBOB1DODDDBBKBG11",
    "1111111BOBBBBBBBODOBBKBBBODD1O1O1BBKB111",
    "1111111BO11BBBBBBBBBKKBBBDOBDBKBOBBBB111",
    "11111111BBDBBBBBBBBBBBBBBDBOOBKK1BBB1111",
    "111111111KBBBKBBBBBBBBBBBBODBBBB11G11111",
    "11111111111BBBB11KBBBBBBBBBBBBBBBG111111",
    "111111111111GBBOD1BBBBBBKBBBBKBG11111111",
    "11111111111111KBOO1BBBBBBBBBBOB111111111",
    "1111111111111111BBDOBBBKGKBKBB1111111111",
    "11111111111111111GBB11BBBBK1B11111111111",
]
_BB_COLORS = {
    "1": None, "B": "#111114", "Y": "#FFD000",
    "D": "#C49000", "O": "#886000", "K": "#383A42",
    "G": "#686A72", "6": "#1A88FF",
}

# ================================================================
# WHEELJACK — Code Agent
# Extracted from reference — dark helmet, cyan wing panels
# K=dark helmet  G=mid grey  S=silver  C=cyan wings  B=black  6=visor
# ================================================================
_WJ_GRID = [
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
    "111111111111111111SGGSG11111111111111111",
    "11111111111111B1BBSGGSBB1B11111111111111",
    "111111111111GSSSKKSGGSKKSSSB111111111111",
    "111111111111SSSSKKSGGSKKSSSS111111111111",
    "111111111111KSSSKKSGGSKKSSSK111111111111",
    "11111111111BKSSSKKSGGSKKSSSKK11111111111",
    "11111111111KKSSGKKSGGSKKSSSKK11111111111",
    "11111111111KKBSSKKSSSSKKSSKKK11111111111",
    "111111111SCKKKKKKKGGGGKKKKKKKCG111111111",
    "1111111SCGGKKKKKKKGGGGKKKKKKKGGCC1111111",
    "111111CCGGGKKKKKKKKGGKKKKKKKKGGCCCG11111",
    "11SCGGGCGGGGKKKKKKKGGKKKKKKKGGGCCGCGCC11",
    "1CGCGGGCCCGGKKGGGGGGGGGGGGKKGGGCCGGGCGC1",
    "1CGGGGCGGGGGKKGGGGGGGGGGGGKKGGCGGGGGGGC1",
    "1GGGCCCGCGGGSSSSSSSSSSSSSSSSSGGGGGCCGGC1",
    "11CGCGCCCGGGGGGGGGGGGGGGGGGGGGGCCGGCGG11",
    "111GGGGCGGGSSSSSSSSSSSSSSSSSSGGGCGGGC111",
    "1111CCGCGGGSGGGGGGGGGGGGGGGGGGGGCGCC1111",
    "11111SCCGGGGSSSSSSSSSSSSSSSSGGGGCCG11111",
    "1111111GCCGGSSSSSSSSSSSSSSSSGGCCG1111111",
    "1111111111CGGGSSSSSSSSSSSSSGGC1111111111",
    "111111111111GCSSSSSSSSSSSSCC111111111111",
    "111111111111111GSGGGGGGSG111111111111111",
    "1111111111111111SSSSSSSS1111111111111111",
    "111111111111111111GSSKK11111111111111111",
    "1111111111111111111KK1111111111111111111",
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
]
_WJ_COLORS = {
    "1": None, "B": "#0f0f14", "K": "#2d2d37",
    "G": "#646970", "S": "#afb4bc", "C": "#8cdceb", "6": "#00beef",
}

# ================================================================
# IRONHIDE — Reminder Agent
# Extracted from reference — grey armour, purple/blue accents, yellow chin
# B=black  K=dark grey  G=mid grey  S=silver  P=purple/blue  Y=yellow  6=cyan eyes
# ================================================================
_IH_GRID = [
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
    "11111111111111111111G1111111111111111111",
    "111111111111111111SGGGSS1111111111111111",
    "111111111GG111111KGG1GGB111111GK11111111",
    "111111111KG1111GKGGGGGGGKG1111GK11111111",
    "11111111BGG111GPGGGKGGGGGPG111GGK1111111",
    "11111111KGGG1GPPGGGGGGGGGPPG1GGGK1111111",
    "11111111GKGKGGPKSGGSGSSGSKPGGGGKG1111111",
    "1111111KGGGGGKPPPKGGBGGKPPPKGGGGGK111111",
    "1111111GGGGGKGGPPPKKKKKPPPGKKGGGGG111111",
    "111111KGGKGGKKSKGKGGGGGGKKSKKGGKGGG11111",
    "111111KGGKGGKGGGKGGGGGGKKGGGKGGKGGG11111",
    "111111GGGGGKGGGGGGGGGGGBSGGGKGGGGGG11111",
    "111111GGGGGGKGGGGKGGKGGKGGGGKKGGGGK11111",
    "111111KGGGYGBGGGSKGGGGGKSGGGBGYGGGG11111",
    "1111111KGGYYGGGGGKGGGGGGGGGGGGYGGKG11111",
    "11111KGGGKGGKGGGGGGPPPGGGGGSKSGKGGBK1111",
    "11111KGSGGSGKKKBKGGGKGGGGKKKKSSKGGGK1111",
    "11111KGSBGS1SGKKGGGKGGKKGKKGS1SGBSGK1111",
    "11111KGBKBGS1KGKG6SKGKSGGKGK1SGKGBKG1111",
    "11111BKBKGKGSSGGGKGGGGGBGGGSSGKGKBKK1111",
    "111111GKGGGKGKKGPPGGGGGPPGKKGKGGGKG11111",
    "111111GBGGBGKGKGPPGGBGGGPGKSKGKGGKG11111",
    "1111111GSGKKKGGPPGGKBKGGPGSSKKKGSG111111",
    "11111111KGGGGBKGPGKKBKKKPGKKGKKGK1111111",
    "111111111B11BKGGPPGKBGGGPGGKB11B11111111",
    "11111111111111GGPPPPPPPPPGG1111111111111",
    "11111111111111GGPPPPPPPPPGG1111111111111",
    "111111111111111K11SSPGS11K11111111111111",
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
]
_IH_COLORS = {
    "1": None, "B": "#14141a", "K": "#373a46",
    "G": "#646973", "S": "#a0a5af", "P": "#503cb4", "Y": "#dcbe1e", "6": "#00d2e6",
}

# ================================================================
# PERCEPTOR — Memory Agent
# Red with orange scope, silver faceplate, cyan visor
# ================================================================
_PC_GRID = [
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
    "111111111111111OOOO1111111111111111111",
    "111111111111111OOOO1111111111111111111",
    "111111111111111SSSS1111111111111111111",
    "11111111111111RRSSRR111111111111111111",
    "1111111111111RRRRSSRRRR11111111111111",
    "111111111111RRRRRSSRRRRRR1111111111111",
    "1111111111RRRRRRSSSSRRRRRRR11111111111",
    "111111111RRRRRRRSSSSRRRRRRRR1111111111",
    "11111111RRRRRRRRRSSRRRRRRRRRR111111111",
    "1111111RRRRRRRRRRRRRRRRRRRRRRR11111111",
    "111111RRRRRRRRRRRRRRRRRRRRRRRRRR111111",
    "11111RRRRRRRRRRRRRRRRRRRRRRRRRRRR11111",
    "1111RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR111",
    "111RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR11",
    "11DRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRD111",
    "11DRRRRRRRRSSSSSSSSSSSSSSRRRRRRRRD111",
    "11DRRRRRRRSSSSSSSSSSSSSSSRRRRRRRRD111",
    "11DRRRRRRS1SS66666666SS1SRRRRRRRRD111",
    "11DRRRRRRSS166666666661SSRRRRRRRRD111",
    "11DRRRRRRS1SS66666666SS1SRRRRRRRRD111",
    "11DRRRRRRRSSSSSSSSSSSSSSSRRRRRRRRD111",
    "111DRRRRRRSSGGGGGGGGGGSSRRRRRRRRD1111",
    "111DRRRRRRSGGGGGGGGGGGGSRRRRRRRRD1111",
    "1111DRRRRRSGGWWWWWWWWGGRSRRRRRD111111",
    "1111DRRRRRSGGGWWWWWWWGGRSRRRRRD111111",
    "11111DRRRRRSGGGGGGGGGGSRRRRRRD1111111",
    "111111DRRRRRRSSSSSSSSRRRRRRD111111111",
    "1111111DRRRRRRRRRRRRRRRRRD11111111111",
    "11111111DDRRRRRRRRRRRRDD1111111111111",
    "111111111DDDRRRRRRRRRDDD1111111111111",
    "11111111111DDDDDDDDDDD111111111111111",
    "1111111111111111111111111111111111111111",
    "1111111111111111111111111111111111111111",
]
_PC_COLORS = {
    "1": None, "R": "#CC3333", "D": "#881111", "S": "#A0A8B0",
    "G": "#707880", "W": "#E8E8E8", "O": "#FF8800", "6": "#00CCFF",
}


def _draw_char(canvas, grid, color_map, cx, cy, visor_key="6",
               visor_color="#00CCFF", glow_color="#004466", pulse=0, ps=10):
    """Generic pixel art draw — works for all characters."""
    COLS = len(grid[0])
    ROWS = len(grid)
    ox   = cx - (COLS * ps) // 2
    oy   = cy - (ROWS * ps) // 2
    for ri, row in enumerate(grid):
        for ci, cell in enumerate(row):
            if cell == "1":
                continue
            x0 = ox + ci * ps
            y0 = oy + ri * ps
            x1 = x0 + ps
            y1 = y0 + ps
            if cell == visor_key:
                if pulse > 0:
                    canvas.create_rectangle(x0-2, y0-2, x1+2, y1+2,
                                            fill=glow_color, outline="")
                fill = visor_color
            else:
                fill = color_map.get(cell)
                if fill is None:
                    continue
            canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="")


def draw_bumblebee(canvas, cx, cy, palette, pulse=0):
    _draw_char(canvas, _BB_GRID, _BB_COLORS, cx, cy,
               visor_color=palette["visor"], glow_color=palette["glow"], pulse=pulse)

def draw_wheeljack(canvas, cx, cy, palette, pulse=0):
    _draw_char(canvas, _WJ_GRID, _WJ_COLORS, cx, cy,
               visor_color=palette["visor"], glow_color=palette["glow"], pulse=pulse)

def draw_ironhide(canvas, cx, cy, palette, pulse=0):
    _draw_char(canvas, _IH_GRID, _IH_COLORS, cx, cy,
               visor_color=palette["visor"], glow_color=palette["glow"], pulse=pulse)

def draw_perceptor(canvas, cx, cy, palette, pulse=0):
    _draw_char(canvas, _PC_GRID, _PC_COLORS, cx, cy,
               visor_color=palette["visor"], glow_color=palette["glow"], pulse=pulse)


# Master draw dispatcher
DRAW_FN = {
    "chat":     draw_optimus,
    "browser":  draw_bumblebee,
    "code":     draw_wheeljack,
    "memory":   draw_perceptor,
    "reminder": draw_ironhide,
}

def draw_agent(agent: str, canvas, cx, cy, palette, pulse=0):
    fn = DRAW_FN.get(agent, draw_optimus)
    fn(canvas, cx, cy, palette, pulse)


class GifPlayer:
    """Plays an animated GIF on a tkinter Canvas."""

    def __init__(self, canvas: tk.Canvas, cx: int, cy: int):
        self.canvas   = canvas
        self.cx       = cx
        self.cy       = cy
        self._frames  = []
        self._delays  = []
        self._idx     = 0
        self._job     = None
        self._img_id  = None
        self._active  = False

    def load(self, gif_path: str):
        self._frames = []
        self._delays = []
        try:
            img = Image.open(gif_path)
            for frame in range(img.n_frames):
                img.seek(frame)
                # Resize to fit nicely — 320x320
                resized = img.copy().convert("RGBA").resize((320, 320), Image.NEAREST)
                self._frames.append(ImageTk.PhotoImage(resized))
                delay = img.info.get("duration", 80)
                self._delays.append(max(delay, 40))
        except Exception as e:
            print(f"[HUD] GIF load failed: {e}")

    def start(self):
        if not self._frames:
            return
        self._active = True
        self._idx    = 0
        self._show_frame()

    def stop(self):
        self._active = False
        if self._job:
            self.canvas.after_cancel(self._job)
            self._job = None
        if self._img_id:
            self.canvas.delete(self._img_id)
            self._img_id = None

    def _show_frame(self):
        if not self._active or not self._frames:
            return
        if self._img_id:
            self.canvas.delete(self._img_id)
        frame = self._frames[self._idx]
        self._img_id = self.canvas.create_image(
            self.cx, self.cy, image=frame, anchor="center"
        )
        # Keep reference to prevent GC
        self.canvas._gif_frame = frame
        self._idx = (self._idx + 1) % len(self._frames)
        delay     = self._delays[self._idx]
        self._job = self.canvas.after(delay, self._show_frame)