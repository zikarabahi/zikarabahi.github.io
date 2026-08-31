#!/usr/bin/env python3
"""
محرك المحتوى — نقطة البداية.

الاستخدام:
  python engine/main.py            # يولّد المقال التالي (LLM أو وضع العرض) ويعيد بناء الموقع
  python engine/main.py --demo     # وضع العرض قسريًا (بدون مفتاح API)
  python engine/main.py --auto     # وضع الـ workflow: يتخطى التوليد بدل وضع العرض إن لم يوجد مفتاح
  python engine/main.py --limit 3  # عدد المقالات في هذه الدورة
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate  # noqa: E402
import publish  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env_file():
    """تحميل .env محليًا إن وُجد (لا حاجة له على GitHub)."""
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    for line in open(env_path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def load_cfg():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def load_topics():
    path = os.path.join(ROOT, "topics.txt")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def load_processed():
    path = os.path.join(ROOT, "data", "processed.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_processed(proc):
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "processed.json"), "w", encoding="utf-8") as f:
        json.dump(sorted(proc), f, ensure_ascii=False, indent=2)


def slug_for(topic):
    ascii_part = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    if len(ascii_part) >= 4:
        return ascii_part[:60]
    h = hashlib.md5(topic.encode("utf-8")).hexdigest()[:8]
    return f"article-{h}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="وضع العرض قسريًا (بدون API)")
    ap.add_argument("--auto", action="store_true", help="وضع الـ workflow: بدون وضع عرض")
    ap.add_argument("--limit", type=int, default=None, help="عدد المقالات هذه الدورة")
    ap.add_argument("--rebuild", action="store_true", help="إعادة بناء الموقع فقط دون توليد")
    args = ap.parse_args()

    load_env_file()
    cfg = load_cfg()

    if args.rebuild:
        count = publish.build_site(ROOT, cfg)
        print(f"🔁 أُعيد بناء الموقع ({count} مقالًا) في public/")
        return

    topics = load_topics()
    processed = load_processed()
    pending = [t for t in topics if t not in processed]

    if not pending:
        print("✅ لا توجد مواضيع جديدة. أضف المزيد إلى topics.txt")
    else:
        limit = args.limit or cfg.get("articles_per_run", 1)
        pending = pending[:limit]
        today = datetime.date.today().isoformat()
        made = 0

        for topic in pending:
            print(f"\n▶ الموضوع: {topic}")
            md = generate.generate(
                topic, cfg, today=today, allow_demo=not args.auto
            )
            if not md:
                print("  ⏭️ تم تخطي هذا الموضوع.")
                continue

            slug = publish.slug_from_md(md) or slug_for(topic)
            slug = re.sub(r"[^a-z0-9-]", "-", slug).strip("-") or slug_for(topic)
            base_slug, n = slug, 1
            while os.path.exists(os.path.join(ROOT, "content", slug + ".md")):
                n += 1
                slug = f"{base_slug}-{n}"
            path = os.path.join(ROOT, "content", slug + ".md")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)

            processed.add(topic)
            save_processed(processed)
            made += 1
            print(f"  ✅ حُفظ: content/{slug}.md")

        print(f"\n🎉 اكتمل: {made} مقالًا جديدًا.")

        if args.auto and made == 0:
            print("\n❌ لم يُنشر أي مقال هذه الدورة (فشلت محاولات الكتابة) — ستُعاد في الدورة القادمة.")
            sys.exit(1)

    count = publish.build_site(ROOT, cfg)
    print(f"🌐 أُعيد بناء الموقع ({count} مقالًا) في public/")


if __name__ == "__main__":
    main()
