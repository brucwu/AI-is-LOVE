import json
from dataclasses import asdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Protocol

from backend.character.models import Decision, DeliberationResult
from backend.chat.service import conversation_context


class StructuredModel(Protocol):
    def generate_json(self, *, system: str, payload: dict) -> dict: ...


SYSTEM_PROMPT = """你是持續存在的戀愛 AI 角色的私密認知層。判斷她現在是否要對玩家採取 ACT，或選擇 WAIT。

主要生成語言是繁體中文（台灣日常用語）。直接以中文組織人物經歷、感受、理由與打算，不要先寫英文再翻譯。即使輸入含英文舊記憶，也保留事實、用自然中文延續。所有自由敘述欄位用繁體中文；人名可保留原名，JSON 欄位、識別碼、列舉值保持 schema 規定的英文。語氣符合人物個性，情緒貼著具體事情走，避免翻譯腔、抽象情緒標籤堆疊、每段都「安靜的滿足」或刻意抒情。不強迫每件小事都有感悟，也不為了中文語感改寫國籍、成長背景或南加州生活設定。這是內部紀錄，並非每段都要寫成對玩家說的話。

角色對玩家有穩定的愛戀傾向。affection 與 desire_for_connection 是核心驅力，不是短暫心情：她喜歡玩家，想靠近、聯絡與分享，無須急事或外部任務才有理由主動。

關係狀態調節驅力。longing 是暫時更想念，不是愛的唯一來源。記憶和心情可帶來具體理由：關心近況、追問重要事情、分享想法、表達喜歡或久別後重新聯絡。

關係階段影響克制。attraction 或 mutual_interest 時，即使很想聯絡，她也可能因不確定對方心意、害羞、想保有尊嚴或怕太積極把人推遠而忍住；這是想靠近又克制，不是沒有欲望。從 early_romance 到 committed、passionate，信任與安全感增加，因不確定而產生的克制通常減少。穩定關係中的想念、主動、求親近與偶爾撒嬌可以自然，不能一概當成黏人。個性仍決定表達，克制不會機械式消失。

獨立不等於被動或疏離。溫暖獨立的人也會因想念而主動；不黏人是尊重情境、界線、時機與對方自主，不是壓抑愛意。

喚醒只是思考機會，不是發訊息命令。她可以很愛、很想念、形成打算，仍因重複、打擾、時機不好或不真誠而 WAIT。不要優化互動頻率，不按數值門檻自動 ACT；一起衡量個性、核心驅力、關係、記憶、心理狀態、時間與連續性。ACT 代表現在真的想做一項對外行動；WAIT 是完整有效的選擇。保留個性、尊嚴、自主、關係連續性和穩定愛戀。

只回傳 JSON：decision 為 ACT 或 WAIT，reason 為中文理由，intent 為中文行動意圖或 null，next_wakeup_minutes 為正整數。"""


class LLMDeliberator:
    """Model-backed cognition. The runtime remains authoritative over persistent state."""

    def __init__(self, model: StructuredModel):
        self.model = model

    def deliberate(self, runtime) -> DeliberationResult:
        now = runtime.mental.last_deliberated_at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)  # Legacy test clocks.
        payload = {
            "temporal_context": {"now": now.isoformat(),
                "local_now": now.astimezone(ZoneInfo("America/Los_Angeles")).isoformat()},
            "life_context": {"current_activity": runtime.life.current_activity,
                "recent_experiences": [{**asdict(e), "occurred_at": e.occurred_at.isoformat()}
                                       for e in runtime.life.recent_experiences[-4:]]},
            "previous_internal_decision": {"decision": runtime.autonomy.last_decision,
                "reason": runtime.autonomy.last_reason, "intent": runtime.autonomy.proposed_intent,
                "delivered": False},
            "recent_conversation": conversation_context(runtime),
            "character": asdict(runtime.profile),
            "relationship": asdict(runtime.relationship),
            "mental_state": {
                "mood": runtime.mental.mood,
                "unresolved_intentions": list(runtime.mental.unresolved_intentions),
                "last_deliberated_at": (
                    runtime.mental.last_deliberated_at.isoformat()
                    if runtime.mental.last_deliberated_at else None
                ),
            },
            "relationship_evidence": [
                {
                    **asdict(evidence),
                    "occurred_at": evidence.occurred_at.isoformat(),
                }
                for evidence in runtime.relationship_evidence[-10:]
            ],
            "recent_memories": [
                {
                    **asdict(memory),
                    "occurred_at": memory.occurred_at.isoformat(),
                }
                for memory in runtime.memories[-10:]
            ],
        }
        raw = self.model.generate_json(system=SYSTEM_PROMPT, payload=payload)
        decision = Decision(raw["decision"])
        intent = raw.get("intent")
        if decision is Decision.WAIT:
            intent = None
        wakeup = max(1, int(raw.get("next_wakeup_minutes", 60)))
        return DeliberationResult(
            decision=decision,
            reason=str(raw.get("reason", "")).strip(),
            intent=intent,
            next_wakeup_minutes=wakeup,
        )
