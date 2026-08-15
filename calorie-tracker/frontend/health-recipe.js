import {
  API,
  apiFetch,
  getJsonOrThrow,
  showStatus,
} from './common.js?v=20260403-11';

let recipeRequestInFlight = false;
let recipeGenerated = false;
let currentRecipePayload = null;
let currentUserId = null;

const RECIPE_CACHE_VERSION = 'v1';

function isCzech() {
  return (document.documentElement.lang || '').toLowerCase().startsWith('cs');
}

function copy(cs, en) {
  return isCzech() ? cs : en;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function finiteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function recipeCacheKey(userId) {
  return `food-reader:user:${userId}:recipe:${RECIPE_CACHE_VERSION}`;
}

function readRecipeCache(userId) {
  if (!userId) return null;
  try {
    const raw = window.localStorage.getItem(recipeCacheKey(userId));
    if (!raw) return null;
    const cached = JSON.parse(raw);
    return cached?.payload?.recipe ? cached.payload : null;
  } catch {
    return null;
  }
}

function writeRecipeCache(userId, payload) {
  if (!userId || !payload?.recipe) return;
  try {
    window.localStorage.setItem(
      recipeCacheKey(userId),
      JSON.stringify({
        saved_at: new Date().toISOString(),
        payload,
      }),
    );
  } catch {
    // Persistence is a convenience. The current recipe stays visible even if storage is unavailable.
  }
}

async function resolveCurrentUserId() {
  if (currentUserId) return currentUserId;
  try {
    const response = await apiFetch(API.currentUser);
    if (!response.ok) return null;
    const user = await response.json();
    currentUserId = user?.id || null;
    return currentUserId;
  } catch {
    return null;
  }
}

function applyRecipeCopy() {
  const eyebrow = document.getElementById('recipeEyebrow');
  const heading = document.getElementById('recipeHeading');
  const support = document.getElementById('recipeSupport');
  const button = document.getElementById('generateRecipeButton');
  if (!eyebrow || !heading || !support || !button) return;

  eyebrow.textContent = copy('Další jídlo', 'Next meal');
  heading.textContent = copy('Co si mám dnes uvařit?', 'What should I cook today?');
  support.textContent = copy(
    'Vygenerovaný recept zůstane uložený, dokud si výslovně nevygeneruješ nový. Nové generování vždy používá aktuální stav dne.',
    'The generated recipe stays saved until you explicitly generate a new one. Regeneration always uses the current state of the day.',
  );
  button.textContent = recipeGenerated
    ? copy('Vygenerovat znovu', 'Generate again')
    : copy('Doporučit recept', 'Recommend recipe');
}

function resetRecipe(message = null) {
  const target = document.getElementById('recipeRecommendation');
  if (!target) return;
  target.innerHTML = `<div class="empty-state compact">${escapeHtml(message || copy(
    'Klikni na „Doporučit recept“. Spočítám ho z dnešních aktuálních dat.',
    'Tap “Recommend recipe”. I’ll calculate it from today’s current data.',
  ))}</div>`;
}

function macroLine(macros) {
  const calories = finiteNumber(macros?.calories) ?? 0;
  const protein = finiteNumber(macros?.protein_g) ?? 0;
  const carbs = finiteNumber(macros?.carbs_g) ?? 0;
  const fat = finiteNumber(macros?.fat_g) ?? 0;
  const fiber = finiteNumber(macros?.fiber_g) ?? 0;
  return `${Math.round(calories)} kcal · P ${Math.round(protein)} g · C ${Math.round(carbs)} g · F ${Math.round(fat)} g · ${copy('vláknina', 'fiber')} ${Math.round(fiber)} g`;
}

function remainingLine(context) {
  const consumed = context?.consumed || {};
  const targets = context?.targets || {};
  const remaining = context?.remaining || {};
  const calorieTarget = finiteNumber(targets.calories);
  const proteinTarget = finiteNumber(targets.protein_g);
  const consumedCalories = finiteNumber(consumed.calories) ?? 0;
  const consumedProtein = finiteNumber(consumed.protein_g) ?? 0;
  const remainingCalories = finiteNumber(remaining.calories);
  const remainingProtein = finiteNumber(remaining.protein_g);

  const parts = [];
  if (calorieTarget !== null) {
    parts.push(copy(
      `${Math.round(consumedCalories)} / ${Math.round(calorieTarget)} kcal`,
      `${Math.round(consumedCalories)} / ${Math.round(calorieTarget)} kcal`,
    ));
  }
  if (proteinTarget !== null) {
    parts.push(copy(
      `protein ${Math.round(consumedProtein)} / ${Math.round(proteinTarget)} g`,
      `protein ${Math.round(consumedProtein)} / ${Math.round(proteinTarget)} g`,
    ));
  }
  if (remainingCalories !== null || remainingProtein !== null) {
    const gapParts = [];
    if (remainingCalories !== null) gapParts.push(`${Math.round(remainingCalories)} kcal`);
    if (remainingProtein !== null) gapParts.push(`${Math.round(remainingProtein)} g P`);
    parts.push(copy(`zbývá ${gapParts.join(' · ')}`, `${gapParts.join(' · ')} remaining`));
  }
  return parts.join(' · ');
}

function ouraLine(context) {
  const oura = context?.oura;
  if (!oura) return copy('Oura není použita', 'Oura not used');
  const parts = [];
  if (finiteNumber(oura.steps) !== null) parts.push(`${Math.round(oura.steps)} ${copy('kroků', 'steps')}`);
  if (finiteNumber(oura.active_calories) !== null) parts.push(`${Math.round(oura.active_calories)} ${copy('aktivních kcal', 'active kcal')}`);
  if (finiteNumber(oura.readiness_score) !== null) parts.push(`Readiness ${Math.round(oura.readiness_score)}`);
  return parts.length ? `Oura · ${parts.join(' · ')}` : copy('Oura připojena', 'Oura connected');
}

function renderRecipe(payload) {
  const target = document.getElementById('recipeRecommendation');
  const recipe = payload?.recipe;
  const context = payload?.context || {};
  if (!target || !recipe) return;

  const ingredients = Array.isArray(recipe.ingredients) ? recipe.ingredients : [];
  const steps = Array.isArray(recipe.steps) ? recipe.steps : [];
  const time = (finiteNumber(recipe.prep_minutes) ?? 0) + (finiteNumber(recipe.cook_minutes) ?? 0);

  target.innerHTML = `
    <article class="health-recipe-card">
      <div class="health-recipe-title-row">
        <div>
          <p class="eyebrow">${copy('AI recept pro dnešek', 'AI recipe for today')}</p>
          <h3>${escapeHtml(recipe.title || '')}</h3>
        </div>
        <span class="health-recipe-time">${Math.round(time)} min</span>
      </div>
      <p class="health-recipe-why">${escapeHtml(recipe.why || '')}</p>
      <div class="health-recipe-context" aria-label="Recipe context">
        <span>${escapeHtml(remainingLine(context))}</span>
        <span>${escapeHtml(ouraLine(context))}</span>
      </div>
      <div class="health-recipe-macros">${escapeHtml(macroLine(recipe.macros))}</div>
      <div class="health-recipe-grid">
        <div>
          <h4>${copy('Suroviny', 'Ingredients')}</h4>
          <ul class="health-recipe-ingredients">
            ${ingredients.map((ingredient) => `<li><strong>${escapeHtml(ingredient.amount)}</strong><span>${escapeHtml(ingredient.item)}</span></li>`).join('')}
          </ul>
        </div>
        <div>
          <h4>${copy('Postup', 'Method')}</h4>
          <ol class="health-recipe-steps">
            ${steps.map((step) => `<li>${escapeHtml(step)}</li>`).join('')}
          </ol>
        </div>
      </div>
      <p class="health-recipe-estimate">${copy(
        'Makra jsou orientační odhad. Tento recept zůstane uložený až do dalšího úspěšného přegenerování.',
        'Macros are an estimate. This recipe stays saved until the next successful regeneration.',
      )}</p>
    </article>
  `;
}

async function restoreRecipe() {
  const userId = await resolveCurrentUserId();
  const cached = readRecipeCache(userId);
  if (!cached) return;

  currentRecipePayload = cached;
  recipeGenerated = true;
  renderRecipe(cached);
  applyRecipeCopy();
  const status = document.getElementById('recipeStatus');
  if (status) status.hidden = true;
}

async function generateRecipe() {
  const button = document.getElementById('generateRecipeButton');
  const status = document.getElementById('recipeStatus');
  if (!button || !status || recipeRequestInFlight) return;

  recipeRequestInFlight = true;
  button.disabled = true;
  showStatus(status, copy('Počítám dnešní zbytek a skládám recept…', 'Calculating the rest of today and building a recipe…'), 'info');

  try {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Prague';
    const locale = isCzech() ? 'cs' : 'en';
    const response = await apiFetch('/assistant/recipe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ timezone, locale }),
    });
    const payload = await getJsonOrThrow(response, copy('Nepodařilo se vygenerovat recept', 'Unable to generate recipe'));

    if (!payload.available || !payload.recipe) {
      if (!currentRecipePayload) {
        resetRecipe(payload.message || copy('Recept teď nedává smysl.', 'A recipe is not useful right now.'));
      }
      showStatus(status, payload.message || copy('Recept teď nedává smysl. Původní recept zůstává uložený.', 'A new recipe is not useful right now. The previous recipe stays saved.'), 'info');
      return;
    }

    const userId = await resolveCurrentUserId();
    currentRecipePayload = payload;
    recipeGenerated = true;
    writeRecipeCache(userId, payload);
    renderRecipe(payload);
    applyRecipeCopy();
    showStatus(status, copy('Nový recept je uložený a nahradil předchozí.', 'The new recipe is saved and replaced the previous one.'), 'success');
  } catch (error) {
    showStatus(
      status,
      currentRecipePayload
        ? copy(`Nový recept se nepodařilo vytvořit. Původní zůstává uložený. ${error.message}`, `Could not create a new recipe. The previous one stays saved. ${error.message}`)
        : error.message,
      'danger',
    );
  } finally {
    recipeRequestInFlight = false;
    button.disabled = false;
  }
}

async function initRecipe() {
  applyRecipeCopy();
  resetRecipe();
  const button = document.getElementById('generateRecipeButton');
  if (button) button.addEventListener('click', generateRecipe);
  await restoreRecipe();

  window.addEventListener('food-reader:localechange', () => {
    applyRecipeCopy();
    if (currentRecipePayload) {
      renderRecipe(currentRecipePayload);
    } else {
      resetRecipe();
    }
    const status = document.getElementById('recipeStatus');
    if (status) status.hidden = true;
  });
}

document.addEventListener('DOMContentLoaded', initRecipe);
