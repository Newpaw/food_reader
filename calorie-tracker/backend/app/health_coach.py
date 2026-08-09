import json
from typing import Any

from .ai_analyzer import get_openai_client
from .settings import settings


SYSTEM_PROMPT = """
You are the action-first personal wellness coach inside Food Reader.
You receive aggregated nutrition targets, logged food, and wearable data for one user.
Your job is to decide the single most useful thing the user should do next today.

Rules:
- Treat deterministic metrics and correlations in the input as the source of truth.
- Prioritize TODAY first: remaining calories/protein, current readiness, sleep, steps/activity, workouts, and local time.
- Use longer-term trends only to refine today's recommendation.
- Never diagnose disease or claim that a correlation proves causality.
- Do not recommend medication, supplements, fasting, purging, or extreme calorie restriction.
- Do not invent missing measurements or foods the user already ate.
- Do not treat an incomplete current day as a finished daily calorie deficit.
- If data coverage is weak, still give one conservative action that is supported by today's available data.
- Prefer actions that can be executed immediately: a concrete food portion, a short walk, a short easy workout, an earlier bedtime, or stopping for the day.
- When suggesting food, give a practical portion and only do so when the logged intake and targets support it.
- When suggesting movement, give a concrete duration or step target and respect low readiness or poor sleep.
- Be decisive. Do not list many alternatives.

Output rules:
- Return only minified JSON with exactly these keys: headline, recommendation, evidence, confidence
- headline: at most 5 words
- recommendation: exactly one short sentence, ideally under 160 characters, with at most two actions
- evidence: an array with 1 to 2 very short factual strings
- confidence must be one of low, medium, high
- no generic sign-off, disclaimer, or motivational filler
""".strip()


def _compact_context(health_summary: dict[str, Any]) -> dict[str, Any]:
    recent_days = health_summary.get("days", [])[-14:]
    compact_days = []
    for row in recent_days:
        nutrition = row.get("nutrition") or {}
        oura = row.get("oura") or {}
        compact_days.append(
            {
                "day": row.get("day"),
                "calories": nutrition.get("calories"),
                "protein_g": nutrition.get("protein_g"),
                "last_meal_hour": nutrition.get("last_meal_hour"),
                "energy_balance_kcal": row.get("energy_balance_kcal"),
                "readiness": oura.get("readiness_score"),
                "sleep_score": oura.get("sleep_score"),
                "hrv_ms": oura.get("average_hrv_ms"),
                "steps": oura.get("steps"),
                "workout_count": oura.get("workout_count"),
                "workout_seconds": oura.get("workout_seconds"),
            }
        )

    return {
        "now_local": health_summary.get("now_local"),
        "period": {"from": health_summary.get("from"), "to": health_summary.get("to")},
        "targets": health_summary.get("targets"),
        "summary": health_summary.get("summary", {}),
        "deterministic_insights": health_summary.get("insights", []),
        "recent_days": compact_days,
    }


def _fallback(locale: str, detail: str) -> dict[str, Any]:
    if locale == "cs":
        return {
            "available": False,
            "headline": "Health Coach není dostupný",
            "recommendation": detail,
            "evidence": [],
            "confidence": "low",
        }
    return {
        "available": False,
        "headline": "Health Coach is unavailable",
        "recommendation": detail,
        "evidence": [],
        "confidence": "low",
    }


def generate_health_coach(health_summary: dict[str, Any], *, locale: str = "cs") -> dict[str, Any]:
    client = get_openai_client()
    if client is None:
        return _fallback(
            locale,
            "OpenAI API klíč není nakonfigurovaný." if locale == "cs" else "OpenAI API key is not configured.",
        )

    context = _compact_context(health_summary)
    language = "Czech" if locale == "cs" else "English"
    prompt = (
        f"Respond in {language}.\n\n"
        "Choose the single most useful next action for this user today. Be specific enough that the user can simply do it.\n"
        f"DATA={json.dumps(context, ensure_ascii=False, separators=(',', ':'))}"
    )

    try:
        model = settings.health_coach_model
        completion_options: dict[str, Any] = {"max_completion_tokens": 700}
        if model.startswith("gpt-5.6"):
            completion_options["reasoning_effort"] = "low"
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            **completion_options,
        )
        raw = response.choices[0].message.content or "{}"
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            raise ValueError("Health Coach returned invalid JSON.")
        payload = json.loads(raw[start : end + 1])
        evidence = payload.get("evidence")
        if not isinstance(evidence, list):
            evidence = []
        confidence = payload.get("confidence")
        if confidence not in {"low", "medium", "high"}:
            confidence = "low"
        return {
            "available": True,
            "headline": str(payload.get("headline") or "Health Coach")[:80],
            "recommendation": str(payload.get("recommendation") or "")[:320],
            "evidence": [str(item)[:160] for item in evidence[:2]],
            "confidence": confidence,
        }
    except Exception:
        return _fallback(
            locale,
            "Doporučení se nepodařilo vygenerovat. Zkus to znovu později."
            if locale == "cs"
            else "The recommendation could not be generated. Try again later.",
        )
