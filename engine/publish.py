"""بناء الموقع الثابت من ملفات Markdown في content/ — النسخة الاحترافية."""
import datetime
import html
import os
import re
import shutil
from urllib.parse import quote

import markdown_lite


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_frontmatter(md):
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", md, flags=re.S)
    if not m:
        return {}, md
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, md[m.end():]


def slug_from_md(md):
    meta, _ = parse_frontmatter(md)
    slug = re.sub(r"[^a-z0-9-]", "-", (meta.get("slug") or "")).strip("-")
    if re.fullmatch(r"[a-z0-9-]+", slug):
        return slug
    ascii_part = re.sub(r"[^a-z0-9]+", "-", (meta.get("title") or "").lower()).strip("-")
    return ascii_part[:60] if ascii_part else None


def first_paragraph(body):
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", ">", "-")):
            return re.sub(r"\*\*|\[|\]\([^)]*\)", "", line)[:160]
    return ""


def ad_slot_html(cfg):
    slot = (cfg.get("adsense_slot") or "").strip()
    if slot:
        return slot
    return (
        '<div class="ad-slot" aria-label="مساحة إعلان">'
        "<span>مساحة إعلان — تُفعَّل تلقائيًا بعد ربط Google AdSense في الإعدادات</span></div>"
    )


def build_site(root, cfg):
    tdir = os.path.join(root, "templates")
    out = os.path.join(root, "public")
    articles_dir = os.path.join(out, "articles")
    os.makedirs(articles_dir, exist_ok=True)
    # تنظيف صفحات المقالات القديمة
    for fn in os.listdir(articles_dir):
        if fn.endswith(".html"):
            os.remove(os.path.join(articles_dir, fn))

    # الأصول
    for fn in ("style.css", "favicon.svg", "og-image.png"):
        src = os.path.join(root, "assets", fn)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(out, fn))

    cdir = os.path.join(root, "content")
    items = []
    for fn in sorted(os.listdir(cdir)):
        if not fn.endswith(".md"):
            continue
        md = _read(os.path.join(cdir, fn))
        meta, body = parse_frontmatter(md)
        title = meta.get("title") or fn[:-3]
        slug = re.sub(r"[^a-z0-9-]", "-", (meta.get("slug") or "")).strip("-") or fn[:-3]
        date = meta.get("date", "2026-01-01")
        desc = meta.get("description") or first_paragraph(body) or title
        content = markdown_lite.md_to_html(body)
        rt = max(1, len(body.split()) // 200)
        items.append(dict(title=title, slug=slug, date=date, desc=desc, content=content, rt=rt))
    items.sort(key=lambda a: a["date"], reverse=True)

    base = cfg.get("base_url", "").rstrip("/")
    ads_client = cfg.get("adsense_client", "")
    site_name = html.escape(cfg["site_name"])
    tagline = html.escape(cfg.get("tagline", ""))
    year = str(datetime.date.today().year)
    og_image = base + "/og-image.png" if os.path.exists(
        os.path.join(root, "assets", "og-image.png")) else ""
    count = len(items)

    def card(a):
        return (
            f'<a class="card" href="__REL__articles/{a["slug"]}.html">\n'
            f'  <h3>{html.escape(a["title"])}</h3>\n'
            f'  <p>{html.escape(a["desc"])}</p>\n'
            f'  <span class="meta">{a["date"]} · {a["rt"]} دقائق قراءة</span>\n'
            f"</a>"
        )

    art_tpl = _read(os.path.join(tdir, "article.html"))
    index_tpl = _read(os.path.join(tdir, "index.html"))

    for a in items:
        content = a["content"]
        ad = ad_slot_html(cfg)
        # إعلان بعد الفقرة الثانية
        first_close = content.find("</p>")
        second_close = content.find("</p>", first_close + 1) if first_close != -1 else -1
        if second_close != -1:
            pos = second_close + 4
            content = content[:pos] + "\n" + ad + "\n" + content[pos:]
        else:
            content = content + "\n" + ad

        related = "\n".join(card(o) for o in [x for x in items if x["slug"] != a["slug"]][:3])
        share_raw = base + f"/articles/{a['slug']}.html"
        page = (
            art_tpl.replace("__SITE_NAME__", site_name)
            .replace("__TAGLINE__", tagline)
            .replace("__TITLE__", html.escape(a["title"]))
            .replace("__DESCRIPTION__", html.escape(a["desc"]))
            .replace("__DATE__", a["date"])
            .replace("__READ_TIME__", str(a["rt"]))
            .replace("__YEAR__", year)
            .replace("__URL__", share_raw)
            .replace("__OG_IMAGE__", og_image)
            .replace("__SHARE_URL__", quote(share_raw, safe=""))
            .replace("__RELATED__", related)
            .replace("__CONTENT__", content)
            .replace("__REL__", "../")
            .replace("__ADSENSE_CLIENT__", ads_client)
        )
        with open(os.path.join(articles_dir, a["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(page)

    index = (
        index_tpl.replace("__SITE_NAME__", site_name)
        .replace("__TAGLINE__", tagline)
        .replace("__YEAR__", year)
        .replace("__URL__", base + "/")
        .replace("__OG_IMAGE__", og_image)
        .replace("__ARTICLE_COUNT__", str(count))
        .replace("__CARDS__", "\n".join(card(a) for a in items))
        .replace("__REL__", "")
        .replace("__ADSENSE_CLIENT__", ads_client)
    )
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(index)

    # الصفحات الثابتة
    sdir = os.path.join(tdir, "static")
    if os.path.isdir(sdir):
        for fn in sorted(os.listdir(sdir)):
            if not fn.endswith(".html"):
                continue
            page = (
                _read(os.path.join(sdir, fn))
                .replace("__SITE_NAME__", site_name)
                .replace("__TAGLINE__", tagline)
                .replace("__YEAR__", year)
                .replace("__EMAIL__", html.escape(cfg.get("contact_email", "")))
                .replace("__ARTICLE_COUNT__", str(count))
                .replace("__DATE__", datetime.date.today().isoformat())
                .replace("__REL__", "")
                .replace("__ADSENSE_CLIENT__", ads_client)
            )
            with open(os.path.join(out, fn), "w", encoding="utf-8") as f:
                f.write(page)

    # sitemap
    urls = [(base + "/", None)]
    urls += [(base + f"/articles/{a['slug']}.html", a["date"]) for a in items]
    urls += [(base + f"/{p}", None) for p in ("about.html", "contact.html", "privacy.html")]
    sm = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u, lm in urls:
        entry = f"<url><loc>{u}</loc>"
        if lm:
            entry += f"<lastmod>{lm}</lastmod>"
        entry += "</url>"
        sm.append(entry)
    sm.append("</urlset>")
    with open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(sm))

    with open(os.path.join(out, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")

    return count
