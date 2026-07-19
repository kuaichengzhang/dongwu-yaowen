#!/usr/bin/env python3
# 动物要闻 · 静态站生成器
# 用法：python3 build.py  （读取 data/issues.json，生成 index.html 与 issue/NNN.html）
import json, os, html, re

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(ROOT, "data", "issues.json"), encoding="utf-8"))
ISSUES = sorted(DATA["issues"], key=lambda x: x["no"])
POOL = DATA["pool"]

DEFAULT_ACCENT = "#2E7D46"

def esc(s):
    return html.escape(s, quote=False)

def accent_for(issue):
    if issue.get("accent"):
        return issue["accent"]
    # 从封面/首图提取一个饱和中等明度的颜色
    try:
        from PIL import Image
        import colorsys
        img = None
        if issue.get("cover"):
            img = issue["cover"]["src"]
        elif issue.get("photos"):
            img = issue["photos"][0]["src"]
        elif issue.get("grid"):
            img = issue["grid"][0]
        if not img:
            return DEFAULT_ACCENT
        im = Image.open(os.path.join(ROOT, img)).convert("RGB").resize((80, 80))
        q = im.quantize(colors=6).convert("RGB")
        best, best_score = None, -1
        for n, c in q.getcolors(10000):
            r, g, b = [v / 255 for v in c]
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            score = s * (1 - abs(v - 0.5) * 1.2)
            if score > best_score:
                best, best_score = c, score
        r, g, b = [int(v * 0.72) for v in best]  # 压暗保证白底可读
        return "#%02x%02x%02x" % (r, g, b)
    except Exception:
        return DEFAULT_ACCENT

ACCENTS = {i["slug"]: accent_for(i) for i in ISSUES}

def chrome(title, body, prefix=""):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{prefix}styles.css">
</head>
<body>
<div class="page">
  <header class="masthead">
    <a class="brand" href="{prefix}index.html">动物要闻</a>
    <nav class="nav">
      <span class="tagline">每天一条动物新闻</span>
      <a href="{prefix}index.html#past">往日</a>
      <a href="{prefix}index.html#pool">编辑部在看</a>
    </nav>
  </header>
{body}
  <footer class="colophon">
    <p class="empty-day">没有合格选题的日子，这里会写：今日无要闻，动物们都挺好的。</p>
    <p>动物要闻 · 创刊于 2015 · 每天一条动物新闻</p>
    <p class="creed">无一条惨剧 · 每条有主角 · 来源透明</p>
  </footer>
</div>
</body>
</html>
"""

def meta_line(issue, accent):
    parts = [f'<i class="dot" style="background:{accent}"></i>',
             f'<span class="no">第 {issue["no"]:03d} 期</span>']
    date = issue["date"] + (" · " + issue["weekday"] if issue.get("weekday") else "")
    parts += ['<span class="sep">·</span>', f'<span>{esc(date)}</span>',
              '<span class="sep">·</span>', f'<span>{esc(issue["cat"])}</span>']
    return '<div class="issue-meta">' + "\n        ".join(parts) + "</div>"

def figure_html(src, cap, prefix, cls="cover", alt=""):
    cap_html = f"<figcaption>{esc(cap)}</figcaption>" if cap else ""
    return f'<figure class="{cls}"><img src="{prefix}{esc(src)}" alt="{esc(alt or cap)}">{cap_html}</figure>'

def beats_html(beats, prefix):
    out = ['<section class="beats">']
    for b in beats:
        out.append(f'''<div class="beat">
          <div class="beat-no">{esc(b["no"])}</div>
          <img src="{prefix}{esc(b["img"])}" alt="{esc(b.get("alt",""))}">
          <p class="beat-cap">{esc(b["cap"])}</p>
        </div>''')
    out.append("</section>")
    return "\n      ".join(out)

def entries_html(entries):
    out = ['<div class="entries">']
    for e in entries:
        stats = f'<div class="entry-stats">{esc(e["stats"])}</div>' if e.get("stats") else ""
        out.append(f'''<div class="entry">
          <div class="entry-name">{esc(e["name"])}</div>
          {stats}
          <p class="entry-quip">{esc(e["quip"])}</p>
        </div>''')
    out.append("</div>")
    return "\n      ".join(out)

def issue_body(issue, prefix, accent):
    a = [f'<article class="issue" style="--accent:{accent}">',
         f'<a class="back-top" href="{prefix}index.html">← 回到首页</a>',
         meta_line(issue, accent)]
    a.append(f'<h1 class="headline">{issue["title"]}</h1>')
    if issue.get("standfirst"):
        a.append(f'<p class="standfirst">{esc(issue["standfirst"])}</p>')
    if issue.get("cover"):
        a.append(figure_html(issue["cover"]["src"], issue["cover"].get("cap", ""), prefix, "cover", issue["cover"].get("alt", "")))
    if issue.get("body"):
        paras = "\n        ".join(f"<p>{esc(p)}</p>" for p in issue["body"])
        a.append(f'<div class="body">{paras}</div>')
    if issue.get("entries"):
        a.append(entries_html(issue["entries"]))
    if issue.get("photos"):
        a.append('<section class="photos">')
        for p in issue["photos"]:
            a.append(figure_html(p["src"], p.get("cap", ""), prefix, "inbody"))
        a.append("</section>")
    if issue.get("grid"):
        imgs = "\n        ".join(f'<img src="{prefix}{esc(g)}" alt="罕见动物图鉴" loading="lazy">' for g in issue["grid"])
        a.append(f'<section class="photo-grid">{imgs}</section>')
    if issue.get("beats"):
        a.append(beats_html(issue["beats"], prefix))
    if issue.get("postscript"):
        a.append(f'<aside class="postscript"><p>{esc(issue["postscript"])}</p></aside>')
    if issue.get("source"):
        a.append(f'<div class="source-line">{esc(issue["source"])}</div>')
    a.append("</article>")
    return "\n      ".join(a)

def issue_nav(issue, prefix):
    prev_i = next((x for x in ISSUES if x["no"] == issue["no"] - 1), None)
    next_i = next((x for x in ISSUES if x["no"] == issue["no"] + 1), None)
    parts = ['<nav class="issue-nav">']
    if prev_i:
        t = re.sub(r"<br\s*/?>", " ", prev_i["title"])
        parts.append(f'<a class="prev" href="{prev_i["slug"]}.html">← 第 {prev_i["no"]:03d} 期<span>{esc(t)}</span></a>')
    else:
        parts.append("<span></span>")
    parts.append(f'<a class="home" href="{prefix}index.html">首页</a>')
    if next_i:
        t = re.sub(r"<br\s*/?>", " ", next_i["title"])
        parts.append(f'<a class="next" href="{next_i["slug"]}.html">第 {next_i["no"]:03d} 期 →<span>{esc(t)}</span></a>')
    else:
        parts.append("<span></span>")
    parts.append("</nav>")
    return "\n      ".join(parts)

def build_issue_pages():
    os.makedirs(os.path.join(ROOT, "issue"), exist_ok=True)
    for issue in ISSUES:
        accent = ACCENTS[issue["slug"]]
        body = "      " + issue_body(issue, "../", accent) + "\n      " + issue_nav(issue, "../")
        plain = issue.get("title_plain") or re.sub(r"<br\s*/?>", " ", issue["title"])
        page = chrome(f"{plain} · 动物要闻 第{issue['no']:03d}期", body, "../")
        open(os.path.join(ROOT, "issue", f"{issue['slug']}.html"), "w", encoding="utf-8").write(page)

def past_row(issue):
    thumb_path = os.path.join(ROOT, "img", "thumbs", f"{issue['slug']}.jpg")
    if os.path.exists(thumb_path):
        thumb = f'<img class="past-thumb" src="img/thumbs/{issue["slug"]}.jpg" alt="">'
    else:
        thumb = '<span class="past-thumb past-thumb-empty">无图</span>'
    t = re.sub(r"<br\s*/?>", " ", issue["title"])
    return f'''<li class="past-row">
          <a class="past-link" href="issue/{issue["slug"]}.html">{thumb}
          <span class="past-title">{esc(t)}</span>
          <span class="past-meta"><span class="no">第 {issue["no"]:03d} 期</span>{esc(issue["cat"])} · {esc(issue["date"])}</span></a>
        </li>'''

def build_index():
    latest = ISSUES[-1]
    accent = ACCENTS[latest["slug"]]
    parts = ["  <!-- 今日这一期 -->\n  <main>",
             "      " + issue_body(latest, "", accent)]
    past = "\n        ".join(past_row(i) for i in reversed(ISSUES[:-1]))
    parts.append(f'''    <!-- 往日 -->
    <section class="past" id="past">
      <div class="section-head">
        <h2>往日</h2>
        <p class="section-note">本报 2015 年创刊，休刊十年，今夏复刊。以下是创刊初期的全部 {len(ISSUES)-1} 期。</p>
      </div>
      <ul class="past-list">
        {past}
      </ul>
    </section>''')
    pool_rows = "\n        ".join(
        f'<li class="pool-row"><i class="st st-{p["status"]}"></i><span class="pool-title">{esc(p["title"])}</span><span class="pool-meta">{esc(p["meta"])}</span></li>'
        for p in POOL)
    parts.append(f'''    <!-- 编辑部在看 -->
    <section class="pool" id="pool">
      <div class="section-head">
        <h2>编辑部在看</h2>
        <p class="section-note">每天巡逻信源得到的候选都列在这里。发哪一条，主编说了算。</p>
        <div class="legend">
          <span><i class="st st-open"></i>待选</span>
          <span><i class="st st-half"></i>编译中</span>
          <span><i class="st st-full"></i>已排期</span>
        </div>
      </div>
      <ul class="pool-list">
        {pool_rows}
      </ul>
    </section>
  </main>''')
    page = chrome("动物要闻 · 每天一条动物新闻", "\n".join(parts))
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(page)

if __name__ == "__main__":
    build_issue_pages()
    build_index()
    print(f"ok: index + {len(ISSUES)} issue pages")
    for i in ISSUES:
        print(f"  第{i['no']:03d}期 accent={ACCENTS[i['slug']]}")
