import json
from typing import Any

from .ai_analyzer import get_openai_client
from .settings import settings


SYSTEM_PROMPT = """
You are the personal wellness coach inside Food Reader.
You receive only aggregated nutrition and wearable data for one user.
Your job is to turn the measured patterns into one short, practical recommendation for today.

Rules:
- Treat deterministic metrics and correlations in the input as the source of truth.
- Never diagnose disease or claim that a correlation proves causality.
- Do not recommend medication, supplements, fasting, purging, or extreme calorie restriction.
- Do not invent missing measurements.
- Prefer trends across multiple days over a single outlier.
- If data coverage is weak, say that explicitly and recommend better logging/sync rather than pretending certainty.
- Keep the advice practical and specific to the supplied data.
- Return only minified JSON with exactly these keys:
  headline, recommendation, evidence, confidence
- confidence must be one of low, medium, high.
- evidence must be an array with 1 to 3 short strings.
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
            }
        )

    return {
        "period": {"from": health_summary.get("from"), "to": health_summary.get("to")},
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
        "Analyze this user's aggregated Food Reader + Oura data and produce the single most useful recommendation for today.\n"
        f"DATA={json.dumps(context, ensure_ascii=False, separators=(',', ':'))}"
    )

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=350,
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
            "headline": str(payload.get("headline") or "Health Coach"),
            "recommendation": str(payload.get("recommendation") or ""),
            "evidence": [str(item) for item in evidence[:3]],
            "confidence": confidence,
        }
    except Exception:
        return _fallback(
            locale,
            "Doporučení se nepodařilo vygenerovat. Zkus to znovu později."
            if locale == "cs"
            else "The recommendation could not be generated. Try again later.",
        )
