"""Predefined repair templates and inspection checklists (Arabic labels, keyed by category)."""

REPAIR_TEMPLATES: dict[str, list[str]] = {
    "brakes": ["تغيير فحمات فرامل أمامية", "تغيير فحمات فرامل خلفية", "تغيير ديسكات الفرامل",
               "تغيير زيت الفرامل", "فحص نظام الفرامل", "إصلاح فرامل آخر"],
    "oil": ["تغيير زيت المحرك والفلتر", "تغيير فلتر الهواء", "تغيير فلتر البنزين", "تغيير زيت الفتيس"],
    "engine": ["فحص كمبيوتر", "تغيير شمعات الاحتراق", "تغيير سير التوقيت", "إصلاح تسريب زيت", "إصلاح موتور"],
    "ac": ["شحن فريون", "تغيير كمبروسر التكييف", "تغيير فلتر المكيف", "فحص تسريب التكييف"],
    "electrical": ["فحص كهرباء", "تغيير دينامو", "تغيير مارش", "إصلاح إضاءة"],
    "battery": ["فحص وشحن بطارية", "تغيير بطارية"],
    "tires": ["تغيير كفرات", "ترصيص وميزان", "إصلاح بنشر", "ضبط زوايا"],
    "suspension": ["تغيير مساعدين", "تغيير مقصات", "تغيير جلب وجوانات", "فحص مقدمة"],
    "transmission": ["صيانة فتيس", "تغيير دبرياج", "فحص فتيس"],
    "cooling": ["تغيير رادياتير", "تغيير طلمبة مياه", "تغيير ترموستات", "غسيل دورة التبريد"],
    "steering": ["إصلاح دركسيون", "تغيير ذراع دركسيون", "فحص دركسيون"],
    "exhaust": ["إصلاح شكمان", "تغيير كاتم صوت"],
    "body": ["سمكرة", "دهان", "تلميع"],
    "inspection": ["فحص عام شامل", "فحص قبل السفر", "فحص قبل الشراء"],
}

INSPECTION_TEMPLATES: dict[str, list[str]] = {
    "engine": ["صوت المحرك", "تسريب زيت", "حالة السيور", "دخان العادم"],
    "brakes": ["فحمات أمامية", "فحمات خلفية", "ديسكات", "زيت الفرامل", "فرامل اليد"],
    "transmission": ["تعشيق الغيارات", "تسريب زيت الفتيس", "الدبرياج"],
    "suspension": ["مساعدين أمامية", "مساعدين خلفية", "جلب ومقصات"],
    "steering": ["خلوص الدركسيون", "ذراع الدركسيون", "زيت الباور"],
    "cooling": ["مستوى المياه", "الرادياتير", "الخراطيم", "مروحة التبريد"],
    "ac": ["برودة التكييف", "الكمبروسر", "فلتر المكيف"],
    "electrical": ["الإنارة الأمامية", "الإنارة الخلفية", "لمبات التابلوه", "الدينامو والمارش"],
    "battery": ["جهد البطارية", "أقطاب البطارية"],
    "tires": ["كفر أمامي يمين", "كفر أمامي شمال", "كفر خلفي يمين", "كفر خلفي شمال", "الاستبن"],
    "fluids": ["زيت المحرك", "مياه الراديتير", "زيت الفرامل", "مياه المساحات"],
    "lights": ["كشافات", "إشارات", "فرامل خلفية", "رجوع"],
    "exhaust": ["الشكمان", "كاتم الصوت", "الكاتلايزر"],
    "safety": ["الأحزمة", "الإسعافات", "طفاية الحريق", "مثلث التحذير"],
}

CONDITION_POINTS = ["front_bumper", "rear_bumper", "left_side", "right_side", "windshield", "headlights",
                    "taillights", "tires", "interior", "dashboard", "scratches_dents"]
DASHBOARD_LIGHTS = ["tire_pressure", "traction", "abs", "check_engine", "airbag", "oil_pressure", "battery", "brake", "temperature"]
FUEL_LEVELS = ["empty", "quarter", "half", "three_quarters", "full"]

STATUSES = ["received", "inspection_pending", "under_inspection", "waiting_quotation", "waiting_approval",
            "waiting_parts", "in_progress", "quality_check", "ready", "delivered", "cancelled"]
CLOSED = {"delivered", "cancelled"}


# Recommended service intervals (months, km) used to auto-create reminders when a job is delivered.
SERVICE_INTERVALS: dict[str, tuple[int, int, str]] = {
    "oil": (6, 5000, "تغيير زيت المحرك"),
    "brakes": (12, 20000, "فحص الفرامل"),
    "tires": (12, 10000, "ترصيص وفحص الكفرات"),
    "battery": (24, 0, "فحص البطارية"),
    "ac": (12, 0, "صيانة التكييف"),
    "cooling": (24, 40000, "فحص دورة التبريد"),
    "transmission": (24, 40000, "صيانة الفتيس"),
}
