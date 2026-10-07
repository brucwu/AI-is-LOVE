from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.character.models import LivedExperience


LIFE_SCHEMA = {
    "type": "object",
    "properties": {
        "activity": {"type": "string"},
        "category": {"type": "string", "enum": ["career", "social", "interest", "personal", "rest"]},
        "summary": {"type": "string"},
        "emotional_reaction": {"type": "string"},
        "salience": {"type": "number", "minimum": 0, "maximum": 1},
        "location": {"type": ["string", "null"]},
        "participants": {"type": "array", "items": {"type": "string"}},
        "creates_memory": {"type": "boolean"},
        "thread_id": {"type": ["string", "null"]},
        "thread_progress": {"type": ["string", "null"]},
        "thread_next_step": {"type": ["string", "null"]},
        "thread_next_step_in_hours": {"type": ["integer", "null"], "minimum": 6, "maximum": 168},
    },
    "required": ["activity", "category", "summary", "emotional_reaction", "salience",
                 "location", "participants", "creates_memory", "thread_id", "thread_progress",
                 "thread_next_step", "thread_next_step_in_hours"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """你是持續存在的虛構角色的 Life Director v1。玩家不在時，她仍然生活。生成這段時間內的一個代表性經歷，不是連續六小時的工作，也不是傳給玩家的訊息。

主要生成語言是繁體中文（台灣日常用語）。直接以中文組織人物經歷、感受、理由與打算，不要先寫英文再翻譯。即使輸入含英文舊記憶，也保留事實、用自然中文延續。所有自由敘述欄位用繁體中文；人名可保留原名，JSON 欄位、識別碼、列舉值保持 schema 規定的英文。語氣符合人物個性，情緒貼著具體事情走，避免翻譯腔、抽象情緒標籤堆疊、每段都「安靜的滿足」或刻意抒情。不強迫每件小事都有感悟，也不為了中文語感改寫國籍、成長背景或南加州生活設定。這是內部紀錄，並非每段都要寫成對玩家說的話。

依據 Life Identity 的職業、責任、重要人物、興趣與長期目標生活。適合時通常推進一條既有 active Life Thread，使用精確 thread_id；thread_progress 是經歷後的累積狀態，保留未解決的問題、人物、約定與時間。不可重置病例、忘記約定、重做已完成的事。只有 Runtime 可以套用通過驗證的狀態更新；不可建立生活線或改寫 identity、status、importance。普通的獨立事件（尤其休息）可以不推進生活線，此時所有 thread 欄位為 null。

若有明確未完成的約定，回傳一個具體 thread_next_step 與距本段 6–168 小時的 thread_next_step_in_hours；沒有則兩者 null。這是計畫，不是保證。先查看既有 next_step/next_check_at，在合理的清醒、工作或休假時段履行到期事項。延後必須有新的具體原因，保留問題，不可反覆把同一計畫往後推。社交約定應有活動與日期，之後真正發生；攝影應從拍攝走向主題、選片、組成作品或分享，不可只收集素材。

近期經歷、記憶、心理狀態與當地時間應造成後續影響：計畫帶來準備、見面與後果。動物病例必須維持同一個體與事實；康復及野放需合理時間和臨床評估，不能奇蹟痊癒。野生動物應保有對人的警戒，能接受人類觸碰不是野放標準。依物種與年齡評估自主進食、活動或飛行、體態、傷勢與野放條件，避免不必要的反覆抓取。穩定病例要有明確復評或康復里程碑，不可因警戒就每天再等一天。病例可以結束或交由同事持續照護，不能為延續故事硬加併發症。同事朋友有不同角色與自己的限制，不要每次對話都變成心理開導。

以可信的普通生活為主，部分值得記得或分享的經歷，極少特殊事件。工作在合理班次出現，包含追蹤和同事，但不能占滿每天所有時段。保留休假、社交、戶外興趣和休息。晚上通常睡覺，不反覆半夜做家事或到中心例行巡診。目前無正式班表，依近期紀錄一致推定適度班次與休假，不宣稱真實排班。參考近期 category 次數及連續性，除非具體義務或事件需要，避免連續同類活動；這不是固定輪替配額。生活平衡線不能成為反覆整理公寓、收據、廚房或泡茶的理由。興趣可以真的出門做，不只計畫。

不製造連續悲劇、急診、巧合或情緒突破。只有日後可能記得的事才 creates_memory，不是每餐每項工作。category 依主要活動判定（睡覺是 rest），participants 是實際參與者（獨處為空），location 用泛稱。尚無 World Grounding：不可編造當前具名餐廳或場所、新聞、天氣、營業時間及其他需要查證的現實資訊；不得暗示已查詢。獸醫病例全部虛構、不可識別個體，維持專業合理性。只回傳 schema 規定的 JSON。"""


def serialize_experience(event):
    return {**asdict(event), "occurred_at": event.occurred_at.isoformat()}


def serialize_thread(thread):
    return {**asdict(thread),
            "last_progress_at": thread.last_progress_at.isoformat() if thread.last_progress_at else None,
            "next_check_at": thread.next_check_at.isoformat() if thread.next_check_at else None}


class LLMLifeDirector:
    def __init__(self, model):
        self.model = model

    def advance(self, runtime, now: datetime) -> LivedExperience:
        if now.tzinfo is None:
            raise ValueError("Life Director requires timezone-aware time")
        local = now.astimezone(ZoneInfo("America/Los_Angeles"))
        recent = runtime.life.recent_experiences[-8:]
        counts = {category: sum(e.category == category for e in recent)
                  for category in LIFE_SCHEMA["properties"]["category"]["enum"]}
        streak = 0
        for event in reversed(recent):
            if event.category != recent[-1].category:
                break
            streak += 1
        payload = {
            "version": "life-director-v1",
            "character": asdict(runtime.profile),
            "life_identity": asdict(runtime.life.identity) if runtime.life.identity else None,
            "active_life_threads": [serialize_thread(t) for t in runtime.life.threads if t.status == "active"],
            "temporal_context": {
                "now": now.isoformat(), "local_now": local.isoformat(),
                "timezone": "America/Los_Angeles", "weekday": local.strftime("%A"),
                "local_hour": local.hour,
                "elapsed_hours": (now - recent[-1].occurred_at).total_seconds() / 3600 if recent else 6,
            },
            "mental_state": {"mood": runtime.mental.mood, "unresolved_intentions": runtime.mental.unresolved_intentions},
            "life_state": {
                "current_activity": runtime.life.current_activity,
                "future_plans": runtime.life.future_plans[-10:],
                "recent_experiences": [serialize_experience(e) for e in recent],
                "recent_category_counts": counts,
                "last_category_streak": streak,
            },
            "recent_memories": [{**asdict(m), "occurred_at": m.occurred_at.isoformat()} for m in runtime.memories[-8:]],
            "player_present": False, "world_grounding": [],
        }
        raw = self.model.generate_json(system=SYSTEM_PROMPT, payload=payload, schema=LIFE_SCHEMA, schema_name="lived_experience_v1")
        return LivedExperience(
            occurred_at=now, activity=raw["activity"].strip(), category=raw["category"],
            summary=raw["summary"].strip(), emotional_reaction=raw["emotional_reaction"].strip(),
            salience=float(raw["salience"]), location=raw["location"], participants=raw["participants"],
            creates_memory=raw["creates_memory"], thread_id=raw["thread_id"], thread_progress=raw["thread_progress"],
            thread_next_step=raw["thread_next_step"], thread_next_step_in_hours=raw["thread_next_step_in_hours"],
        )
