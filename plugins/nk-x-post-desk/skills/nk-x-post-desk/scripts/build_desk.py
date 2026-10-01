#!/usr/bin/env python3
"""build_desk.py — turn a folder of drafted X posts into one page of prefilled composer links.

    python3 build_desk.py <desk-folder>                 check every post, then write <desk-folder>/desk.html
    python3 build_desk.py <desk-folder> --out FILE      the same, written to FILE
    python3 build_desk.py <desk-folder> --check         check only; exit 1 on any problem, write nothing
    python3 build_desk.py <desk-folder> --allow-root-link   let the root post carry a link (refused by default)
    python3 build_desk.py --demo [--out FILE]           build the bundled example into ./demo-desk.html
    python3 build_desk.py --count "some text"           print the length of a text as X counts it ("-" reads stdin)
    python3 build_desk.py --selftest                    run the checks below against planted samples

The desk folder (full format: references/format.md):

    my-desk/
      desk.json                      optional: {"title": "...", "note": "...", "allowRootLink": true}
      2026-11-03-short-name/         one folder per post: the day you plan to post it, then a lower-case name
        post.md                      the root post, then each reply; parts separated by a line of =====
        picture.png                  optional, at most one: .png .jpg .jpeg .gif .webp
        alt.txt                      optional: the picture's description, to paste into X

What is checked (any problem stops the build, and then nothing is written):

    F01 no desk folder, or no post folder in it      F02 a folder not named YYYY-MM-DD-name, or a date that does not exist
    F03 post.md missing, empty or not UTF-8          F04 an empty part (two separators in a row, or one at an edge)
    F05 more than one picture, an unsupported        F06 a picture that is empty, over 5 MB, or not the type its
        picture type, or alt.txt with no picture         name says
    F07 desk.json with a wrong key or value          P01 a part over 280 as X counts it
    P02 a link in the root post (unless allowed)     P03 a control character in a part

One notice, which stops nothing: a bare file name in a reply that X will turn into a link (notes.md, main.py).

The page: one file, pictures embedded, no request to any other host (a Content-Security-Policy in the page forbids
them, and the build reads its own output back and refuses to write a page that refers to anything outside itself
except the links to X's composer). Nothing here posts, and nothing here opens x.com: the buttons are plain links to
X's documented web intent (https://x.com/intent/tweet with text and in_reply_to) that the reader taps.
Standard library only, Python 3.9+. Exit: 0 fine · 1 problems found or a failed self-test · 2 usage error.
"""
import base64, datetime, hashlib, html, json, os, re, shutil, struct, sys, tempfile, unicodedata, urllib.parse, zlib
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLE = os.path.join(os.path.dirname(HERE), "references", "example-desk")
LIMIT = 280
INTENT = "https://x.com/intent/tweet"     # X's documented web intent; parameters used here: text, in_reply_to
MAX_PICTURE = 5 * 1024 * 1024
SEPARATOR = re.compile(r"^={5,}$")
POST_DIR = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
# A published post's link, and nothing else around it: (x|twitter).com/<name>/status/<digits>. The same pattern is
# written into the page, where it decides whether a pasted link may become a reply link.
STATUS_PATTERN = r"^(?:https?://)?(?:www\.|mobile\.)?(?:x|twitter)\.com/(?:[A-Za-z0-9_]{1,30}|i/web)/status/([0-9]{5,25})(?:[/?#]\S*)?$"
PICTURES = {".png": ("image/png", lambda b: b[:8] == b"\x89PNG\r\n\x1a\n"),
            ".jpg": ("image/jpeg", lambda b: b[:3] == b"\xff\xd8\xff"),
            ".jpeg": ("image/jpeg", lambda b: b[:3] == b"\xff\xd8\xff"),
            ".gif": ("image/gif", lambda b: b[:6] in (b"GIF87a", b"GIF89a")),
            ".webp": ("image/webp", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP")}
OTHER_PICTURES = {".svg", ".heic", ".heif", ".bmp", ".tif", ".tiff", ".avif", ".ico", ".psd"}


# ── How X counts a post ──────────────────────────────────────────────────────────────────────────────────────────────
# Read from X's own counting library, github.com/twitter/twitter-text (config/v3.json and js/src/regexp/*):
#   - the limit is 280 "weighted" characters, after Unicode NFC normalisation;
#   - every link counts 23, whatever its length. A link is an http(s) URL, or a bare domain: any name ending in a real
#     top-level domain, with or without a path. So `CLAUDE.md`, `main.py` and `run.sh` are links too (.md, .py and .sh
#     are country domains); `x.txt`, `report.html` and `node.js` are not;
#   - a character counts 1 inside U+0000-10FF, U+2000-200D, U+2010-201F, U+2032-2037, and 2 everywhere else: Chinese,
#     Japanese and Korean text, full-width punctuation, arrows, the ellipsis character, check marks, emoji.
# X_TLDS is the ASCII part of that library's two domain lists. Not copied: its non-ASCII domains, and its emoji table
# (X counts a whole emoji sequence as 2; here each code point of it counts, so an emoji sequence can come out higher
# than on X, never lower).
X_TLDS = frozenset("""
aaa aarp abarth abb abbott abbvie abc able abogado abudhabi ac academy accenture accountant accountants aco active actor ad adac ads adult ae aeg aero
aetna af afamilycompany afl africa ag agakhan agency ai aig aigo airbus airforce airtel akdn al alfaromeo alibaba alipay allfinanz allstate ally
alsace alstom am americanexpress americanfamily amex amfam amica amsterdam an analytics android anquan anz ao aol apartments app apple aq aquarelle ar
arab aramco archi army arpa art arte as asda asia associates at athleta attorney au auction audi audible audio auspost author auto autos avianca aw
aws ax axa az azure ba baby baidu banamex bananarepublic band bank bar barcelona barclaycard barclays barefoot bargains baseball basketball bauhaus
bayern bb bbc bbt bbva bcg bcn bd be beats beauty beer bentley berlin best bestbuy bet bf bg bh bharti bi bible bid bike bing bingo bio biz bj bl
black blackfriday blanco blockbuster blog bloomberg blue bm bms bmw bn bnl bnpparibas bo boats boehringer bofa bom bond boo book booking boots bosch
bostik boston bot boutique box bq br bradesco bridgestone broadway broker brother brussels bs bt budapest bugatti build builders business buy buzz bv
bw by bz bzh ca cab cafe cal call calvinklein cam camera camp cancerresearch canon capetown capital capitalone car caravan cards care career careers
cars cartier casa case caseih cash casino cat catering catholic cba cbn cbre cbs cc cd ceb center ceo cern cf cfa cfd cg ch chanel channel charity
chase chat cheap chintai chloe christmas chrome chrysler church ci cipriani circle cisco citadel citi citic city cityeats ck cl claims cleaning click
clinic clinique clothing cloud club clubmed cm cn co coach codes coffee college cologne com comcast commbank community company compare computer comsec
condos construction consulting contact contractors cooking cookingchannel cool coop corsica country coupon coupons courses cpa cr credit creditcard
creditunion cricket crown crs cruise cruises csc cu cuisinella cv cw cx cy cymru cyou cz dabur dad dance data date dating datsun day dclk dds de deal
dealer deals degree delivery dell deloitte delta democrat dental dentist desi design dev dhl diamonds diet digital direct directory discount discover
dish diy dj dk dm dnp do docs doctor dodge dog doha domains doosan dot download drive dtv dubai duck dunlop duns dupont durban dvag dvr dz earth eat
ec eco edeka edu education ee eg eh email emerck energy engineer engineering enterprises epost epson equipment er ericsson erni es esq estate esurance
et etisalat eu eurovision eus events everbank exchange expert exposed express extraspace fage fail fairwinds faith family fan fans farm farmers
fashion fast fedex feedback ferrari ferrero fi fiat fidelity fido film final finance financial fire firestone firmdale fish fishing fit fitness fj fk
flickr flights flir florist flowers flsmidth fly fm fo foo food foodnetwork football ford forex forsale forum foundation fox fr free fresenius frl
frogans frontdoor frontier ftr fujitsu fujixerox fun fund furniture futbol fyi ga gal gallery gallo gallup game games gap garden gay gb gbiz gd gdn ge
gea gent genting george gf gg ggee gh gi gift gifts gives giving gl glade glass gle global globo gm gmail gmbh gmo gmx gn godaddy gold goldpoint golf
goo goodhands goodyear goog google gop got gov gp gq gr grainger graphics gratis green gripe grocery group gs gt gu guardian gucci guge guide guitars
guru gw gy hair hamburg hangout haus hbo hdfc hdfcbank health healthcare help helsinki here hermes hgtv hiphop hisamitsu hitachi hiv hk hkt hm hn
hockey holdings holiday homedepot homegoods homes homesense honda honeywell horse hospital host hosting hot hoteles hotels hotmail house how hr hsbc
ht htc hu hughes hyatt hyundai ibm icbc ice icu id ie ieee ifm iinet ikano il im imamat imdb immo immobilien in inc industries infiniti info ing ink
institute insurance insure int intel international intuit investments io ipiranga iq ir irish is iselect ismaili ist istanbul it itau itv iveco iwc
jaguar java jcb jcp je jeep jetzt jewelry jio jlc jll jm jmp jnj jo jobs joburg jot joy jp jpmorgan jprs juegos juniper kaufen kddi ke kerryhotels
kerrylogistics kerryproperties kfh kg kh ki kia kim kinder kindle kitchen kiwi km kn koeln komatsu kosher kp kpmg kpn kr krd kred kuokgroup kw ky
kyoto kz la lacaixa ladbrokes lamborghini lamer lancaster lancia lancome land landrover lanxess lasalle lat latino latrobe law lawyer lb lc lds lease
leclerc lefrak legal lego lexus lgbt li liaison lidl life lifeinsurance lifestyle lighting like lilly limited limo lincoln linde link lipsy live
living lixil lk llc llp loan loans locker locus loft lol london lotte lotto love lpl lplfinancial lr ls lt ltd ltda lu lundbeck lupin luxe luxury lv
ly ma macys madrid maif maison makeup man management mango map market marketing markets marriott marshalls maserati mattel mba mc mcd mcdonalds
mckinsey md me med media meet melbourne meme memorial men menu meo merckmsd metlife mf mg mh miami microsoft mil mini mint mit mitsubishi mk ml mlb
mls mm mma mn mo mobi mobile mobily moda moe moi mom monash money monster montblanc mopar mormon mortgage moscow moto motorcycles mov movie movistar
mp mq mr ms msd mt mtn mtpc mtr mu museum mutual mutuelle mv mw mx my mz na nab nadex nagoya name nationwide natura navy nba nc ne nec net netbank
netflix network neustar new newholland news next nextdirect nexus nf nfl ng ngo nhk ni nico nike nikon ninja nissan nissay nl no nokia
northwesternmutual norton now nowruz nowtv np nr nra nrw ntt nu nyc nz obi observer off office okinawa olayan olayangroup oldnavy ollo om omega one
ong onion onl online onyourside ooo open oracle orange org organic orientexpress origins osaka otsuka ott ovh pa page pamperedchef panasonic panerai
paris pars partners parts party passagens pay pccw pe pet pf pfizer pg ph pharmacy phd philips phone photo photography photos physio piaget pics
pictet pictures pid pin ping pink pioneer pizza pk pl place play playstation plumbing plus pm pn pnc pohl poker politie porn post pr pramerica praxi
press prime pro prod productions prof progressive promo properties property protection pru prudential ps pt pub pw pwc py qa qpon quebec quest qvc
racing radio raid re read realestate realtor realty recipes red redstone redumbrella rehab reise reisen reit reliance ren rent rentals repair report
republican rest restaurant review reviews rexroth rich richardli ricoh rightathome ril rio rip rmit ro rocher rocks rodeo rogers room rs rsvp ru rugby
ruhr run rw rwe ryukyu sa saarland safe safety sakura sale salon samsclub samsung sandvik sandvikcoromant sanofi sap sapo sarl sas save saxo sb sbi
sbs sc sca scb schaeffler schmidt scholarships school schule schwarz science scjohnson scor scot sd se search seat secure security seek select sener
services ses seven sew sex sexy sfr sg sh shangrila sharp shaw shell shia shiksha shoes shop shopping shouji show showtime shriram si silk sina
singles site sj sk ski skin sky skype sl sling sm smart smile sn sncf so soccer social softbank software sohu solar solutions song sony soy space
spiegel sport spot spreadbetting sr srl srt ss st stada staples star starhub statebank statefarm statoil stc stcgroup stockholm storage store stream
studio study style su sucks supplies supply support surf surgery suzuki sv swatch swiftcover swiss sx sy sydney symantec systems sz tab taipei talk
taobao target tatamotors tatar tattoo tax taxi tc tci td tdk team tech technology tel telecity telefonica temasek tennis teva tf tg th thd theater
theatre tiaa tickets tienda tiffany tips tires tirol tj tjmaxx tjx tk tkmaxx tl tm tmall tn to today tokyo tools top toray toshiba total tours town
toyota toys tp tr trade trading training travel travelchannel travelers travelersinsurance trust trv tt tube tui tunes tushu tv tvs tw tz ua ubank ubs
uconnect ug uk um unicom university uno uol ups us uy uz va vacations vana vanguard vc ve vegas ventures verisign versicherung vet vg vi viajes video
vig viking villas vin vip virgin visa vision vista vistaprint viva vivo vlaanderen vn vodka volkswagen volvo vote voting voto voyage vu vuelos wales
walmart walter wang wanggou warman watch watches weather weatherchannel webcam weber website wed wedding weibo weir wf whoswho wien wiki williamhill
win windows wine winners wme wolterskluwer woodside work works world wow ws wtc wtf xbox xerox xfinity xihuan xin xperia xxx xyz yachts yahoo yamaxun
yandex ye yodobashi yoga yokohama you youtube yt yun za zappos zara zero zip zippo zm zone zuerich zw
""".split())
_X_CAND = re.compile(r"(https?://)?((?:[A-Za-z0-9](?:[A-Za-z0-9_-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,})(?![A-Za-z0-9@+-])"
                     r"((?::[0-9]+)?(?:[/?][A-Za-z0-9!*';:=+,.$/%#\[\]\-\u2013_~@|&()?]*)?)")
_X_NARROW = ((0x0000, 0x10FF), (0x2000, 0x200D), (0x2010, 0x201F), (0x2032, 0x2037))


def x_urls(text):
    """[(start, end)] of the pieces X treats as links."""
    out, pos = [], 0
    while True:
        m = _X_CAND.search(text, pos)
        if not m:
            return out
        proto, domain, tail = m.group(1) or "", m.group(2), m.group(3)
        before = text[m.start() - 1] if m.start() else ""
        # not right after a letter, a digit, @ $ #; a bare domain also not after - _ . /
        if (before and re.match(r"[A-Za-z0-9@\uff20$#\uff03]", before)) or (not proto and before and before in "-_./"):
            pos = m.start() + 1
            continue
        labels = domain.split(".")
        k = next((k for k in range(len(labels), 1, -1) if labels[k - 1].lower() in X_TLDS), 0)
        if not k:                                   # no real top-level domain in it: plain text, also after http://
            pos = m.end()
            continue
        if k == len(labels):
            while tail and not re.match(r"[A-Za-z0-9+\-=_#/]", tail[-1]):     # a path cannot end in . , ; : ! ? ) ...
                tail = tail[:-1]
            end = m.start() + len(proto) + len(domain) + len(tail)
        else:                                       # "example.com.zzz": the link is "example.com"
            end = m.start() + len(proto) + len(".".join(labels[:k]))
        out.append((m.start(), end))
        pos = end


# File endings that are also real top-level domains. A bare name that ends in one is a file name to the writer and a
# link to X: CLAUDE.md, main.py, run.sh, lib.rs.
FILE_ENDINGS = frozenset("md py sh rs pl pm ps cc mm ml mk tf zip mov java".split())


def file_like(link):
    """True for a piece X links that reads as a file name: no http(s)://, no path, and one of FILE_ENDINGS at the end."""
    if re.match(r"https?://", link, re.I) or not re.fullmatch(r"[A-Za-z0-9._-]+", link):
        return False                                    # a typed link, or a name with a path: written as a link
    return link.rsplit(".", 1)[-1].lower() in FILE_ENDINGS


def _x_weight(text):
    return sum(1 if any(a <= ord(c) <= b for a, b in _X_NARROW) else 2 for c in text)


def x_len(s):
    """The length of a post as X counts it."""
    s = unicodedata.normalize("NFC", s)
    total, pos = 0, 0
    for a, b in x_urls(s):
        total += _x_weight(s[pos:a]) + 23
        pos = b
    return total + _x_weight(s[pos:])


# ── Links ────────────────────────────────────────────────────────────────────────────────────────────────────────────
def status_id(link):
    """The id of a published post, from its link; None for anything that is not exactly such a link."""
    m = re.search(STATUS_PATTERN, str(link or "").strip())     # search, as the page's RegExp.exec does: the anchors are in the pattern
    return m.group(1) if m else None


def encoded(text):
    return urllib.parse.quote(text, safe="-_.!~*'()")     # the same characters JavaScript's encodeURIComponent keeps


def intent_url(text, reply_to=None):
    """The composer link for a text; with reply_to (a status id, digits only) it opens as a reply to that post."""
    if reply_to is not None and not re.fullmatch(r"[0-9]{5,25}", str(reply_to)):
        raise ValueError("reply_to must be a status id: 5 to 25 digits")
    return INTENT + "?" + (f"in_reply_to={reply_to}&" if reply_to is not None else "") + "text=" + encoded(text)


# ── Reading and checking a desk folder ───────────────────────────────────────────────────────────────────────────────
def split_parts(text):
    """post.md → the parts, in order. Line ends are normalised and spaces at the end of a line are dropped (X would
    count them); blank lines around a part are dropped; blank lines inside a part are kept."""
    lines = [l.rstrip() for l in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    parts, cur = [], []
    for l in lines:
        if SEPARATOR.match(l):
            parts.append("\n".join(cur).strip("\n"))
            cur = []
        else:
            cur.append(l)
    parts.append("\n".join(cur).strip("\n"))
    return parts


def read_desk(folder, allow_root_link=False):
    """(desk, problems, notes). desk = {"title", "note", "posts": [{"id", "date", "name", "parts", "lens", "picture"}]};
    problems = [(code, where, message)], empty when the folder keeps the format; notes = files that were skipped, and
    file names X will link. A link in the root post is a problem unless allow_root_link is true or desk.json says
    "allowRootLink": true."""
    problems, notes = [], []
    bad = lambda code, where, msg: problems.append((code, where, msg))
    desk = {"title": "X Post Desk", "note": "", "posts": []}
    if not os.path.isdir(folder):
        bad("F01", folder, "there is no such folder")
        return desk, problems, notes
    cfg = os.path.join(folder, "desk.json")
    if os.path.isfile(cfg):
        try:
            data = json.loads(open(cfg, encoding="utf-8").read())
        except (ValueError, UnicodeDecodeError) as e:
            data = None
            bad("F07", "desk.json", f"it is not valid JSON ({str(e)[:80]})")
        if data is not None:
            if not isinstance(data, dict):
                bad("F07", "desk.json", 'it must be an object like {"title": "...", "note": "..."}')
            else:
                for k, v in data.items():
                    if k == "allowRootLink":
                        if isinstance(v, bool):
                            allow_root_link = allow_root_link or v
                        else:
                            bad("F07", "desk.json", '"allowRootLink" must be true or false')
                        continue
                    cap = {"title": 80, "note": 400}.get(k)
                    if cap is None:
                        bad("F07", "desk.json", f'unknown key "{k}": only "title", "note" and "allowRootLink" are read')
                    elif not isinstance(v, str) or len(v) > cap or re.search(r"[\x00-\x08\x0b-\x1f\x7f]", v):
                        bad("F07", "desk.json", f'"{k}" must be plain text of at most {cap} characters')
                    elif str(v).strip():
                        desk[k] = " ".join(str(v).split())
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not os.path.isdir(path):
            continue                                        # desk.json, desk.html and anything else at the top is left alone
        if name.startswith((".", "_")):
            notes.append(f"{name}/: skipped (its name starts with '{name[0]}')")
            continue
        m = POST_DIR.match(name)
        if not m:
            bad("F02", name + "/", "a post folder is named YYYY-MM-DD-name, the name in lower-case letters, digits and "
                                   "hyphens (for example 2026-11-03-launch). Rename it, or start its name with _ to leave it out")
            continue
        try:
            day = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            bad("F02", name + "/", f"{name[:10]} is not a date that exists")
            continue
        post = {"id": name, "date": day, "name": m.group(4), "parts": [], "lens": [], "picture": None}
        files = sorted(f for f in os.listdir(path) if not f.startswith(".") and os.path.isfile(os.path.join(path, f)))
        pics = [f for f in files if os.path.splitext(f)[1].lower() in PICTURES]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in OTHER_PICTURES:
                bad("F05", f"{name}/{f}", f"{ext} pictures are not embedded: save it as .png, .jpg, .gif or .webp")
            elif f not in ("post.md", "alt.txt") and ext not in PICTURES:
                notes.append(f"{name}/{f}: not read (a post folder holds post.md, one picture and alt.txt)")
        if len(pics) > 1:
            bad("F05", name + "/", f"{len(pics)} pictures ({', '.join(pics)}): a post folder holds at most one")
        elif pics:
            pic = os.path.join(path, pics[0])
            data = open(pic, "rb").read()
            mime, looks_right = PICTURES[os.path.splitext(pics[0])[1].lower()]
            if not data:
                bad("F06", f"{name}/{pics[0]}", "the file is empty")
            elif len(data) > MAX_PICTURE:
                bad("F06", f"{name}/{pics[0]}", f"{len(data) / 1048576:.1f} MB: the page embeds every picture, the limit is 5 MB each")
            elif not looks_right(data):
                bad("F06", f"{name}/{pics[0]}", f"the content is not {mime} (the first bytes do not match the file name)")
            else:
                post["picture"] = {"file": pics[0], "mime": mime, "data": data, "alt": ""}
        if "alt.txt" in files:
            if not pics:
                bad("F05", f"{name}/alt.txt", "a picture description with no picture next to it")
            else:
                try:
                    alt = " ".join(open(os.path.join(path, "alt.txt"), encoding="utf-8").read().split())
                except UnicodeDecodeError:
                    alt = None
                    bad("F05", f"{name}/alt.txt", "it is not UTF-8 text")
                if alt and post["picture"]:
                    post["picture"]["alt"] = alt
        src = os.path.join(path, "post.md")
        if "post.md" not in files:
            bad("F03", name + "/", "there is no post.md in it")
            continue
        try:
            text = open(src, encoding="utf-8").read()
        except UnicodeDecodeError:
            bad("F03", f"{name}/post.md", "it is not UTF-8 text")
            continue
        if text.startswith("\ufeff"):
            text = text[1:]
        if not text.strip():
            bad("F03", f"{name}/post.md", "it is empty")
            continue
        parts = split_parts(text)
        for i, p in enumerate(parts):
            where = f"{name}/post.md {'root' if i == 0 else 'reply ' + str(i)}"
            if not p.strip():
                bad("F04", where, "this part is empty: a line of ===== must have text before it and after it")
                continue
            ctrl = re.search(r"[\x00-\x09\x0b-\x1f\x7f\u2028\u2029]", p)
            if ctrl:
                bad("P03", where, f"it holds a control character (U+{ord(ctrl.group()):04X}): take it out, a tab becomes spaces")
            n = x_len(p)
            if n > LIMIT:
                bad("P01", where, f"{n} as X counts it, the limit is {LIMIT} ({n - LIMIT} over)")
        if parts and parts[0].strip() and not allow_root_link:
            links = [parts[0][a:b] for a, b in x_urls(unicodedata.normalize("NFC", parts[0]))]
            typed = [l for l in links if re.match(r"https?://", l, re.I)]
            bare = [l for l in links if l not in typed]
            allow = 'or allow root links: --allow-root-link, or "allowRootLink": true in desk.json'
            if typed:
                bad("P02", f"{name}/post.md root", f"the root post carries a link ({', '.join(repr(l) for l in typed)}). "
                    f"Move it to a reply, {allow}")
            if bare:
                bad("P02", f"{name}/post.md root", f"X turns {', '.join(repr(l) for l in bare)} into a link (a name that ends in a "
                    f"real top-level domain; it counts 23). Reword it or move it to a reply, {allow}")
        for i, p in enumerate(parts):
            if p.strip() and (i > 0 or allow_root_link):       # where a link is allowed, a file name still becomes one
                where = f"{name}/post.md {'root' if i == 0 else 'reply ' + str(i)}"
                for l in [p[a:b] for a, b in x_urls(unicodedata.normalize("NFC", p))]:
                    if file_like(l):
                        msg = (f"X turns {l!r} into a link (.{l.rsplit('.', 1)[-1].lower()} is a real top-level domain) and "
                               "counts it as 23. Nothing is refused; reword the name if a live link is not what you mean")
                        notes.append(f"{where}: {msg}")          # a notice, never a problem: the build goes on
        post["parts"] = parts
        post["lens"] = [x_len(p) for p in parts]
        desk["posts"].append(post)
    if not problems and not desk["posts"]:
        bad("F01", folder, "there is no post folder in it (expected at least one folder named YYYY-MM-DD-name)")
    return desk, problems, notes


# ── The page ─────────────────────────────────────────────────────────────────────────────────────────────────────────
CSS = """
:root{--bg:#fbf7f6;--surface:#ffffff;--ink:#22302a;--muted:#5d6c64;--line:#e6dcda;--green:#2a644c;--green-soft:#e4efe9;
--pink:#a63f60;--pink-soft:#f8e3e9;--display:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
--body:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#14201b;--surface:#1b2a24;--ink:#eef2ee;--muted:#a3b3aa;--line:#2e4038;
--green:#8fd0af;--green-soft:#21382e;--pink:#f09bb4;--pink-soft:#3d2430;color-scheme:dark}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);font-size:16px;line-height:1.55;padding:28px 16px 56px}
.wrap{max-width:780px;margin:0 auto;display:flex;flex-direction:column;gap:22px}
header{display:flex;flex-direction:column;gap:8px}
h1{font-family:var(--display);font-weight:400;font-size:2rem;line-height:1.15;margin:0}
h2{font-family:var(--display);font-weight:400;font-size:1.3rem;line-height:1.2;margin:0;overflow-wrap:anywhere}
h3{font:600 .95rem var(--body);margin:0;display:flex;gap:10px;align-items:center}
p{margin:0}
.lede{color:var(--muted);max-width:62ch}
.label{font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);font-weight:600}
.note{background:var(--pink-soft);border-radius:10px;padding:13px 16px}
.posts{display:flex;flex-direction:column;gap:14px}
details.card{background:var(--surface);border:1px solid var(--line);border-radius:14px}
details.card>summary{list-style:none;cursor:pointer;padding:16px 20px;display:flex;gap:8px 12px;align-items:center;justify-content:space-between}
details.card>summary::-webkit-details-marker{display:none}
details.card>summary:focus-visible{outline:2px solid var(--pink);outline-offset:2px;border-radius:14px}
.sum-left{display:flex;flex-direction:column;gap:2px;min-width:0}
.sum-right{display:flex;gap:10px;align-items:center;flex:none}
.meta{font-size:.84rem;color:var(--muted)}
.fold{font-size:.8rem;color:var(--muted)}
details[open] .fold .closed,details:not([open]) .fold .opened{display:none}
.chip{font-size:.75rem;font-weight:700;padding:3px 10px;border-radius:999px;white-space:nowrap;background:var(--green-soft);color:var(--green)}
.chip.done{background:var(--pink-soft);color:var(--pink)}
.body{padding:0 20px 20px;display:flex;flex-direction:column;gap:16px}
.step{display:flex;flex-direction:column;gap:10px;min-width:0;border-top:1px solid var(--line);padding-top:14px}
.n{flex:none;width:1.6rem;height:1.6rem;border-radius:50%;background:var(--green-soft);color:var(--green);display:inline-flex;align-items:center;justify-content:center;font:700 .8rem var(--mono)}
pre.post{font-family:var(--mono);font-size:.86rem;line-height:1.55;white-space:pre-wrap;overflow-wrap:anywhere;background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:13px;margin:0}
pre.alt{font-family:var(--body)}
.count{font-family:var(--mono);font-size:.8rem;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
a.btn,button.btn{font:600 .95rem var(--body);border-radius:10px;padding:11px 16px;border:1px solid var(--green);cursor:pointer;text-decoration:none;display:inline-block;min-height:44px}
a.btn.primary{background:var(--green);color:var(--bg)}
a.btn.primary[aria-disabled="true"]{opacity:.45;pointer-events:none}
button.btn{background:transparent;color:var(--green)}
a.btn:focus-visible,button.btn:focus-visible,input:focus-visible{outline:2px solid var(--pink);outline-offset:2px}
input[type=text]{font:500 16px var(--mono);width:100%;padding:11px 12px;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--ink);min-width:0}
.hint{font-size:.86rem;color:var(--muted)}
.hint.bad{color:var(--pink)}
.hint.ok{color:var(--green)}
.path{font-family:var(--mono);font-size:.82rem;overflow-wrap:anywhere}
img.media{border:1px solid var(--line);border-radius:10px;display:block;max-width:100%;height:auto}
footer{display:flex;flex-direction:column;gap:8px;border-top:1px solid var(--line);padding-top:16px}
[hidden]{display:none}
@media (min-width:760px){
.body.has-pic{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:0 22px;align-items:start}
.body.has-pic>.step{grid-column:2;margin-bottom:16px}
.body.has-pic>.step.pic{grid-column:1;grid-row:1 / span 12}
}
"""

JS = """
(function(){
"use strict";
var INTENT="https://x.com/intent/tweet";
var STATUS=new RegExp(__STATUS__);
var storageOk=true;
function statusId(s){var m=STATUS.exec(String(s==null?"":s).trim());return m?m[1]:null;}
function load(k){try{return window.localStorage.getItem("xpd:"+k)||"";}catch(e){storageOk=false;return "";}}
function save(k,v){try{if(v){window.localStorage.setItem("xpd:"+k,v);}else{window.localStorage.removeItem("xpd:"+k);}}catch(e){storageOk=false;}}
function each(sel,root,fn){Array.prototype.forEach.call(root.querySelectorAll(sel),fn);}
function tally(){
  var all=document.querySelectorAll("details.card").length,done=document.querySelectorAll("details.card.is-done").length;
  var t=document.querySelector("[data-tally]");if(t){t.textContent=all+(all===1?" post":" posts")+" \\u00b7 "+done+" posted";}
}
each("button[data-copy]",document,function(btn){
  var label=btn.textContent,timer=0;
  btn.addEventListener("click",function(){
    var pre=document.getElementById(btn.getAttribute("data-copy"));if(!pre){return;}
    function say(t){btn.textContent=t;window.clearTimeout(timer);timer=window.setTimeout(function(){btn.textContent=label;},2200);}
    function selectIt(){var r=document.createRange();r.selectNodeContents(pre);var s=window.getSelection();s.removeAllRanges();s.addRange(r);
      var ok=false;try{ok=document.execCommand("copy");}catch(e){}say(ok?"Copied":"Selected: copy it now");}
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(pre.textContent).then(function(){say("Copied");},selectIt);}else{selectIt();}
  });
});
var opened=false;
each("details.card",document,function(card){
  var id=card.getAttribute("data-post"),done=load(id+":done")==="1";
  var chip=card.querySelector("[data-chip]"),mark=card.querySelector("[data-mark]");
  function paint(){
    chip.textContent=done?"Posted":"Ready";chip.className="chip"+(done?" done":"");
    mark.textContent=done?"Mark as not posted":"Mark as posted";
    if(done){card.classList.add("is-done");}else{card.classList.remove("is-done");}
    tally();
  }
  mark.addEventListener("click",function(){done=!done;save(id+":done",done?"1":"");paint();if(done){card.open=false;}});
  each("input[data-link]",card,function(input){
    var n=input.getAttribute("data-link"),step=input.parentNode,hint=step.querySelector("[data-hint]"),a=step.querySelector("a[data-reply]");
    input.value=load(id+":link:"+n);
    function refresh(){
      var raw=input.value.trim(),sid=statusId(raw);
      if(sid){a.setAttribute("href",INTENT+"?in_reply_to="+sid+a.getAttribute("data-tail"));a.setAttribute("aria-disabled","false");
        hint.textContent="Got it. This reply will go under post "+sid+".";hint.className="hint ok";}
      else{a.removeAttribute("href");a.setAttribute("aria-disabled","true");
        hint.textContent=raw?"That is not a post link. It looks like https://x.com/name/status/1234567890":"Waiting for the link.";hint.className=raw?"hint bad":"hint";}
      save(id+":link:"+n,raw);
    }
    input.addEventListener("input",refresh);refresh();
  });
  paint();
  if(!done&&!opened){card.open=true;opened=true;}else{card.open=false;}
});
tally();
save("probe","1");
if(!storageOk){var w=document.querySelector("[data-nostore]");if(w){w.hidden=false;}}
})();
"""


def _b64hash(text):
    return base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


def day_label(d):
    return f"{d:%a} {d.day} {d:%b} {d.year}"


def render(desk):
    """The whole page as one string. Every piece of the desk's text goes through html.escape; the script and the style
    are fixed texts whose sha256 is the only script and style the page's Content-Security-Policy allows."""
    e = lambda s: html.escape(s, quote=True)
    script = JS.replace("__STATUS__", json.dumps(STATUS_PATTERN))
    cards = []
    for post in desk["posts"]:
        pid, parts, pic = post["id"], post["parts"], post["picture"]
        n_replies = len(parts) - 1
        meta = ("post" if not n_replies else f"post + {n_replies} repl{'y' if n_replies == 1 else 'ies'}") + (" · picture" if pic else "")
        steps, k = [], 1
        if pic:
            src = f"data:{pic['mime']};base64,{base64.b64encode(pic['data']).decode('ascii')}"
            alt_block = (f'<span class="label">Picture description, for X\'s ALT field</span><pre class="post alt" id="a-{pid}">{e(pic["alt"])}</pre>'
                         f'<div class="row"><button type="button" class="btn" data-copy="a-{pid}">Copy description</button></div>') if pic["alt"] else ""
            steps.append(f'<section class="step pic"><h3><span class="n">{k}</span>Save the picture</h3>'
                         f'<img class="media" alt="{e(pic["alt"])}" src="{src}">'
                         f'<p class="hint">On a phone, press and hold the picture and save it. On a computer it is the file '
                         f'<span class="path">{e(pid + "/" + pic["file"])}</span>. A link cannot attach a picture, so you add it in X.</p>'
                         f'{alt_block}</section>')
            k += 1
        steps.append(f'<section class="step"><h3><span class="n">{k}</span>The post</h3>'
                     f'<pre class="post" id="t-{pid}-0">{e(parts[0])}</pre>'
                     f'<div class="row"><a class="btn primary" target="_blank" rel="noopener noreferrer" href="{e(intent_url(parts[0]))}">Open in X with this text</a>'
                     f'<button type="button" class="btn" data-copy="t-{pid}-0">Copy text</button><span class="count">{post["lens"][0]} / {LIMIT}</span></div>'
                     f'<p class="hint">{"In X: add the picture, then press Post." if pic else "In X: press Post."}</p></section>')
        k += 1
        for i in range(1, len(parts)):
            ask = ("Paste the link of the post you just published. The button then opens this text as a reply to it." if i == 1 else
                   f"Paste the link of reply {i - 1}, which you just published, so this one continues the thread.")
            steps.append(f'<section class="step"><h3><span class="n">{k}</span>{"Reply" if n_replies == 1 else f"Reply {i} of {n_replies}"}</h3>'
                         f'<pre class="post" id="t-{pid}-{i}">{e(parts[i])}</pre>'
                         f'<label class="hint" for="l-{pid}-{i}">{ask}</label>'
                         f'<input type="text" id="l-{pid}-{i}" data-link="{i}" inputmode="url" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="https://x.com/name/status/1234567890">'
                         f'<p class="hint" data-hint>Waiting for the link.</p>'
                         f'<div class="row"><a class="btn primary" data-reply data-tail="{e("&text=" + encoded(parts[i]))}" aria-disabled="true" target="_blank" rel="noopener noreferrer">Open the reply in X</a>'
                         f'<button type="button" class="btn" data-copy="t-{pid}-{i}">Copy text</button><span class="count">{post["lens"][i]} / {LIMIT}</span></div></section>')
            k += 1
        steps.append(f'<section class="step"><h3><span class="n">{k}</span>Done</h3>'
                     f'<div class="row"><button type="button" class="btn" data-mark>Mark as posted</button>'
                     f'<span class="hint">Remembered in this browser only.</span></div></section>')
        cards.append(f'<details class="card" id="p-{pid}" data-post="{pid}"{" open" if not cards else ""}>'
                     f'<summary><span class="sum-left"><span class="label">{e(day_label(post["date"]))}</span><h2>{e(post["name"])}</h2>'
                     f'<span class="meta">{meta}</span></span><span class="sum-right"><span class="chip" data-chip>Ready</span>'
                     f'<span class="fold"><span class="closed">show</span><span class="opened">hide</span></span></span></summary>'
                     f'<div class="body{" has-pic" if pic else ""}">{"".join(steps)}</div></details>')
    n = len(desk["posts"])
    csp = (f"default-src 'none'; img-src data:; style-src 'sha256-{_b64hash(CSS)}'; script-src 'sha256-{_b64hash(script)}'; "
           "base-uri 'none'; form-action 'none'")
    note = f'<p class="note">{e(desk["note"])}</p>' if desk["note"] else ""
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            f"<meta http-equiv=\"Content-Security-Policy\" content=\"{e(csp)}\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<meta name=\"referrer\" content=\"no-referrer\">\n"
            f"<title>{e(desk['title'])}</title>\n<style>{CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">\n"
            f"<header><span class=\"label\" data-tally>{n} post{'' if n == 1 else 's'}</span><h1>{e(desk['title'])}</h1>"
            "<p class=\"lede\">Each post opens in X with the words already typed. You add the picture and press Post yourself. "
            "Nothing here posts for you.</p></header>\n"
            f"{note}\n<section class=\"posts\">\n" + "\n".join(cards) + "\n</section>\n"
            "<footer><p class=\"hint\" data-nostore hidden>This browser is not keeping anything for this page (a private window, or "
            "storage is blocked): posted marks and pasted links will be gone when you close it.</p>"
            "<p class=\"hint\">Posted marks and pasted links are kept in this browser's local storage on this device, and nowhere else. "
            "The page asks no other site for anything; the X buttons are ordinary links that open X's composer when you press them.</p>"
            "<p class=\"hint\">If X opens a new post where you expected a reply: close it, open your post in X, press Reply and paste the "
            "copied text.</p>"
            "<p class=\"hint\">Built by X Post Desk (build_desk.py). Not affiliated with X.</p>"
            "<noscript><p class=\"hint\">Without JavaScript the first button of each post still works; reply links, copy buttons and "
            "posted marks do not.</p></noscript></footer>\n</div>\n"
            f"<script>{script}</script>\n</body>\n</html>\n")


class _Audit(HTMLParser):
    """Reads a built page the way a browser would see its markup: every element, every attribute, the text of every pre."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.problems, self.tags, self.pre, self.links, self.reply_links, self.csp = [], [], {}, [], [], ""
        self.blocks = {"script": [], "style": []}
        self._in, self._pre = None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append(tag)
        if tag in ("link", "iframe", "frame", "object", "embed", "form", "base", "video", "audio", "source", "track", "svg", "math"):
            self.problems.append(f"a <{tag}> element")
        for k, v in attrs:
            v = v or ""
            if k.startswith("on"):
                self.problems.append(f"an inline handler: <{tag} {k}=…>")
            if k in ("src", "srcset", "poster", "data", "action", "formaction", "background", "ping", "manifest", "style"):
                if not (tag == "img" and k == "src" and re.match(r"data:image/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]*$", v)):
                    self.problems.append(f"<{tag} {k}=…> points outside the page: {v[:60]}")
            if k == "href":
                if tag == "a" and v.startswith(INTENT + "?text="):
                    self.links.append(v)
                else:
                    self.problems.append(f"<{tag} href=…> is not a link to X's composer: {v[:60]}")
        if tag == "a" and "data-reply" in a:
            self.reply_links.append(a.get("href"))
        if tag == "meta" and (a.get("http-equiv") or "").lower() == "content-security-policy":
            self.csp = a.get("content") or ""
        if tag == "meta" and (a.get("http-equiv") or "").lower() == "refresh":
            self.problems.append("a <meta refresh>")
        if tag in self.blocks:
            self._in = tag
            self.blocks[tag].append("")
        if tag == "pre":
            self._pre = a.get("id")
            self.pre[self._pre] = ""

    def handle_endtag(self, tag):
        if tag == self._in:
            self._in = None
        if tag == "pre":
            self._pre = None

    def handle_data(self, data):
        if self._in:
            self.blocks[self._in][-1] += data
        elif self._pre is not None:
            self.pre[self._pre] += data


NETWORK_WORDS = ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource", "importScripts", "import(", ".src=", "location.href=",
                 "location.assign", "location.replace", "window.open", "document.write", "innerHTML", "eval(", "Function(")


def audit_page(page):
    """(problems, parsed). problems lists everything in a built page that could make a browser ask another host for
    something, or run text as markup: empty for a page this script may write."""
    p = _Audit()
    p.feed(page)
    p.close()
    out = list(p.problems)
    if len(p.blocks["script"]) != 1 or len(p.blocks["style"]) != 1:
        out.append(f"{len(p.blocks['script'])} script blocks and {len(p.blocks['style'])} style blocks (one of each is written)")
    for kind in ("script", "style"):
        for text in p.blocks[kind]:
            if f"{kind}-src 'sha256-{_b64hash(text)}'" not in p.csp:
                out.append(f"a {kind} block the page's Content-Security-Policy does not name")
    if "default-src 'none'" not in p.csp or "img-src data:" not in p.csp:
        out.append("no Content-Security-Policy that forbids requests (default-src 'none'; img-src data:)")
    for text in p.blocks["style"]:
        for word in ("url(", "@import", "image-set(", "src:"):
            if word in text:
                out.append(f"the style sheet uses {word}")
    for text in p.blocks["script"]:
        for word in NETWORK_WORDS:
            if word in text:
                out.append(f"the script uses {word}")
    return out, p


def _n(count, word):
    return f"{count} {word}" + ("" if count == 1 else "s")


def report(desk, problems, notes, out=sys.stdout):
    for post in desk["posts"]:
        if not any(w.startswith(post["id"] + "/") for _, w, _ in problems):
            lens = " · ".join(f"{'root' if i == 0 else 'reply ' + str(i)} {n}" for i, n in enumerate(post["lens"]))
            print(f"✔ {post['id']} · {lens}" + (f" · picture {post['picture']['file']}" if post["picture"] else ""), file=out)
    for n in notes:
        print(f"· {n}", file=out)
    for code, where, msg in problems:
        print(f"✘ {code} {where}: {msg}", file=out)
    parts = sum(len(p["parts"]) for p in desk["posts"])
    print(f"{_n(len(desk['posts']), 'post')}, {_n(parts, 'part')}, {_n(len(problems), 'problem')}", file=out)


def build(folder, out_path=None, check_only=False, out=sys.stdout, _render=None, allow_root_link=False):
    desk, problems, notes = read_desk(folder, allow_root_link)
    report(desk, problems, notes, out)
    if problems:
        print("nothing written" if not check_only else "check failed", file=out)
        return 1
    if check_only:
        return 0
    page = (_render or render)(desk)
    leaks, _ = audit_page(page)
    if leaks:
        for l in leaks:
            print(f"✘ A01 the built page failed its own audit: {l}", file=out)
        print("nothing written", file=out)
        return 1
    out_path = out_path or os.path.join(folder, "desk.html")
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    os.replace(tmp, out_path)
    pics = sum(1 for p in desk["posts"] if p["picture"])
    print(f"written {out_path} · {_n(len(desk['posts']), 'post')} · {_n(pics, 'picture')} embedded · {len(page.encode('utf-8')) / 1024:.0f} KB · "
          "0 references outside the page", file=out)
    return 0


# ── Self-test ────────────────────────────────────────────────────────────────────────────────────────────────────────
# (text, X's count). The rule and this table were first checked against X's own library on 2026-10-01.
X_LEN_CASES = [
    ("hello", 5),
    ("a https://example.org/some/very/long/path/that/is/longer/than/twenty-three b", 27),   # 2 + 23 + 2
    ("see example.org.", 28),                              # a bare domain: 4 + 23, and the full stop after it
    ("example.com/someone/some-repo", 23),
    ("CLAUDE.md is a file", 33),                           # .md is a country domain: a link on X
    ("main.py", 23), ("x.txt and report.html", 21), ("node.js", 7), ("v1.2.3", 6), ("e.g. this", 9),
    ("write me@example.com", 20),                          # after @ it is not a link
    ("http://localhost/abc", 20),                          # no real top-level domain: plain text
    ("example.com.zzz", 27),                               # the link is example.com
    ("\u4f60\u597d\uff0c\u4e16\u754c", 10),                # a CJK line: five wide characters
    ("\u65e5\u672c\u8a9e abc", 10),
    ("na\u00efve caf\u00e9", 10), ("e\u0301", 1),             # accents count 1; a decomposed e-acute is normalised first
    ("wait\u2026 \u2192 \u2713", 12),                       # ellipsis, arrow and check mark count 2 each
    ("\u201cquoted\u201d \u2014 dash", 15),                 # curly quotes and the em dash count 1
    ("\U0001f600", 2),
    ("https://example.org/a\u4f60\u597d", 27),              # a path stops at the first CJK character
]
STATUS_CASES = [
    ("https://x.com/someone/status/1234567890123456789", "1234567890123456789"),
    ("x.com/someone/status/12345", "12345"),
    ("https://twitter.com/someone/status/1234567890?s=20", "1234567890"),
    ("https://mobile.x.com/i/web/status/1234567890", "1234567890"),
    ("  https://x.com/someone/status/1234567890/photo/1  ", "1234567890"),
    ("https://x.com/someone", None),
    ("https://x.com/someone/status/12ab", None),
    ("https://x.com/someone/status/1234", None),                            # too short to be an id
    ("https://example.com/x.com/someone/status/1234567890", None),          # another site with the path of a post link
    ("https://notx.com/someone/status/1234567890", None),
    ("https://x.com.example.org/someone/status/1234567890", None),
    ("javascript:alert(1)//x.com/a/status/1234567890", None),
    ("1234567890", None),
    ("see https://x.com/someone/status/1234567890", None),                  # text around the link
    ("https://x.com/someone/status/1234567890 and more", None),
    ("", None),
]
HOSTILE = ('</pre></section><script>alert(1)</script><img src="https://evil.example/p.png" onerror="alert(2)">\n'
           '"><a href="https://evil.example/">tap</a> &amp; &lt;b&gt; <!-- --> ${x} \\u003c </script>')


def _png(w=4, h=3, rgb=(47, 107, 82)):
    """A real, tiny PNG (standard library only)."""
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    chunk = lambda tag, data: struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def _desk(tmp, name, posts, cfg=None):
    """Write a desk folder: posts = {folder name: {file name: text or bytes}}."""
    root = os.path.join(tmp, name)
    os.makedirs(root)
    for folder, files in posts.items():
        os.makedirs(os.path.join(root, folder))
        for f, body in files.items():
            with open(os.path.join(root, folder, f), "wb") as fh:
                fh.write(body if isinstance(body, bytes) else body.encode("utf-8"))
    if cfg is not None:
        with open(os.path.join(root, "desk.json"), "w", encoding="utf-8") as fh:
            fh.write(cfg if isinstance(cfg, str) else json.dumps(cfg))
    return root


def selftest():
    results = []
    tmp = tempfile.mkdtemp(prefix="x_post_desk_")
    codes = lambda folder: sorted({c for c, _, _ in read_desk(folder)[1]})
    quiet = open(os.devnull, "w")

    def tid():
        return f"T{len(results) + 1:02d}"

    def check(tid, label, ok, detail=""):
        results.append(ok)
        print(f"  {'✔' if ok else '✘'} {tid} {label}" + (f" — {detail}" if detail and not ok else ""))

    # T01 the count
    wrong = [(t, want, x_len(t)) for t, want in X_LEN_CASES if x_len(t) != want]
    check(tid(), f"X's count: {len(X_LEN_CASES) - len(wrong)}/{len(X_LEN_CASES)} sample texts match",
          not wrong, "; ".join(f"{t!r} counted {got}, X counts {want}" for t, want, got in wrong[:3]))
    check(tid(), f"the domain list holds {len(X_TLDS)} names; com, org, md, py, dev are in it; txt, html, js are not",
          len(X_TLDS) == 1419 and {"com", "org", "md", "py", "dev"} <= X_TLDS and not ({"txt", "html", "js"} & X_TLDS))

    # T03 a clean desk has no problem; T04.. each planted mistake trips exactly its own code
    ok280 = "a" * 256 + " example.org/page"                       # 256 + 1 + 23 = 280: the last length that passes
    clean = _desk(tmp, "clean", {"2026-11-03-launch": {"post.md": "the root\n=====\nthe reply example.org\n", "p.png": _png(), "alt.txt": "a green square"},
                                 "2026-11-06-second": {"post.md": "only a root\n"}}, {"title": "My desk", "note": "one a day"})
    check(tid(), "a desk that keeps the format has no problem", codes(clean) == [], f"got {codes(clean)}")
    edge = _desk(tmp, "edge", {"2026-11-03-edge": {"post.md": "root\n=====\n" + ok280}})
    over = _desk(tmp, "over", {"2026-11-03-over": {"post.md": "root\n=====\n" + ok280 + "!"}})
    check(tid(), "a part of exactly 280 passes and one of 281 is refused (P01)",
          x_len(ok280) == 280 and codes(edge) == [] and codes(over) == ["P01"] and build(over, check_only=True, out=quiet) == 1,
          f"280 → {codes(edge)}, 281 → {codes(over)}")
    wide = _desk(tmp, "wide", {"2026-11-03-wide": {"post.md": "\u4f60" * 141}})
    check(tid(), "141 wide characters count 282 and are refused (P01)", codes(wide) == ["P01"], f"got {codes(wide)}")
    planted = [
        ("a link in the root post", {"2026-11-03-a": {"post.md": "read it at https://example.org/x\n=====\nreply"}}, None, ["P02"]),
        ("a file name that X treats as a link, in the root post", {"2026-11-03-a": {"post.md": "see notes.md for it\n=====\nreply"}}, None, ["P02"]),
        ("a folder that is not named YYYY-MM-DD-name", {"launch-post": {"post.md": "root"}, "2026-11-03-a": {"post.md": "root"}}, None, ["F02"]),
        ("a date that does not exist", {"2026-02-30-a": {"post.md": "root"}, "2026-11-03-a": {"post.md": "root"}}, None, ["F02"]),
        ("a post folder with no post.md", {"2026-11-03-a": {"notes.txt": "root"}}, None, ["F03"]),
        ("an empty part", {"2026-11-03-a": {"post.md": "root\n=====\n\n=====\nreply 2"}}, None, ["F04"]),
        ("two pictures in one post", {"2026-11-03-a": {"post.md": "root", "a.png": _png(), "b.png": _png()}}, None, ["F05"]),
        ("a picture that is not what its name says", {"2026-11-03-a": {"post.md": "root", "a.png": b"<svg onload=alert(1)>"}}, None, ["F06"]),
        ("a desk.json with an unknown key", {"2026-11-03-a": {"post.md": "root"}}, {"title": "t", "theme": "dark"}, ["F07"]),
        ("a desk.json that is not JSON", {"2026-11-03-a": {"post.md": "root"}}, "{title: desk}", ["F07"]),
        ("a control character in a part", {"2026-11-03-a": {"post.md": "root\x00text"}}, None, ["P03"]),
        ("a post.md that is not UTF-8", {"2026-11-03-a": {"post.md": b"caf\xe9 root"}}, None, ["F03"]),
        ("a post.md with nothing in it", {"2026-11-03-a": {"post.md": "\n\n"}}, None, ["F03"]),
        ("a picture type the page does not embed", {"2026-11-03-a": {"post.md": "root", "a.svg": "<svg/>"}}, None, ["F05"]),
        ("a picture description with no picture", {"2026-11-03-a": {"post.md": "root", "alt.txt": "a square"}}, None, ["F05"]),
        ("a picture over 5 MB", {"2026-11-03-a": {"post.md": "root", "a.png": _png() + b"\x00" * MAX_PICTURE}}, None, ["F06"]),
        ("a desk.json whose title is not text", {"2026-11-03-a": {"post.md": "root"}}, {"title": 5}, ["F07"]),
        ("a desk with no post folder", {}, None, ["F01"]),
    ]
    for i, (label, posts, cfg, want) in enumerate(planted):
        d = _desk(tmp, f"planted{i}", posts, cfg)
        got = codes(d)
        wrote = build(d, out=quiet) != 1 or os.path.exists(os.path.join(d, "desk.html"))
        check(tid(), f"{label} is refused ({want[0]}) and no page is written", got == want and not wrote, f"got {got}, page written: {wrote}")
    link_reply = _desk(tmp, "linkreply", {"2026-11-03-a": {"post.md": "root\n=====\nit is at https://example.org/x and notes.md"}})
    check(tid(), "the same links in a reply are allowed", codes(link_reply) == [], f"got {codes(link_reply)}")

    # T19 which pasted links may become a reply link
    wrong = [(s, want, status_id(s)) for s, want in STATUS_CASES if status_id(s) != want]
    check(tid(), f"post links: {len(STATUS_CASES) - len(wrong)}/{len(STATUS_CASES)} samples read correctly (an id only from a real post link)",
          not wrong, "; ".join(f"{s!r} gave {got!r}, expected {want!r}" for s, want, got in wrong[:3]))

    # T20.. the built page, with text that tries to be markup
    hostile = _desk(tmp, "hostile", {"2026-11-03-a": {"post.md": HOSTILE.split("\n")[0] + "\n=====\n" + HOSTILE.split("\n")[1] + "\n=====\nthird",
                                                      "p.png": _png(), "alt.txt": '"><script>alert(3)</script>'}},
                    {"title": "</title><script>alert(4)</script>", "note": "<img src=https://evil.example/n.png>"})
    rc = build(hostile, out=quiet)
    page = open(os.path.join(hostile, "desk.html"), encoding="utf-8").read() if rc == 0 else ""
    leaks, seen = audit_page(page)
    desk, _, _ = read_desk(hostile)
    parts = desk["posts"][0]["parts"] if desk["posts"] else []
    shown = [seen.pre.get(f"t-2026-11-03-a-{i}") for i in range(len(parts))]
    check(tid(), "text that looks like markup is shown as text: every part reads back from the page exactly as written",
          rc == 0 and len(parts) == 3 and shown == parts, f"build exit {rc}; read back {shown!r:.200}")
    check(tid(), "the hostile desk adds no element: one script, one style, one picture, no handler, no outside reference",
          rc == 0 and leaks == [] and seen.tags.count("script") == 1 and seen.tags.count("img") == 1 and seen.tags.count("a") == 3,
          f"{leaks[:3]} script×{seen.tags.count('script')} img×{seen.tags.count('img')} a×{seen.tags.count('a')}")
    # T22 the links, as strings
    q = lambda url: urllib.parse.parse_qs(urllib.parse.urlsplit(url).query, keep_blank_values=True)
    root_ok = rc == 0 and len(seen.links) == 1 and seen.links[0].startswith(INTENT + "?text=") and q(seen.links[0]) == {"text": [parts[0]]}
    check(tid(), "the root button is X's composer link and its text parameter decodes to the root post, character for character", root_ok,
          f"links in the page: {seen.links!r:.200}")
    tails = re.findall(r'data-tail="([^"]*)"', page)
    reply_ok = (rc == 0 and len(tails) == 2 and seen.reply_links == [None, None] and "in_reply_to" not in page.split("<script>")[0]
                and [q(intent_url("x", "12345") + html.unescape(t).replace("&text=", "&t2=", 1)).get("t2") for t in tails] == [[parts[1]], [parts[2]]])
    check(tid(), "a reply button has no link in the page as built: it gets one only from a pasted post link, and then carries the reply's exact text",
          reply_ok and json.dumps(STATUS_PATTERN) in page, f"tails: {len(tails)}")
    sample = intent_url("a&b #c +d\n\u4f60 100%", "1234567890")
    refused = False
    try:
        intent_url("x", "12345&text=evil")
    except ValueError:
        refused = True
    check(tid(), "a composer link round-trips &, #, +, %, a line break and wide characters, and refuses a reply id that is not digits",
          sample.startswith(INTENT + "?in_reply_to=1234567890&text=") and q(sample) == {"in_reply_to": ["1234567890"], "text": ["a&b #c +d\n\u4f60 100%"]} and refused)

    # T25.. no request to another host
    check(tid(), "the page's Content-Security-Policy allows only its own script and style (by sha256) and embedded pictures",
          rc == 0 and "default-src 'none'; img-src data:; style-src 'sha256-" in seen.csp and "script-src 'sha256-" in seen.csp
          and "unsafe-inline" not in seen.csp and "http" not in seen.csp, seen.csp[:120])
    plants = [('<img src="https://evil.example/p.png">', "img"), ('<link rel="stylesheet" href="https://evil.example/s.css">', "link"),
              ('<script src="//evil.example/s.js"></script>', "script src"), ('<a href="https://evil.example/">x</a>', "a href"),
              ('<p style="background:url(https://evil.example/b.png)">x</p>', "style attribute"), ('<body onload="x()">', "handler"),
              ('<iframe></iframe>', "iframe")]
    blind = [name for snippet, name in plants if rc != 0 or audit_page(page.replace("<footer>", snippet + "<footer>", 1))[0] == []]

    def rewritten(kind, old, new):
        """The page with its own script or style changed and the policy's sha256 changed to match: only reading the text can see it."""
        block = page.split(f"<{kind}>", 1)[1].split(f"</{kind}>", 1)[0] if rc == 0 else ""
        return page.replace(block, block.replace(old, new, 1), 1).replace(_b64hash(block), _b64hash(block.replace(old, new, 1)), 1)
    inside = [(rewritten("script", '"use strict";', '"use strict";fetch("https://evil.example/");'), "a fetch in the page's own script"),
              (rewritten("style", "*{box-sizing:border-box}", "*{box-sizing:border-box}body{background:url(https://evil.example/b.png)}"), "a url() in the page's own style sheet")]
    inside.append((page.replace('"use strict";', '"use strict";var changed=1;', 1), "a script that is not the one the policy names"))
    blind += [name for changed, name in inside if rc != 0 or changed == page or audit_page(changed)[0] == []]
    check(tid(), f"the audit that guards the build sees each of {len(plants) + len(inside)} planted outside references", not blind, f"not seen: {blind}")
    tampered = lambda desk: render(desk).replace("<footer>", '<img src="https://evil.example/pixel.png"><footer>', 1)
    out_file = os.path.join(tmp, "tampered.html")
    check(tid(), "a build whose page would refer to another host is stopped by its own audit, and nothing is written",
          build(clean, out_file, out=quiet, _render=tampered) == 1 and not os.path.exists(out_file) and build(clean, out_file, out=quiet) == 0)
    check(tid(), "the bundled example passes the check, builds, and builds to the same bytes twice", _demo_twice(tmp, quiet))

    # T35.. the root-link refusal can be switched off, says which kind of link it found, and a file name in a reply gets a notice
    both = {"2026-11-03-a": {"post.md": "read it at https://example.org/x and CLAUDE.md\n=====\nreply"}}
    r_def = _desk(tmp, "rl-default", both)
    r_key = _desk(tmp, "rl-key", both, {"allowRootLink": True})
    r_off = _desk(tmp, "rl-off", both, {"allowRootLink": False})
    r_bad = _desk(tmp, "rl-bad", both, {"allowRootLink": "yes"})
    allowed = sorted({c for c, _, _ in read_desk(r_def, allow_root_link=True)[1]})
    check(tid(), "a link in the root post passes when the caller allows it, and is refused (P02) when not",
          allowed == [] and codes(r_def) == ["P02"], f"allowed → {allowed}, default → {codes(r_def)}")
    check(tid(), 'desk.json "allowRootLink": true lets the root carry a link and the page is built; false does not; "yes" is refused (F07)',
          codes(r_key) == [] and build(r_key, out=quiet) == 0 and os.path.exists(os.path.join(r_key, "desk.html"))
          and codes(r_off) == ["P02"] and codes(r_bad) == ["F07", "P02"],
          f"true → {codes(r_key)}, false → {codes(r_off)}, \"yes\" → {codes(r_bad)}")
    p02 = lambda text: [m for c, _, m in read_desk(_desk(tmp, f"msg{len(os.listdir(tmp))}", {"2026-11-03-a": {"post.md": text}}))[1] if c == "P02"]
    m_typed, m_bare, m_both = p02("read https://example.org/x"), p02("read CLAUDE.md first"), p02("read https://example.org/x and CLAUDE.md")
    opt_out = lambda m: "--allow-root-link" in m and '"allowRootLink": true' in m
    check(tid(), "P02 calls a typed link a link and a file name something X turns into a link: two messages, each naming the way to allow it",
          len(m_typed) == 1 and m_typed[0].startswith("the root post carries a link ('https://example.org/x')") and "X turns" not in m_typed[0]
          and len(m_bare) == 1 and m_bare[0].startswith("X turns 'CLAUDE.md' into a link") and "carries a link" not in m_bare[0]
          and len(m_both) == 2 and all(opt_out(m) for m in m_typed + m_bare + m_both), f"{m_typed!r:.120} | {m_bare!r:.120} | {len(m_both)} messages")
    noticed = _desk(tmp, "noticed", {"2026-11-03-a": {"post.md": "the root\n=====\nsee notes.md and main.py, also https://example.org/notes.md, "
                                                                 "example.org/readme.md, example.org and report.html"}})
    _, n_problems, n_notes = read_desk(noticed)
    _, a_problems, a_notes = read_desk(_desk(tmp, "noticed-root", {"2026-11-03-a": {"post.md": "read CLAUDE.md first"}}), allow_root_link=True)
    check(tid(), "a file name in a reply that X will link (notes.md, main.py) gets a notice, not a refusal; a typed link, a link with a path, "
                 "a domain and report.html get none",
          n_problems == [] and len(n_notes) == 2 and all("post.md reply 1: X turns" in n for n in n_notes) and "'notes.md'" in n_notes[0]
          and "'main.py'" in n_notes[1] and build(noticed, check_only=True, out=quiet) == 0 and FILE_ENDINGS <= X_TLDS
          and a_problems == [] and len(a_notes) == 1 and "post.md root: X turns 'CLAUDE.md'" in a_notes[0] and read_desk(r_def)[2] == [],
          f"problems {[c for c, _, _ in n_problems]}, notices {n_notes!r:.200}, allowed root {a_notes!r:.120}")
    check(tid(), "the command line: --check refuses the root link (exit 1), --check --allow-root-link passes (0), an unknown flag is a usage error (2)",
          main([r_def, "--check"], out=quiet) == 1 and main([r_def, "--check", "--allow-root-link"], out=quiet) == 0
          and main([r_def, "--allow-root"], out=quiet) == 2 and main([r_def, "--check", "--out", "x.html"], out=quiet) == 2)
    quiet.close()
    shutil.rmtree(tmp, ignore_errors=True)
    passed = sum(results)
    print(f"build_desk selftest · {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


def _demo_twice(tmp, quiet):
    a, b = os.path.join(tmp, "demo-a.html"), os.path.join(tmp, "demo-b.html")
    if build(EXAMPLE, a, out=quiet) != 0 or build(EXAMPLE, b, out=quiet) != 0:
        return False
    one, two = open(a, "rb").read(), open(b, "rb").read()
    return one == two and audit_page(one.decode("utf-8"))[0] == [] and read_desk(EXAMPLE)[1] == []


def main(argv, out=sys.stdout):
    if argv == ["--selftest"]:
        return selftest()
    if argv[:1] == ["--count"] and len(argv) == 2:
        text = sys.stdin.read() if argv[1] == "-" else argv[1]
        n = x_len(text.strip("\n"))
        print(f"{n} / {LIMIT}" + ("" if n <= LIMIT else f" ({n - LIMIT} over)"))
        return 0 if n <= LIMIT else 1
    out_path = None
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 >= len(argv):
            print(__doc__, file=out); return 2
        out_path = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if argv == ["--demo"]:
        return build(EXAMPLE, out_path or "demo-desk.html")
    flags = [a for a in argv if a.startswith("--")]
    rest = [a for a in argv if not a.startswith("--")]
    if len(rest) != 1 or any(f not in ("--check", "--allow-root-link") for f in flags) or ("--check" in flags and out_path):
        print(__doc__, file=out); return 2
    return build(rest[0], out_path, check_only="--check" in flags, out=out, allow_root_link="--allow-root-link" in flags)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
