import { describe, expect, it } from 'vitest';

import { applyAuthMode } from '../login.js';

describe('login auth mode', () => {
  it('switches between sign-in and register panels', () => {
    document.body.innerHTML = `
      <div class="auth-intro">
        <p class="eyebrow"></p>
        <h1></h1>
        <p class="panel-note"></p>
      </div>
      <button
        data-auth-mode-toggle="signin"
        data-auth-heading="login.signInHeading"
        data-auth-eyebrow="login.welcomeBack"
        data-auth-support="login.signInSupport"
      ></button>
      <button
        data-auth-mode-toggle="register"
        data-auth-heading="login.createAccess"
        data-auth-eyebrow="login.newAccount"
        data-auth-support="login.createSupport"
      ></button>
      <section data-auth-mode-panel="signin"></section>
      <section data-auth-mode-panel="register" hidden></section>
    `;

    applyAuthMode('register');

    expect(document.querySelector('[data-auth-mode-toggle="register"]').classList.contains('active')).toBe(true);
    expect(document.querySelector('[data-auth-mode-panel="register"]').hidden).toBe(false);
    expect(document.querySelector('[data-auth-mode-panel="signin"]').hidden).toBe(true);
    expect(document.querySelector('.auth-intro h1').textContent).toBe('Create access');

    applyAuthMode('signin');

    expect(document.querySelector('[data-auth-mode-toggle="signin"]').classList.contains('active')).toBe(true);
    expect(document.querySelector('[data-auth-mode-panel="signin"]').hidden).toBe(false);
    expect(document.querySelector('[data-auth-mode-panel="register"]').hidden).toBe(true);
    expect(document.querySelector('.auth-intro h1').textContent).toBe('Sign in');
  });
});
