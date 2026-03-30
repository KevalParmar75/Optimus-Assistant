"""
HUD — Transformers Universe Taskbar UI
Horizontal strip, draggable, all 5 characters visible.
Active agent scales up + glows. Eye blinking + mouth animation.
"""
import tkinter as tk
import random
import time
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"

# ── HUD state palettes ──
HUD_PALETTES = {
    "STANDBY_EN":  {"primary": "#00eaff", "visor": "#00eaff", "glow": "#004466"},
    "STANDBY_HI":  {"primary": "#ff9900", "visor": "#ff9900", "glow": "#663300"},
    "STANDBY_GU":  {"primary": "#00ff9c", "visor": "#00ff9c", "glow": "#004433"},
    "LISTENING":   {"primary": "#ff2d2d", "visor": "#ff2d2d", "glow": "#550000"},
    "PROCESSING":  {"primary": "#ffd500", "visor": "#ffd500", "glow": "#665500"},
    "SPEAKING":    {"primary": "#00ff9c", "visor": "#00ff9c", "glow": "#004433"},
    "REMEMBERING": {"primary": "#cc44ff", "visor": "#cc44ff", "glow": "#440066"},
    "BROWSING":    {"primary": "#ff6600", "visor": "#ff6600", "glow": "#662200"},
    "CODING":      {"primary": "#00ff88", "visor": "#00ff88", "glow": "#004422"},
    "REMINDER":    {"primary": "#ff44aa", "visor": "#ff44aa", "glow": "#660033"},
    "SEEING":      {"primary": "#ffdd00", "visor": "#ffdd00", "glow": "#665500"},
}

# ── Agent order in strip ──
AGENT_ORDER = ["chat", "browser", "code", "memory", "reminder"]

# ── Pixel sizes ──
PS_SMALL  = 5    # inactive characters
PS_ACTIVE = 10   # active character

# ── Strip dimensions (calculated dynamically) ──
STRIP_COLS = 40  # all grids are 40 wide
STRIP_ROWS = 44  # max grid height

CHAR_W_SMALL  = STRIP_COLS * PS_SMALL   # 200
CHAR_H_SMALL  = STRIP_ROWS * PS_SMALL   # 220
CHAR_W_ACTIVE = STRIP_COLS * PS_ACTIVE  # 400
CHAR_H_ACTIVE = STRIP_ROWS * PS_ACTIVE  # 440

PADDING       = 12   # between characters
STRIP_H       = CHAR_H_ACTIVE + 40   # total strip height

# ── Blink config per character ──
BLINK_CONFIG = {
    "chat":     {"min": 3.5, "max": 6.0, "dur": 0.15},
    "browser":  {"min": 2.0, "max": 4.5, "dur": 0.12},
    "code":     {"min": 3.5, "max": 6.0, "dur": 0.15},
    "memory":   {"min": 5.0, "max": 9.0, "dur": 0.18},
    "reminder": {"min": 7.0, "max": 12.0,"dur": 0.20},
}

# ── Mouth animation ──
# 3 frames: 0=closed, 1=half, 2=open  (cycled at 100ms while SPEAKING)
MOUTH_FRAME_MS = 100

# ================================================================
# OPTIMUS pixel grid
# ================================================================
_OP_GRID = [
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
    "3381188881611166181181811611161118811811",  # row 30: mouth at cols 17-22 (char '6')
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
_OP_COLORS = {
    "1": None, "2": "#081428", "3": "#102a6e",
    "4": "#1a4898", "5": "#2d6fc0", "6": "#00ccff",
    "7": "#c8d8e8", "8": "#606878",
}
# Mouth rows/cols in the Optimus grid (row index, col range)
_OP_MOUTH_ROW = 30
_OP_MOUTH_COLS = range(17, 23)
_OP_MOUTH_OPEN_COLOR  = "#c8d8e8"
_OP_MOUTH_HALF_COLOR  = "#404858"
_OP_MOUTH_CLOSE_COLOR = "#606878"

# ================================================================
# BUMBLEBEE pixel grid
# ================================================================
_BB_GRID = [
    "1111GDD111111111111111111111111111111111",
    "111GDDDD1111111111111111111111GOD1111111",
    "1GDDDDDD1111111111111111111111GODD111111",
    "1GDDDDDD111111111GODDDOGD111111GODD11111",
    "1GODDDDDD1111GGGGK1GDDDDODDDGK11GDY11111",
    "11OOOGODDD111GDDDDOKGDDDDODDDYG1OGD11111",
    "111111GOOGDG1111KODO1GDDDDODODDGGOD11111",
    "1111111GGDDD111111ODG1DDDDDDDDDGG1O11111",
    "11111111GODGKGGG111DD1GDDDDODDDDGG111111",
    "111111GK1111KGGGG11GDGKDDDDODDDDGGKK1111",
    "11111DDDOG111GGGG11GDD1ODDDODODDGGGKK111",
    "1111GDDDDDG1111111KDDD1GDDDDOOODO1D11111",
    "1111DDDDDDDG11111GDDDDGKDDOROOOOO1DO1111",
    "1111G1ODODDDOGGODDDDDDO1DDDDDODDO1DDOG11",
    "1111OO1GDDDDDDDDDDDDDDO1GDDOOGOOD1DDDYK1",
    "111O1OD1ODDDDDDDDDDDDDDGKDDDOGODO1DDDDG1",
    "111111OO1DDDDDDDDDDDDDDG1DDDDODDD1DDDDG1",
    "1111111D1ODDDDDOOOOOODDO1ODDDDDDG1DDDDG1",
    "1111111OGGDDOGKK111KKGOG1GDDDDDDGGOGKKG1",
    "1DD11111O1DOK111111111K11GODDDDOG11111K1",
    "GDYD1111D1DG111KGK1111111GOGOOOO11111111",
    "1DDYDOG1G11K1D1111666611111GGG1166611G11",  # row 21: mouth col 4-7, eyes col 18-21,25-27
    "GGODDYDDOG11GD11116GGG611KG1GG116GG611OO",
    "GDOGOODDGGDGGDO11166G61111GGDD116G66111D",
    "GDDDOGD1111GGDDG1116661111DOOOG1G6611G1G",
    "1DDDDOD111111DDO1111111GGGDGODO11111GG1G",
    "1ODDDOD111111DDOGGGGGOO1GDD1KGDG1OGGD11G",
    "1GDDDOD111111GDODDDDDOGGGDG1KKKG1GDDO11G",
    "11ODDOD111111OGGOOGG1GDDDG111111YD1GG11G",
    "111ODGO111111DDG1KKKKODDDDDOGGDDDDKK1111",
    "11111GOG111O1ODGKGGGGKDDDDDDDDDDDOKG11G1",
    "1111111GGGG11ODGKGGGGKODDDGGGGGODGGG1111",
    "1111111111111ODO1GGGGGGDDGOOGGOODKKG1111",
    "1111111111111GDD1KGGGKDD1GGKGGKGGDKG1111",
    "11111111111111DDO1KKGDDO1OKGDDOG1DO11111",
    "111111111111111ODO1ODDDD1DKGDDGGGDO11111",
    "11111111K11111111ODGGODD1OGGDDDGGD111111",
    "1111111111111111111GGOGDG1DODDD1OG111111",
    "1111111111111111111111GGOO1ODDGGO1111111",
    "111111111111111111111111G11OOO1111111111",
    "1111111111111111111111111111111111111111",
    "111111111111111111111111K111111111111111",
    "111111111111111111D111111111O11111111111",
    "111111111111111111OG1111K111111111111111",
]
_BB_COLORS = {
    "1": None, "Y": "#FFD000", "D": "#C08800", "O": "#7A5000",
    "K": "#282A2E", "G": "#585A60", "R": "#CC1A10", "6": "#1A88FF",
}
_BB_MOUTH_ROW  = 21
_BB_MOUTH_COLS = range(4, 8)

# ================================================================
# WHEELJACK pixel grid
# ================================================================
_WJ_GRID = [
    "111111111111111111GWWWWWW111111111111111",
    "11111111111111111KKGWWWWWWWK111111111111",
    "111111111111111FFFHKGWWWWWWW111111111111",
    "111111111111111HFFFFKGWWWWWWG11111111111",
    "1111111111111111HFFFHGWWWWWWWK1111111111",
    "1111111111111KK11FFFFKWWWWWWWGH111111111",
    "1K111111111111KK11FFFKGWWWWWWWHK11111111",
    "KWG111111HF111KK11FEEHGWWWWWWWKH111111WK",
    "WWWK11111FFFH11KK1KFFHGWWWWWWWKFK1111GWW",
    "WWWW11111HHFFH11K11FFFKWWGGGGWKF11111WWW",
    "WWWWG111HHHHFFH111HFFFKWWGGGGWKFH111GWWW",
    "GWWWWK1111HHFFFEFFFFFFKGWWGGGWKFFF11WWWW",
    "KWWWWW11HH1HFFFFFFFFFFHGWWGGGWKFFFKWWWWW",
    "1WWWWWG111H1HFFFFFFHFFHKWWGGGWKFFFFWWWWK",
    "1GWWWWW111H1HHFFFFFFFFHKWWWGWWKFFFEGWWW1",
    "11WWWWWW1K111HFFHHHKHHHKWWWWWW1FFFFGWWW1",
    "11GWWWWW11111HHKGKKKGK1KGWWWWWKHKGKGWWK1",
    "11KWWWWG1K111HKK11111KKKGWWWWGKKK1KGWW11",
    "111WWWWG11111HK11KGG1111GGGGGG11111WWW11",
    "111GWWWWWG111KKK1G6666GG1KGGG1GG611WWK11",
    "1111WWWWWWWGK11G1G6GG6666GKKG66G61KWG111",
    "1111KWGWWWWWWG1GK1G666666GGGG666G1WG1111",  # row 21: mouth area
    "11111KGWWWW11GGGGGK1KGGGGGGGGGG1K11G1111",
    "111111GWWWG11GKGGGWGGKKKKGGWGKKGW1KK1111",
    "111111WWWWG11GKGGGWWWWWWWWGWWWWWG1KK1111",
    "111111GWWWG11GKGGGWWGWWWWWGWWWWWG1KK1111",
    "111111KWWWG1KGKKGGGWWWWWWWGGGWWWG1KK1111",
    "1111111WWWG1KGKHKGGGGWWWWWGGGWWGG1GK1111",
    "1111111KWGG1KGKHHKGGGGWWWWGGWWWGG1G11111",
    "111111111GGKGGK1HKGGGGWWWWWWWWWGKKG11111",
    "1111111111KGGG11HKGGGGWWGGGGGWWG11111111",
    "111111111K111111FKGGGGWWGWWWWWGG11111111",
    "1111111111111111F1GGGGWWWGGGGWGK11111111",
    "1111111111111111FHKGGGGWWGGGGWGK11111111",
    "1111111111111111HF1KGGGWGGGGGWGK11111111",
    "111111111111111111F1KGGGGKGGGGG111111111",
    "111111111111K111111HH1KGKWGGWG1111111111",
    "1111111111111F1111111HH1GWGGGG1111111111",
    "1111111111111H111111111GWKWWGG1111111111",
    "11111111111111111KK11111KKWWK11111111111",
    "111111111111111111F111111111111111111111",
    "111111111111111111H1111K1111111111111111",
    "111111111111111111KW1H1111KK111111111111",
    "1111111111111111111W11HFH111111111111111",
]
_WJ_COLORS = {
    "1": None, "E": "#44AA22", "F": "#2A7010", "H": "#184008",
    "K": "#202820", "G": "#505850", "W": "#D0D8D0", "6": "#00C8FF", "R": "#CC1A10",
}
_WJ_MOUTH_ROW  = 22
_WJ_MOUTH_COLS = range(18, 24)

# ================================================================
# IRONHIDE pixel grid
# ================================================================
_IH_GRID = [
    "1111111111DD1111111111111111111111111111",
    "1111111111DD1111111111111111111111OO1111",
    "111111111OR1111111111OOOO1111111111D1111",
    "111111111DD111111OOOODDDRRRD1111111D1111",
    "111111111R1111111111111ODDRRRD11111DO111",
    "11111OO1OD1111111O111111OODRRRD1111O1111",
    "111111O1DO111OODDDDDD1111OODRDRO111OO111",
    "111111O1D1111OODDDRRRRO111OD111ODD11D111",
    "11111111D111111DRRDRRRRO11OO1K11ODRO1111",
    "1111111OD11KK11ODRRRRRRD11D11KK11ORRO111",
    "111O111OD111KG111DRRDDDDO11KGGGGK1DDR111",
    "11111O1DO11KKKG11ORDDDDDD1GKRRRRKGODDD11",
    "1111111D1111KKKK11ODDDDDD1GRDRRRRKODDO11",
    "11111O1D111K111111K1DODDDO1GKKRKS1ODD111",
    "11O11O1O1111K11111KK11ODDD1GRRRRK1DDO1K1",
    "1111111O1111K111111K111ODDOKSRRKG1DD11K1",
    "111111111G111111111KKKK11111KGGG1DO11KK1",
    "1111K111KKG11K11111KK111KK111OOOD111KKK1",
    "1111KKK1GGK11K111111KKK11K11ODDDDK11KK11",
    "111KKKG1OS111111111111111KK11DOODK111111",
    "1111KKGKOSK1111111KKK11111111DDDD111KK1K",
    "1111K1GKOGK1O1D1111K1KKKK111111111KK111G",
    "1111K1K11G1111D111111661111KGGGG11661111",  # row 22: mouth col 5-9
    "111111K11K1111OD11KKK1KKGKKGKKGG11KKKKD1",
    "11K1K1111K1111ODRD11GGGGGK111KKKG1KGG1R1",
    "11KK111111111111DRRD1KK111111KKKGKKK1RR1",
    "11111111111K11111DDDD111111111KKK1111111",
    "1111111111KKK1111OO111111111111111111111",
    "11111111111K11111OD111111111111111111111",
    "11111111111K11111OD1111111111111K1111111",
    "11111111111111111OD111111111111111111111",
    "1111111111111ODO111OK111111111KKK1111111",
    "11111111111111ODDO1111111111111111111111",
    "111111111K111O11ODOKGSGK111111KK111GSK11",
    "111111111KG11111111GSSSSK1111KKKK11GSK11",
    "1111111G1K1111111O1GGG11K11111KKK111G111",
    "1111111GGK11G111111GGG11K1111DOOO111G111",
    "11111111K111KK1G111KGG11K111O1KKKO1KK111",
    "111111111K11GG11K1111KGGK111OKGGKOKK1111",
    "111111111111KG111K111K11111OOGGGKO111111",
    "1111111111111G1GKK1111G11111111111111111",
    "111111111111111GGKK1111GSG11111111111111",
    "1111111111111111KKSG1111K1111G1111111111",
    "111111111111111111SG111KGK11111111111111",
]
_IH_COLORS = {
    "1": None, "R": "#CC2000", "D": "#8A1200", "O": "#500800",
    "K": "#282020", "G": "#585050", "S": "#A09090", "6": "#1A88FF",
}
_IH_MOUTH_ROW  = 22
_IH_MOUTH_COLS = range(5, 10)

# ================================================================
# PERCEPTOR pixel grid
# ================================================================
_PC_GRID = [
    "11111RRO11111111111111111111111D11111111",
    "1111RRRR11111111111111111111111RR1111111",
    "111RRRRRO11111111111OODDD111111ORR111111",
    "111RRRRRD1111111111ODDDRRRRRDK11OR111111",
    "111ODDRRRO11111OO1111ODDDDDDOOO11DD11111",
    "111111ORRRD1111ODRRD11ODDD11GGTGTKD11111",
    "11111111DRRR1111KKDRD11ODD1GSK11TTO11111",
    "11111111ODRRD111111DRD11D1KST1KK1TK11111",
    "111111111ODO11KTK111DRK1O1KGTTTT1TK11111",
    "1111111111111KKKTK11KRD1111TTTTT1T11K111",
    "1111ODDDDDO111KKTK111RRK111KTTTKTK11T111",
    "1111DDDDRRRO11111111KRRD1OD11KKK1ODO1111",
    "111OO1OORRRRD11111KKRRRD11RDO111DRDDK111",
    "11111DDOORRRRDOODDRRRRRR11RRRRRRRRDDRR11",
    "1111111ODORRRRRRRRRRRRRRO1DRDRDDDRDDRRD1",
    "111111K11DORRRRRRRRRRRRRD1ORDDRRDRODRRR1",
    "111111111DODRRRRRRRRRRRRD1ORRRRRRR1DRRR1",
    "111KKKD111OORRRRDDDDDRRRR11RDDRRDRODRDD1",
    "1111KKKR11OORRD11KKKKKKOR11RRRDDRRO1K111",
    "1111OTTOD1OOOO1111111111111RRRRRRR11K111",
    "1111OKGKR11O11111KTTTTT11111ODDOO1TT111D",
    "111111TKD11111R111KT6TT61111111116K6T11D",  # row 21: mouth area
    "111111K1D11OODRD11KT6KK6111DDDODT6K6T11D",
    "111111K1O11DDDDRD11KT66T111ORRRRDT6611D1",
    "1111O111O11ODDDRRR11K111KKORRRRRRO111OR1",
    "11OO11111111ODDDRRRRO1OODRRRRRRRRRRO1RR1",
    "11111111111T1OODDRRDDODRRRRRRDODDRRDO1O1",
    "1111111111KKK1OODRD111ORRRRO1ODDD1RD1111",
    "11111111111111DOORD1111ODO1O11OODD111111",
    "111K1KK11111111OORD11OOD11O11ODDDO111111",
    "111111T1111111111DRK111DD11OO1OOODO11111",
    "1111111K11111RO111ODOO1OD1111DDDR111O111",
    "11111K1111111D1K11111111DO1DO111OD111D11",
    "1111111111111D111RD1KKT1OD111ODDO11TT111",
    "1111111111111DO11DO1GTTT1D11DDDDDO11T111",
    "1111111O1111111OODO1KT111DDRDODDDD11K111",
    "1111111OD111O1111OO1KK111DR1OD11DO11K111",
    "111111111DD1111111111K111RD1D1TKKO111111",
    "111111111OD1OD111111111K1DODD1KK1D111111",
    "1111111111111R11KT111111111DO1111D111111",
    "1111111111111O1DDK11K1111111111111111111",
    "111111111111111ORO111O11K111111111111111",
    "111111111111111111RO1OO1K1111D1111111111",
    "111111111111111111OO111DRD11111111111111",
]
_PC_COLORS = {
    "1": None, "R": "#CC2000", "D": "#8A1200", "O": "#500800",
    "K": "#201818", "G": "#504848", "S": "#908080", "T": "#405868", "6": "#1A88FF",
}
_PC_MOUTH_ROW  = 21
_PC_MOUTH_COLS = range(6, 11)

# ── Master character registry ──
CHARS = {
    "chat":     {"grid": _OP_GRID, "colors": _OP_COLORS, "visor": "6",
                 "mouth_row": _OP_MOUTH_ROW, "mouth_cols": _OP_MOUTH_COLS,
                 "mouth_open": _OP_MOUTH_OPEN_COLOR, "mouth_half": _OP_MOUTH_HALF_COLOR,
                 "mouth_close": _OP_MOUTH_CLOSE_COLOR},
    "browser":  {"grid": _BB_GRID, "colors": _BB_COLORS, "visor": "6",
                 "mouth_row": _BB_MOUTH_ROW, "mouth_cols": _BB_MOUTH_COLS,
                 "mouth_open": "#FFD000", "mouth_half": "#C08800", "mouth_close": "#7A5000"},
    "code":     {"grid": _WJ_GRID, "colors": _WJ_COLORS, "visor": "6",
                 "mouth_row": _WJ_MOUTH_ROW, "mouth_cols": _WJ_MOUTH_COLS,
                 "mouth_open": "#D0D8D0", "mouth_half": "#707870", "mouth_close": "#505850"},
    "memory":   {"grid": _PC_GRID, "colors": _PC_COLORS, "visor": "6",
                 "mouth_row": _PC_MOUTH_ROW, "mouth_cols": _PC_MOUTH_COLS,
                 "mouth_open": "#CC4040", "mouth_half": "#8A2020", "mouth_close": "#500808"},
    "reminder": {"grid": _IH_GRID, "colors": _IH_COLORS, "visor": "6",
                 "mouth_row": _IH_MOUTH_ROW, "mouth_cols": _IH_MOUTH_COLS,
                 "mouth_open": "#909090", "mouth_half": "#585050", "mouth_close": "#282020"},
}


def _draw_char_on_canvas(canvas, agent, cx, cy, ps,
                         visor_color, glow_color, pulse,
                         blink=False, mouth_frame=0):
    """Draw a single character at (cx,cy) with given pixel size."""
    char      = CHARS[agent]
    grid      = char["grid"]
    colors    = char["colors"]
    visor_key = char["visor"]
    mouth_row = char["mouth_row"]
    mouth_col = char["mouth_cols"]

    COLS = len(grid[0])
    ROWS = len(grid)
    ox   = cx - (COLS * ps) // 2
    oy   = cy - (ROWS * ps) // 2

    mouth_colors = [
        char["mouth_close"],
        char["mouth_half"],
        char["mouth_open"],
    ]
    mouth_fill = mouth_colors[mouth_frame]

    for ri, row in enumerate(grid):
        for ci, cell in enumerate(row):
            if cell == "1":
                continue
            x0 = ox + ci * ps
            y0 = oy + ri * ps
            x1 = x0 + ps
            y1 = y0 + ps

            # Mouth override
            if ri == mouth_row and ci in mouth_col:
                canvas.create_rectangle(x0, y0, x1, y1, fill=mouth_fill, outline="")
                continue

            # Visor / eye cells
            if cell == visor_key:
                if blink:
                    # Replace eye with helmet color (dark)
                    fill = colors.get("2") or "#081428"
                else:
                    if pulse > 0:
                        canvas.create_rectangle(x0-1, y0-1, x1+1, y1+1,
                                                fill=glow_color, outline="")
                    fill = visor_color
            else:
                fill = colors.get(cell)
                if fill is None:
                    continue

            canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="")


class TransformerHUD(tk.Tk):
    """
    Horizontal taskbar HUD — all 5 Transformers visible.
    Active agent scales up + glows.  Others dim slightly.
    Draggable, borderless, always-on-top.
    """

    def __init__(self):
        super().__init__()

        # ── Window setup ──
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)
        self.config(background="#000001")
        self.attributes("-transparentcolor", "#000001")

        # ── State ──
        self.active_agent  = "chat"
        self.status_text   = "STANDBY"
        self.current_lang  = "en"

        # ── Animation state ──
        self._pulse        = 0
        self._pulse_grow   = True
        self._mouth_frame  = 0
        self._mouth_tick   = 0

        # ── Scale animation per agent (float PS, target PS) ──
        self._scales   = {a: float(PS_SMALL) for a in AGENT_ORDER}
        self._scales["chat"] = float(PS_ACTIVE)  # Optimus starts active

        # ── Blink state per agent ──
        self._blink    = {a: False for a in AGENT_ORDER}

        # ── Calculate strip width ──
        # 4 small + 1 active + padding between 5 slots
        self._strip_w  = (4 * CHAR_W_SMALL + CHAR_W_ACTIVE +
                          5 * PADDING + PADDING)
        self._strip_h  = STRIP_H

        # Position — center-bottom of screen
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - self._strip_w) // 2
        y  = sh - self._strip_h - 40
        self.geometry(f"{self._strip_w}x{self._strip_h}+{x}+{y}")

        # ── Canvas ──
        self.canvas = tk.Canvas(self, width=self._strip_w, height=self._strip_h,
                                bg="#000001", highlightthickness=0)
        self.canvas.pack()

        # ── Drag ──
        self.canvas.bind("<Button-1>",   self._drag_start)
        self.canvas.bind("<B1-Motion>",  self._drag_move)

        # ── Status label ──
        self._status_var = tk.StringVar(value="STANDBY")
        self._label      = tk.Label(self, textvariable=self._status_var,
                                    fg="#ffffff", bg="#111111",
                                    font=("Consolas", 10, "bold"))
        self._label.place(x=0, y=self._strip_h - 22,
                          width=self._strip_w, height=20)

        # ── Start blink schedulers ──
        for agent in AGENT_ORDER:
            self._schedule_blink(agent)

        # ── Fade in + animate ──
        self._fade_in()
        self._animate()

    # ── Drag ───────────────────────────────────────────────────
    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag_move(self, e):
        nx = self.winfo_x() + e.x - self._dx
        ny = self.winfo_y() + e.y - self._dy
        self.geometry(f"+{nx}+{ny}")

    # ── Fade in ─────────────────────────────────────────────────
    def _fade_in(self):
        a = self.attributes("-alpha")
        if a < 1.0:
            self.attributes("-alpha", min(a + 0.06, 1.0))
            self.after(30, self._fade_in)

    # ── Public API (called from main.py) ────────────────────────
    def set_agent(self, agent: str):
        """Switch active character."""
        if agent not in AGENT_ORDER:
            agent = "chat"
        self.active_agent = agent

    def set_status(self, status: str):
        self.status_text = status
        try:
            self._status_var.set(status)
        except Exception:
            pass

    def set_language(self, lang: str):
        self.current_lang = lang

    # ── Blink scheduler ─────────────────────────────────────────
    def _schedule_blink(self, agent: str):
        cfg      = BLINK_CONFIG[agent]
        interval = random.uniform(cfg["min"], cfg["max"])
        ms       = int(interval * 1000)
        self.after(ms, lambda: self._do_blink(agent))

    def _do_blink(self, agent: str):
        cfg = BLINK_CONFIG[agent]
        self._blink[agent] = True
        dur_ms = int(cfg["dur"] * 1000)
        self.after(dur_ms, lambda: self._end_blink(agent))

    def _end_blink(self, agent: str):
        self._blink[agent] = False
        self._schedule_blink(agent)

    # ── Palette helper ───────────────────────────────────────────
    def _palette(self) -> dict:
        key = self.status_text
        if key not in HUD_PALETTES:
            lang_map = {"en": "STANDBY_EN", "hi": "STANDBY_HI", "gu": "STANDBY_GU"}
            key = lang_map.get(self.current_lang, "STANDBY_EN")
        return HUD_PALETTES.get(key, HUD_PALETTES["STANDBY_EN"])

    # ── Main animation loop (30 fps) ─────────────────────────────
    def _animate(self):
        # Pulse
        step = 0.4
        if self._pulse_grow:
            self._pulse += step
            if self._pulse > 10:
                self._pulse_grow = False
        else:
            self._pulse -= step
            if self._pulse < 0:
                self._pulse_grow = True

        # Mouth cycling (only during SPEAKING)
        if self.status_text == "SPEAKING...":
            self._mouth_tick += 1
            if self._mouth_tick >= (MOUTH_FRAME_MS // 33):  # ~3 ticks per frame at 30fps
                self._mouth_tick = 0
                self._mouth_frame = (self._mouth_frame + 1) % 3
        else:
            self._mouth_frame = 0
            self._mouth_tick  = 0

        # Scale animation — smooth lerp toward target
        for agent in AGENT_ORDER:
            target = float(PS_ACTIVE) if agent == self.active_agent else float(PS_SMALL)
            cur    = self._scales[agent]
            diff   = target - cur
            if abs(diff) > 0.1:
                self._scales[agent] = cur + diff * 0.18
            else:
                self._scales[agent] = target

        self._draw()
        self.after(33, self._animate)  # ~30 fps

    # ── Draw all characters ──────────────────────────────────────
    def _draw(self):
        self.canvas.delete("all")
        palette   = self._palette()
        pulse     = int(self._pulse)
        is_speak  = self.status_text == "SPEAKING..."

        # Calculate X positions for each slot
        # Active slot gets CHAR_W_ACTIVE, others get CHAR_W_SMALL
        x = PADDING
        positions = {}
        for agent in AGENT_ORDER:
            ps      = int(round(self._scales[agent]))
            w       = len(CHARS[agent]["grid"][0]) * ps
            positions[agent] = (x, ps, w)
            x += w + PADDING

        # Draw each character
        for agent in AGENT_ORDER:
            slot_x, ps, w = positions[agent]
            is_active = (agent == self.active_agent)
            rows = len(CHARS[agent]["grid"])
            h    = rows * ps

            # Center vertically in strip (leave room for label at bottom)
            cy   = (self._strip_h - 24) // 2
            cx   = slot_x + w // 2

            # Glow background for active character
            if is_active and pulse > 2:
                gpad = 8
                self.canvas.create_oval(
                    cx - w//2 - gpad, cy - h//2 - gpad,
                    cx + w//2 + gpad, cy + h//2 + gpad,
                    fill=palette["glow"], outline=""
                )

            # Dim inactive characters slightly
            vc = palette["visor"] if is_active else self._dim_color(palette["visor"])
            gc = palette["glow"]  if is_active else "#111111"

            _draw_char_on_canvas(
                canvas      = self.canvas,
                agent       = agent,
                cx          = cx,
                cy          = cy,
                ps          = ps,
                visor_color = vc,
                glow_color  = gc,
                pulse       = pulse if is_active else 0,
                blink       = self._blink[agent],
                mouth_frame = self._mouth_frame if (is_active and is_speak) else 0,
            )

            # Name tag under active character
            if is_active:
                names = {
                    "chat": "OPTIMUS", "browser": "BUMBLEBEE",
                    "code": "WHEELJACK", "memory": "PERCEPTOR",
                    "reminder": "IRONHIDE",
                }
                self.canvas.create_text(
                    cx, cy + h//2 + 8,
                    text=names[agent],
                    fill=palette["primary"],
                    font=("Consolas", 8, "bold"),
                    anchor="n"
                )

    @staticmethod
    def _dim_color(hex_color: str) -> str:
        """Darken a hex color to ~35% brightness for inactive characters."""
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            r = int(r * 0.35)
            g = int(g * 0.35)
            b = int(b * 0.35)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return "#333333"


# ── Legacy compatibility shim ─────────────────────────────────────
# main.py may call draw_agent() directly; keep it working.

def draw_agent(agent: str, canvas, cx: int, cy: int,
               palette: dict, pulse: int = 0):
    """Compatibility shim — draw a character at given position."""
    _draw_char_on_canvas(
        canvas      = canvas,
        agent       = agent,
        cx          = cx,
        cy          = cy,
        ps          = PS_ACTIVE,
        visor_color = palette.get("visor", "#00ccff"),
        glow_color  = palette.get("glow",  "#004466"),
        pulse       = pulse,
        blink       = False,
        mouth_frame = 0,
    )