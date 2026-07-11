# Weight-loss coach design

Food Reader is designed around one outcome: helping the user lose body fat at a sustainable pace while preserving muscle, energy and adherence.

## Closed feedback loop

1. A meal is photographed or described.
2. The AI returns components, a central estimate, a calorie range, confidence, assumptions and at most one useful clarification question.
3. The user reviews the estimate. Manual changes and reanalysis corrections are stored separately from the original analysis.
4. Recent corrections calibrate future estimates for that user.
5. The daily coach combines calories, protein, fiber, logging completeness and a short wellbeing check-in into one next action.
6. The weekly coach evaluates all calendar days, weight trend, training and data completeness before recommending any calorie change.

## Weight-loss guardrails

- Default calorie target is an approximately 18% TDEE deficit, constrained to a 300–650 kcal deficit and a BMR-based floor.
- Protein is weight-based, not merely a percentage of calories; the default weight-loss target is 1.8 g/kg.
- Adaptive changes are limited to 100 kcal and require at least four weight readings plus 70% logging completeness.
- Fast loss causes a recommendation to add calories; slow loss only causes a reduction when logging and intake adherence are credible.
- Missing days are included in weekly averages and clearly lower the completeness score. They are never silently treated as low-calorie days.
- The coach never recommends compensatory starvation, extreme restriction, medication or medical treatment.

## Privacy and image security

- Uploads are decoded as real JPEG, PNG or WebP images, dimension-limited, EXIF-rotated and re-encoded as metadata-free JPEG files.
- Images are stored outside public static serving and returned through short-lived signed URLs.
- User and AI text is sanitized before persistence because older UI surfaces still use templated HTML.
- Corrections, check-ins, meals and Withings measurements remain user-scoped.

## Operational notes

- Run Alembic migration `003_weight_loss_coach` before deployment.
- Configure a random `JWT_SECRET` of at least 32 characters in production.
- Set `OPENAI_API_KEY`, `LLM_MODEL` and optionally `COACH_MODEL`.
- Refresh `uv.lock` after dependency changes; Docker and CI intentionally resolve the exact Pillow pin until the lock is regenerated.
