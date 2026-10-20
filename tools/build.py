"""把 src/survey-cases.html 打包成離線單檔版，並產生可散佈的 zip。

用法：python3 tools/build.py            （內建 data/seed.json 的資料）
      python3 tools/build.py --no-seed  （第一次開啟為空白）
"""
import json, pathlib, re, sys, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "survey-cases.html"
LIB = ROOT / "vendor" / "xlsx.full.min.js"
SEED = ROOT / "data" / "seed.json"
OUT_DIR = ROOT / "dist" / "測量案件排程"
OUT = OUT_DIR / "測量案件排程.html"
GUIDE = ROOT / "dist" / "使用說明.txt"
ZIP = ROOT / "dist" / "測量案件排程.zip"
# 發佈給離線版「檢查更新」用：程式讀 release/version.json，下載 release/survey-schedule.zip
RELEASE = ROOT / "release"
REPO_RAW = "https://github.com/gn01918004-hub/work-paper/raw/main/release/survey-schedule.zip"

CDN_TAG = '<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>'


def build(seed: bool) -> None:
    html = SRC.read_text(encoding="utf-8")
    assert CDN_TAG in html and 'const BUILD = "artifact";' in html and "const SEED = null;" in html
    # 內嵌 Excel 元件，離線也能匯入／匯出
    html = html.replace(CDN_TAG, "<script>" + LIB.read_text(encoding="utf-8").replace("</script", "<\\/script") + "</script>")
    html = html.replace('const BUILD = "artifact";', 'const BUILD = "standalone";')
    if seed:
        html = html.replace("const SEED = null;", "const SEED = " + SEED.read_text(encoding="utf-8").replace("</", "<\\/") + ";")
    html = html.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
    # 線上版由平台補上 <head>；離線版自己補
    title, rest = html.split("\n", 1)
    doc = ('<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
           + title +
           '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
           'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'
           '</head><body>\n' + rest + '\n</body></html>\n')
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    (OUT_DIR / GUIDE.name).write_text(GUIDE.read_text(encoding="utf-8"), encoding="utf-8")
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in (OUT, OUT_DIR / GUIDE.name):
            z.write(f, f"測量案件排程/{f.name}")
    print(f"built {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} bytes), {ZIP.relative_to(ROOT)}")
    if seed:
        release(html)


def latest_entry(html: str) -> dict:
    """從原始碼的 CHANGELOG 陣列取出第一筆（目前版本）。"""
    version = re.search(r'const VERSION = "([\d.]+)";', html).group(1)
    block = re.search(r"const CHANGELOG = \[(.*?)\n\];", html, re.S).group(1)
    first = re.search(r"\{v:\"([\d.]+)\", date:\"([^\"]*)\", title:\"([^\"]*)\", items:\[(.*?)\]\}", block, re.S)
    assert first and first.group(1) == version, "CHANGELOG 第一筆必須是目前版本 VERSION"
    items = re.findall(r'"((?:[^"\\]|\\.)*)"', first.group(4))
    return {"version": version, "date": first.group(2), "title": first.group(3), "items": items}


def release(html: str) -> None:
    RELEASE.mkdir(exist_ok=True)
    info = latest_entry(html)
    info["download"] = REPO_RAW
    (RELEASE / "version.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RELEASE / "survey-schedule.zip").write_bytes(ZIP.read_bytes())
    print(f"release v{info['version']}: release/version.json, release/survey-schedule.zip")


if __name__ == "__main__":
    build(seed="--no-seed" not in sys.argv)
