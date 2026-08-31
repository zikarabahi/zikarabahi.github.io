"""توليد المقالات: حقيقية عبر API ذكاء اصطناعي، أو قالب تجريبي بدون مفتاح."""
import datetime
import hashlib
import json as _json
import os
import re
import time

PROMPT = """أنت كاتب محتوى محترف باللغة العربية تعمل لموقع "{site}" المتخصص في {niche}.
اكتب مقالًا كاملًا حول الموضوع: "{topic}"

ابدأ بـ frontmatter بين سطرَي --- بهذه الصيغة:
---
title: (عنوان جذاب بالعربية، 40 حرفًا كحد أقصى)
slug: (نص لاتيني قصير بدون مسافات، مثال: best-ai-tools-2026)
date: {today}
description: (وصف مختصر من 150 حرفًا كحد أقصى)
---

ثم المقال بصيغة Markdown:
- عنوان H1 مطابق للعنوان
- مقدمة تشد القارئ (2-3 فقرات)
- من 5 إلى 7 عناوين فرعية H2 بمحتوى عملي مفيد
- قوائم منقطة أو مرقمة حيث يناسب
- قسم "الخلاصة" في النهاية
- قسم "الأسئلة الشائعة" بثلاثة أسئلة كعناوين H3
- إذا ذُكرت أدوات، ضع رابط موقعها الرسمي بين قوسين

الطول: 800-1200 كلمة. الأسلوب: واضح وعملي بدون حشو، بصيغة المخاطب.
أخرج النص النهائي فقط، بدون أي شرح أو مقدمات."""


def llm_generate(topic, cfg, today):
    """نداء إلى أي API متوافق مع OpenAI. يعيد نص المقال أو None."""
    key_env = cfg["llm"].get("api_key_env", "OPENAI_API_KEY")
    key = os.environ.get(key_env, "").strip()
    if not key:
        return None
    import requests  # استيراد كسول حتى لا يتأثر وضع العرض

    payload = {
        "model": cfg["llm"].get("model", "gpt-4o-mini"),
        "temperature": 0.7,
        "max_tokens": 8000,
        "messages": [
            {
                "role": "user",
                "content": PROMPT.format(
                    site=cfg["site_name"], niche=cfg["niche"], topic=topic, today=today
                ),
            }
        ],
    }
    base = cfg["llm"].get("api_base", "https://api.openai.com/v1").rstrip("/")
    _size = len(_json.dumps(payload, ensure_ascii=True).encode("utf-8"))
    resp = None
    for attempt in range(6):
        resp = requests.post(
            base + "/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            },
            json=payload,
            timeout=180,
        )
        print(f"    [محاولة {attempt+1}] الحجم={_size} بايت → HTTP {resp.status_code}")
        # 401/404 خطأ حقيقي (مفتاح/نموذج) — لا معنى لإعادة المحاولة
        if resp.status_code in (200, 401, 404):
            break
        if attempt < 5:
            time.sleep(15 * (attempt + 1))  # أخطاء مؤقتة (413/429/5xx) — نعيد بتدرّج حتى ~3 دقائق
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"].strip()
    text = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", text, flags=re.M).strip()
    return text


def demo_generate(topic, cfg, today):
    """مقال تجريبي يعمل بدون مفتاح API — لإثبات أن النظام يعمل كاملًا."""
    h = hashlib.md5(topic.encode("utf-8")).hexdigest()[:8]
    return f"""---
title: {topic}
slug: article-{h}
date: {today}
description: مقال تجريبي من وضع العرض حول: {topic}
---

# {topic}

> **ملاحظة:** هذا مقال تجريبي من "وضع العرض" يعمل بدون مفتاح API. بعد إضافة المفتاح ستُنشر هنا مقالات حقيقية مولّدة بالذكاء الاصطناعي (راجع README.md).

{topic} من الموضوعات التي تشغل اهتمام الكثيرين هذه الأيام، وفي هذا المقال نستعرض أهم ما تحتاج معرفته للبدء.

## لماذا يهمك هذا الموضوع

- يوفّر وقتك في المهام المتكررة
- يساعدك على اتخاذ قرارات أفضل بمعلومات محدثة
- يفتح لك فرص عمل ودخل جديدة

## خطوات عملية للبدء

1. حدّد هدفك بدقة: ماذا تريد أن تحقق بالضبط؟
2. جرب الأداة أو الطريقة الأساسية وقارن البدائل
3. طبّق ما تعلمته في مشروع صغير حقيقي
4. قس النتيجة ثم وسّع تدريجيًا

## الخلاصة

ابدأ صغيرًا، طبّق بواقعية، ثم وسّع. الذكاء الاصطناعي أداة تضخّم قدراتك، وليس بديلًا عن فهمك للأمر.

## الأسئلة الشائعة

### هل أحتاج خبرة سابقة؟
لا، يمكنك البدء من الصفر مع الالتزام بالتدرج.

### ما التكلفة التقريبية؟
تبدأ من الأدوات المجانية، وقد تصل إلى بضع عشرات من الدولارات شهريًا حسب الاستخدام.

### كم من الوقت أحتاج لرؤية النتائج؟
أسابيع قليلة للمهارات الأساسية، وشهر إلى ثلاثة أشهر للنتائج الواضحة.
"""


def generate(topic, cfg, today=None, allow_demo=True):
    today = today or datetime.date.today().isoformat()
    try:
        text = llm_generate(topic, cfg, today)
        if text:
            return text
        if not allow_demo:
            print("  ⚠️ لم يُعثر على مفتاح API — أضفه في GitHub Secrets ثم شغّل مرة أخرى.")
            return None
        print("  ⚠️ لا يوجد مفتاح API → وضع العرض (demo)")
    except Exception as e:
        print(f"  ⚠️ خطأ في API: {e}")
        if not allow_demo:
            return None
        print("  ⚠️ استخدام وضع العرض بدلًا من ذلك")
    return demo_generate(topic, cfg, today)
