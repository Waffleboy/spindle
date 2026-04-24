import { useEffect, useRef, useCallback } from "react"

const LANDING_STYLES = `
  .lp *, .lp *::before, .lp *::after { margin: 0; padding: 0; box-sizing: border-box; }

  .lp {
    --lp-bg: #FAFAFA;
    --lp-fg: #0F172A;
    --lp-muted: #F1F5F9;
    --lp-muted-fg: #64748B;
    --lp-accent: #0052FF;
    --lp-accent-secondary: #4D7CFF;
    --lp-accent-fg: #FFFFFF;
    --lp-border: #E2E8F0;
    --lp-card: #FFFFFF;
    --lp-ring: #0052FF;
    --lp-serif: 'Calistoga', Georgia, serif;
    --lp-sans: 'Inter', system-ui, sans-serif;
    --lp-mono: 'JetBrains Mono', monospace;
    --lp-ease: cubic-bezier(0.16, 1, 0.3, 1);

    font-family: var(--lp-sans);
    background: var(--lp-bg);
    color: var(--lp-fg);
    line-height: 1.6;
    overflow-x: hidden;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }

  .lp ::selection { background: var(--lp-accent); color: var(--lp-accent-fg); }
  .lp h1, .lp h2, .lp h3 { font-family: var(--lp-serif); font-weight: 400; line-height: 1.15; }

  .lp-container { max-width: 72rem; margin: 0 auto; padding: 0 clamp(24px, 4vw, 48px); }

  .lp-gradient-text {
    background: linear-gradient(to right, var(--lp-accent), var(--lp-accent-secondary));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  /* Nav */
  .lp-nav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px clamp(24px, 4vw, 48px);
    background: rgba(250,250,250,0.8); backdrop-filter: blur(20px);
    border-bottom: 1px solid transparent;
    transition: border-color 0.3s, box-shadow 0.3s;
  }
  .lp-nav.scrolled { border-bottom-color: var(--lp-border); box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
  .lp-nav-wordmark { font-family: var(--lp-serif); font-size: 1.375rem; color: var(--lp-fg); letter-spacing: -0.01em; }
  .lp-nav-links { display: flex; gap: 36px; }
  .lp-nav-links a {
    color: var(--lp-muted-fg); text-decoration: none; font-size: 0.875rem;
    font-weight: 500; transition: color 0.2s; cursor: pointer;
  }
  .lp-nav-links a:hover { color: var(--lp-fg); }

  /* Buttons */
  .lp-btn {
    display: inline-flex; align-items: center; gap: 8px; padding: 12px 28px;
    border-radius: 12px; font-family: var(--lp-sans); font-size: 0.9375rem;
    font-weight: 500; text-decoration: none; cursor: pointer; border: none;
    transition: all 0.2s ease-out;
  }
  .lp-btn-primary {
    background: linear-gradient(to right, var(--lp-accent), var(--lp-accent-secondary));
    color: var(--lp-accent-fg); box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }
  .lp-btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,82,255,0.35);
    filter: brightness(1.1);
  }
  .lp-btn-primary:active { transform: scale(0.98); }
  .lp-btn-outline {
    background: transparent; color: var(--lp-fg);
    border: 1px solid var(--lp-border);
  }
  .lp-btn-outline:hover {
    border-color: rgba(0,82,255,0.3); background: var(--lp-muted);
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  .lp-btn-nav {
    font-size: 0.8125rem; font-weight: 600; padding: 10px 24px;
    border-radius: 12px; border: none; cursor: pointer; font-family: var(--lp-sans);
    background: linear-gradient(to right, var(--lp-accent), var(--lp-accent-secondary));
    color: var(--lp-accent-fg); transition: all 0.2s;
    box-shadow: 0 1px 3px rgba(0,82,255,0.2);
  }
  .lp-btn-nav:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(0,82,255,0.25); }

  /* Section Label */
  .lp-section-label {
    display: inline-flex; align-items: center; gap: 12px;
    border-radius: 9999px; border: 1px solid rgba(0,82,255,0.3);
    background: rgba(0,82,255,0.05); padding: 8px 20px;
  }
  .lp-section-label-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--lp-accent);
    animation: lp-pulse 2s infinite;
  }
  @keyframes lp-pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.3); opacity: 0.7; }
  }
  .lp-section-label-text {
    font-family: var(--lp-mono); font-size: 0.75rem; font-weight: 400;
    letter-spacing: 0.15em; text-transform: uppercase; color: var(--lp-accent);
  }

  /* Hero */
  .lp-hero {
    position: relative; min-height: 100vh; display: flex; align-items: center;
    padding: 120px 0 80px; overflow: hidden;
  }
  .lp-hero::before {
    content: ''; position: absolute; top: -20%; right: -10%;
    width: 800px; height: 800px;
    background: radial-gradient(circle, rgba(0,82,255,0.06) 0%, transparent 70%);
    pointer-events: none;
  }
  .lp-hero-inner {
    display: grid; grid-template-columns: 1.1fr 0.9fr; gap: clamp(32px, 4vw, 64px);
    align-items: center; max-width: 72rem; margin: 0 auto;
    padding: 0 clamp(24px, 4vw, 48px); position: relative;
  }
  .lp-hero-content { max-width: 560px; }
  .lp-hero-title {
    font-size: clamp(2.75rem, 5vw, 5.25rem); color: var(--lp-fg);
    margin-bottom: 24px; letter-spacing: -0.02em; line-height: 1.05;
    animation: lp-fadeUp 0.7s var(--lp-ease) 0.2s both;
  }
  .lp-hero-title-underline {
    position: relative; display: inline-block;
  }
  .lp-hero-title-underline::after {
    content: ''; position: absolute; bottom: -4px; left: 0; right: 0; height: 12px;
    border-radius: 2px;
    background: linear-gradient(to right, rgba(0,82,255,0.15), rgba(77,124,255,0.1));
  }
  .lp-hero-sub {
    font-size: clamp(1.0625rem, 1.5vw, 1.1875rem); color: var(--lp-muted-fg);
    margin-bottom: 36px; font-weight: 400; line-height: 1.7;
    animation: lp-fadeUp 0.7s var(--lp-ease) 0.4s both;
  }
  .lp-hero-actions {
    display: flex; gap: 16px; flex-wrap: wrap;
    animation: lp-fadeUp 0.7s var(--lp-ease) 0.6s both;
  }
  .lp-btn-arrow { transition: transform 0.2s; display: inline-block; }
  .lp-btn-primary:hover .lp-btn-arrow { transform: translateX(4px); }

  @keyframes lp-fadeUp {
    from { opacity: 0; transform: translateY(28px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* Hero Graphic */
  .lp-hero-graphic {
    position: relative; width: 100%; aspect-ratio: 1.4; max-height: 280px;
    animation: lp-fadeUp 0.7s var(--lp-ease) 0.6s both;
  }
  .lp-hero-ring {
    position: absolute; inset: 0; border: 2px dashed rgba(0,82,255,0.15);
    border-radius: 50%; animation: lp-rotate 60s linear infinite;
  }
  @keyframes lp-rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  .lp-hero-float-card {
    position: absolute; background: var(--lp-card); border: 1px solid var(--lp-border);
    border-radius: 16px; padding: 20px; box-shadow: 0 10px 15px rgba(0,0,0,0.08);
  }
  .lp-hero-float-a {
    top: 12%; left: 8%; width: 200px;
    animation: lp-float 5s ease-in-out infinite;
  }
  .lp-hero-float-b {
    bottom: 18%; right: 6%; width: 180px;
    animation: lp-float 4s ease-in-out infinite reverse;
  }
  @keyframes lp-float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
  }
  .lp-float-label {
    font-family: var(--lp-mono); font-size: 0.625rem; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--lp-muted-fg); margin-bottom: 8px;
  }
  .lp-float-value {
    font-family: var(--lp-sans); font-size: 1.5rem; font-weight: 700; color: var(--lp-fg);
  }
  .lp-float-tag {
    display: inline-block; font-family: var(--lp-mono); font-size: 0.625rem;
    padding: 3px 8px; border-radius: 6px; margin-top: 8px;
    background: linear-gradient(to right, var(--lp-accent), var(--lp-accent-secondary));
    color: var(--lp-accent-fg);
  }
  .lp-hero-center-shape {
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    width: 80px; height: 80px; border-radius: 20px;
    background: linear-gradient(135deg, var(--lp-accent), var(--lp-accent-secondary));
    box-shadow: 0 8px 24px rgba(0,82,255,0.35);
  }
  .lp-hero-dots {
    position: absolute; top: 38%; right: 20%;
    display: grid; grid-template-columns: repeat(3, 8px); gap: 10px;
  }
  .lp-hero-dots span {
    width: 8px; height: 8px; border-radius: 50%; background: rgba(0,82,255,0.2);
  }

  /* Stats — Inverted Section */
  .lp-stats-section {
    background: var(--lp-fg); color: var(--lp-bg); padding: 80px 0;
    position: relative; overflow: hidden;
  }
  .lp-stats-section::before {
    content: ''; position: absolute; inset: 0;
    background-image: radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 32px 32px; pointer-events: none;
  }
  .lp-stats-section::after {
    content: ''; position: absolute; top: -30%; right: -10%; width: 500px; height: 500px;
    background: radial-gradient(circle, rgba(0,82,255,0.06) 0%, transparent 70%);
    pointer-events: none;
  }
  .lp-stats-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 0; position: relative;
  }
  .lp-stat { text-align: center; padding: 24px 16px; position: relative; }
  .lp-stat:not(:last-child)::after {
    content: ''; position: absolute; top: 20%; right: 0; height: 60%;
    width: 1px; background: rgba(255,255,255,0.1);
  }
  .lp-stat-number {
    display: block; font-family: var(--lp-serif); font-size: 2.75rem;
    color: var(--lp-accent-fg); line-height: 1; margin-bottom: 6px;
  }
  .lp-stat-unit {
    display: block; font-family: var(--lp-mono); font-size: 0.6875rem;
    letter-spacing: 0.15em; text-transform: uppercase;
    color: rgba(255,255,255,0.5); margin-bottom: 10px;
  }
  .lp-stat-label {
    display: block; font-size: 0.8125rem; color: rgba(255,255,255,0.4);
    line-height: 1.5; max-width: 200px; margin: 0 auto;
  }

  /* Features */
  .lp-features-section { padding: clamp(80px, 12vh, 140px) 0; }
  .lp-features-header { text-align: center; margin-bottom: 72px; }
  .lp-features-title {
    font-size: clamp(2rem, 3.5vw, 3.25rem); margin-top: 20px; margin-bottom: 16px;
  }
  .lp-features-sub {
    font-size: 1.0625rem; color: var(--lp-muted-fg); font-weight: 400;
    max-width: 520px; margin: 0 auto; line-height: 1.7;
  }
  .lp-features-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px;
  }
  .lp-feature-card {
    background: var(--lp-card); border: 1px solid var(--lp-border);
    border-radius: 16px; padding: 32px; position: relative; overflow: hidden;
    transition: all 0.3s ease-out;
  }
  .lp-feature-card::after {
    content: ''; position: absolute; inset: 0; opacity: 0;
    background: linear-gradient(135deg, rgba(0,82,255,0.03), transparent);
    transition: opacity 0.3s;
  }
  .lp-feature-card:hover { box-shadow: 0 20px 25px rgba(0,0,0,0.1); transform: translateY(-2px); }
  .lp-feature-card:hover::after { opacity: 1; }
  .lp-feature-icon {
    width: 48px; height: 48px; border-radius: 12px; display: flex;
    align-items: center; justify-content: center; margin-bottom: 20px;
    background: linear-gradient(135deg, var(--lp-accent), var(--lp-accent-secondary));
    box-shadow: 0 4px 14px rgba(0,82,255,0.25);
  }
  .lp-feature-icon svg { width: 24px; height: 24px; stroke: white; fill: none; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
  .lp-feature-card h3 {
    font-family: var(--lp-sans); font-size: 1.125rem; font-weight: 600;
    margin-bottom: 10px; letter-spacing: -0.01em;
  }
  .lp-feature-card p { font-size: 0.9375rem; color: var(--lp-muted-fg); line-height: 1.625; }

  /* How It Works */
  .lp-how-section { padding: clamp(80px, 12vh, 140px) 0; background: var(--lp-muted); }
  .lp-how-header { text-align: center; margin-bottom: 72px; }
  .lp-how-title { font-size: clamp(2rem, 3.5vw, 3.25rem); margin-top: 20px; margin-bottom: 16px; }
  .lp-how-sub { font-size: 1.0625rem; color: var(--lp-muted-fg); max-width: 480px; margin: 0 auto; line-height: 1.7; }
  .lp-how-flow {
    display: flex; align-items: flex-start; justify-content: center; gap: 0;
    position: relative;
  }
  .lp-how-step { flex: 0 0 180px; text-align: center; position: relative; }
  .lp-how-step-number {
    font-family: var(--lp-serif); font-size: 2rem; color: rgba(0,82,255,0.15); margin-bottom: 12px;
  }
  .lp-how-step-icon-wrap {
    width: 56px; height: 56px; border-radius: 14px;
    background: var(--lp-card); border: 1px solid var(--lp-border);
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 16px; transition: all 0.4s;
    box-shadow: 0 4px 6px rgba(0,0,0,0.07);
  }
  .lp-how-step-icon-wrap svg { width: 24px; height: 24px; stroke: var(--lp-muted-fg); fill: none; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
  .lp-how-step.visible .lp-how-step-icon-wrap {
    background: linear-gradient(135deg, var(--lp-accent), var(--lp-accent-secondary));
    border-color: transparent; box-shadow: 0 4px 14px rgba(0,82,255,0.25);
  }
  .lp-how-step.visible .lp-how-step-icon-wrap svg { stroke: white; }
  .lp-how-step h3 { font-family: var(--lp-sans); font-size: 1rem; font-weight: 600; margin-bottom: 8px; }
  .lp-how-step p { font-size: 0.8125rem; color: var(--lp-muted-fg); line-height: 1.5; max-width: 160px; margin: 0 auto; }
  .lp-how-connector {
    flex: 0 0 40px; display: flex; align-items: center; justify-content: center;
    margin-top: 50px;
  }
  .lp-how-connector-badge {
    width: 28px; height: 28px; border-radius: 50%;
    background: linear-gradient(135deg, var(--lp-accent), var(--lp-accent-secondary));
    display: flex; align-items: center; justify-content: center;
  }
  .lp-how-connector-badge svg { width: 14px; height: 14px; stroke: white; fill: none; stroke-width: 2; }

  /* Deep Dive Features */
  .lp-deep-section { padding: clamp(80px, 12vh, 140px) 0; }
  .lp-deep-feature {
    max-width: 72rem; margin: 0 auto 80px;
    padding: 0 clamp(24px, 4vw, 48px);
    display: grid; grid-template-columns: 1.2fr 0.8fr; gap: clamp(48px, 6vw, 80px);
    align-items: center;
  }
  .lp-deep-feature:last-child { margin-bottom: 0; }
  .lp-deep-feature-reverse .lp-deep-text { order: -1; }
  .lp-deep-text h2 { font-size: clamp(1.5rem, 2.5vw, 2.25rem); margin-bottom: 16px; line-height: 1.2; }
  .lp-deep-text p { color: var(--lp-muted-fg); font-size: 1rem; margin-bottom: 12px; line-height: 1.7; }
  .lp-deep-detail { font-size: 0.9375rem !important; color: var(--lp-muted-fg) !important; opacity: 0.8; }

  /* Schema Visual */
  .lp-schema-demo { display: flex; align-items: center; gap: 24px; }
  .lp-schema-doc {
    flex: 0 0 120px; background: var(--lp-card); border: 1px solid var(--lp-border);
    border-radius: 12px; padding: 20px 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.07);
  }
  .lp-doc-lines { display: flex; flex-direction: column; gap: 8px; }
  .lp-doc-line { height: 3px; background: var(--lp-border); border-radius: 2px; }
  .lp-doc-line.short { width: 60%; }
  .lp-schema-arrow { color: var(--lp-muted-fg); font-size: 1.5rem; flex-shrink: 0; opacity: 0.4; }
  .lp-schema-columns { flex: 1; display: flex; flex-direction: column; gap: 6px; }
  .lp-schema-col {
    font-family: var(--lp-mono); font-size: 0.8125rem; padding: 10px 16px;
    background: var(--lp-card); border: 1px solid var(--lp-border); border-radius: 8px;
    border-left: 3px solid var(--lp-accent); color: var(--lp-muted-fg);
    opacity: 0; transform: translateX(20px);
    transition: opacity 0.5s var(--lp-ease), transform 0.5s var(--lp-ease);
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }
  .lp-schema-col.visible { opacity: 1; transform: translateX(0); }

  /* Entity Visual */
  .lp-entity-demo { display: flex; flex-direction: column; gap: 24px; }
  .lp-entity-group { display: flex; align-items: center; gap: 16px; }
  .lp-entity-before-list { display: flex; flex-direction: column; gap: 8px; flex: 1; }
  .lp-entity-name-tag {
    font-family: var(--lp-mono); font-size: 0.8125rem; padding: 8px 14px;
    background: var(--lp-card); border: 1px solid var(--lp-border); border-radius: 8px;
    color: var(--lp-muted-fg);
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }
  .lp-entity-connector { display: flex; flex-direction: column; align-items: center; gap: 2px; flex-shrink: 0; }
  .lp-connector-line {
    width: 48px; height: 2px;
    background: linear-gradient(to right, var(--lp-accent), var(--lp-accent-secondary));
    opacity: 0; transform: scaleX(0);
    transition: opacity 0.5s, transform 0.6s var(--lp-ease); transform-origin: left;
  }
  .lp-connector-line.visible { opacity: 0.6; transform: scaleX(1); }
  .lp-entity-canonical-card {
    background: var(--lp-card); border: 2px solid var(--lp-accent);
    border-radius: 12px; padding: 16px 20px; flex-shrink: 0;
    box-shadow: 0 4px 14px rgba(0,82,255,0.15);
  }
  .lp-canonical-label {
    font-family: var(--lp-mono); font-size: 0.625rem; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--lp-accent); margin-bottom: 4px;
  }
  .lp-canonical-value { font-family: var(--lp-mono); font-size: 0.875rem; color: var(--lp-fg); font-weight: 500; }
  .lp-entity-confidence { text-align: center; margin-top: 8px; }
  .lp-confidence-bar {
    width: 100%; height: 4px; background: var(--lp-border);
    border-radius: 2px; overflow: hidden; margin-bottom: 6px;
  }
  .lp-confidence-fill {
    height: 100%; border-radius: 2px; width: 0%;
    background: linear-gradient(to right, var(--lp-accent), var(--lp-accent-secondary));
    transition: width 1s var(--lp-ease) 0.5s;
  }
  .lp-confidence-fill.visible { width: 94%; }
  .lp-confidence-text { font-family: var(--lp-mono); font-size: 0.6875rem; color: var(--lp-muted-fg); }

  /* Contradiction Visual */
  .lp-contradiction-demo { display: flex; align-items: center; gap: 20px; }
  .lp-contradiction-card {
    flex: 1; background: var(--lp-card); border: 1px solid var(--lp-border);
    border-radius: 12px; padding: 20px; position: relative;
    box-shadow: 0 4px 6px rgba(0,0,0,0.07);
  }
  .lp-contradiction-card-a { border-color: var(--lp-accent); box-shadow: 0 4px 14px rgba(0,82,255,0.15); }
  .lp-contradiction-card-b { opacity: 0.7; }
  .lp-contra-source { font-family: var(--lp-mono); font-size: 0.6875rem; color: var(--lp-muted-fg); letter-spacing: 0.05em; margin-bottom: 8px; }
  .lp-contra-value { font-family: var(--lp-sans); font-size: 1.75rem; font-weight: 700; margin-bottom: 8px; }
  .lp-contradiction-card-a .lp-contra-value { color: var(--lp-accent); }
  .lp-contradiction-card-b .lp-contra-value { color: #DC2626; text-decoration: line-through; text-decoration-color: rgba(220,38,38,0.4); }
  .lp-contra-badge {
    display: inline-block; font-family: var(--lp-mono); font-size: 0.625rem;
    letter-spacing: 0.08em; text-transform: uppercase; padding: 4px 10px;
    border-radius: 6px;
    background: linear-gradient(to right, var(--lp-accent), var(--lp-accent-secondary));
    color: var(--lp-accent-fg);
  }
  .lp-contra-badge-old { background: rgba(220,38,38,0.1); color: #DC2626; }
  .lp-contradiction-vs { display: flex; flex-direction: column; align-items: center; gap: 6px; flex-shrink: 0; }
  .lp-vs-line { width: 1px; height: 20px; background: #DC2626; opacity: 0.3; }
  .lp-vs-symbol {
    font-family: var(--lp-mono); font-size: 0.875rem; color: #DC2626; font-weight: 500;
    width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
    border-radius: 50%; border: 1px solid #DC2626; background: rgba(220,38,38,0.08);
  }

  /* Hero Right Column */
  .lp-hero-right-col {
    display: flex; flex-direction: column; gap: 20px;
  }

  /* Hero Quote */
  .lp-hero-quote {
    padding: 32px 36px; border-left: 3px solid var(--lp-accent);
    background: var(--lp-card); border-radius: 16px;
    border: 1px solid var(--lp-border); border-left: 3px solid var(--lp-accent);
    box-shadow: 0 10px 15px rgba(0,0,0,0.08);
    animation: lp-fadeUp 0.7s var(--lp-ease) 0.5s both;
  }
  .lp-hero-quote p {
    font-size: 1.0625rem; color: var(--lp-muted-fg); line-height: 1.75;
    font-style: italic;
  }

  /* Preview */
  .lp-preview-section { padding: clamp(80px, 12vh, 140px) 0; background: var(--lp-muted); }
  .lp-preview-header { text-align: center; margin-bottom: 56px; }
  .lp-preview-title { font-size: clamp(2rem, 3.5vw, 3.25rem); margin-top: 20px; margin-bottom: 16px; }
  .lp-preview-sub { font-size: 1.0625rem; color: var(--lp-muted-fg); max-width: 480px; margin: 0 auto; line-height: 1.7; }
  .lp-preview-frame {
    max-width: 1100px; margin: 0 auto; border-radius: 16px; border: 1px solid var(--lp-border);
    overflow: hidden; background: var(--lp-card);
    box-shadow: 0 20px 25px rgba(0,0,0,0.1), 0 0 0 1px rgba(0,0,0,0.02);
  }
  .lp-preview-chrome {
    display: flex; align-items: center; gap: 12px; padding: 12px 16px;
    background: var(--lp-muted); border-bottom: 1px solid var(--lp-border);
  }
  .lp-chrome-dots { display: flex; gap: 6px; }
  .lp-chrome-dots span { width: 10px; height: 10px; border-radius: 50%; background: var(--lp-border); }
  .lp-chrome-dots span:first-child { background: #EF4444; opacity: 0.8; }
  .lp-chrome-dots span:nth-child(2) { background: #F59E0B; opacity: 0.8; }
  .lp-chrome-dots span:nth-child(3) { background: #22C55E; opacity: 0.8; }
  .lp-chrome-url {
    font-family: var(--lp-mono); font-size: 0.6875rem; color: var(--lp-muted-fg);
    background: var(--lp-card); padding: 4px 16px; border-radius: 8px;
    flex: 1; max-width: 300px; border: 1px solid var(--lp-border);
  }

  .lp-preview-topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 16px; border-bottom: 1px solid var(--lp-border); background: var(--lp-card);
  }
  .lp-preview-topbar-brand { font-family: var(--lp-serif); font-size: 0.875rem; color: var(--lp-fg); }
  .lp-preview-topbar-subtitle { font-size: 0.6875rem; color: var(--lp-muted-fg); margin-left: 10px; font-family: var(--lp-sans); }
  .lp-preview-progress { display: flex; gap: 3px; }
  .lp-progress-seg {
    height: 3px; width: 32px; border-radius: 2px;
    background: linear-gradient(to right, var(--lp-accent), var(--lp-accent-secondary));
  }

  .lp-preview-app { display: grid; grid-template-columns: 200px 1fr 260px; min-height: 360px; }
  .lp-prev-left { border-right: 1px solid var(--lp-border); padding: 12px; background: var(--lp-bg); }
  .lp-prev-panel-title {
    font-family: var(--lp-mono); font-size: 0.625rem; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--lp-muted-fg); margin-bottom: 12px;
  }
  .lp-prev-upload {
    border: 1px dashed var(--lp-border); border-radius: 8px; padding: 10px;
    text-align: center; font-size: 0.6875rem; color: var(--lp-muted-fg); margin-bottom: 12px;
  }
  .lp-prev-doc {
    display: flex; align-items: center; gap: 8px; padding: 6px 8px;
    border-radius: 6px; margin-bottom: 3px; font-size: 0.6875rem; color: var(--lp-muted-fg);
  }
  .lp-prev-doc:first-of-type { background: var(--lp-muted); }
  .lp-prev-doc-icon {
    width: 14px; height: 14px; background: rgba(220,38,38,0.1); border-radius: 3px;
    display: flex; align-items: center; justify-content: center;
    font-size: 8px; color: #DC2626; flex-shrink: 0;
  }
  .lp-prev-doc-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--lp-fg); }
  .lp-prev-doc-date { font-family: var(--lp-mono); font-size: 0.5625rem; color: var(--lp-muted-fg); flex-shrink: 0; }
  .lp-prev-doc-check { color: #22C55E; font-size: 0.625rem; flex-shrink: 0; }

  .lp-prev-center { display: flex; flex-direction: column; }
  .lp-prev-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--lp-border); }
  .lp-prev-tab {
    padding: 8px 18px; font-size: 0.6875rem; color: var(--lp-muted-fg);
    border-bottom: 2px solid transparent; font-weight: 500;
  }
  .lp-prev-tab.active { color: var(--lp-accent); border-bottom-color: var(--lp-accent); }
  .lp-prev-grid { flex: 1; padding: 8px; overflow: hidden; }
  .lp-prev-grid-header, .lp-prev-grid-row { display: grid; grid-template-columns: 1.3fr 0.8fr 1fr 0.8fr 0.7fr; gap: 1px; font-size: 0.6875rem; }
  .lp-prev-grid-header { margin-bottom: 4px; }
  .lp-prev-grid-header span {
    padding: 6px 8px; font-family: var(--lp-mono); font-size: 0.5625rem;
    letter-spacing: 0.05em; text-transform: uppercase; color: var(--lp-muted-fg);
    border-bottom: 1px solid var(--lp-border);
  }
  .lp-prev-grid-row { margin-bottom: 1px; }
  .lp-prev-grid-row span { padding: 7px 8px; color: var(--lp-fg); border-bottom: 1px solid var(--lp-border); font-size: 0.6875rem; }
  .lp-prev-cell-red { background: rgba(220,38,38,0.08) !important; position: relative; }
  .lp-prev-cell-amber { background: rgba(245,158,11,0.08) !important; }
  .lp-prev-cell-green { border-left: 2px solid #22C55E !important; }

  .lp-prev-cell-red .lp-cell-tooltip {
    position: absolute; bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%) translateY(5px);
    width: 200px; background: var(--lp-fg); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;
    padding: 10px; opacity: 0; pointer-events: none; transition: opacity 0.2s, transform 0.2s; z-index: 10;
  }
  .lp-prev-cell-red:hover .lp-cell-tooltip { opacity: 1; transform: translateX(-50%) translateY(0); }
  .lp-tooltip-title { font-family: var(--lp-mono); font-size: 0.5625rem; color: #EF4444; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 6px; }
  .lp-tooltip-values { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 6px; }
  .lp-tooltip-val { font-family: var(--lp-mono); font-size: 0.75rem; color: #FFFFFF; }
  .lp-tooltip-val small { display: block; font-size: 0.5625rem; color: rgba(255,255,255,0.5); font-family: var(--lp-sans); }
  .lp-tooltip-temporal { font-size: 0.5625rem; color: var(--lp-accent-secondary); text-align: center; }

  .lp-prev-right { border-left: 1px solid var(--lp-border); display: flex; flex-direction: column; background: var(--lp-bg); }
  .lp-prev-right .lp-prev-panel-title { padding: 12px 12px 8px; }
  .lp-prev-chat-messages { flex: 1; padding: 0 12px; display: flex; flex-direction: column; gap: 8px; overflow: hidden; }
  .lp-prev-chat-msg { font-size: 0.6875rem; line-height: 1.5; padding: 8px 10px; border-radius: 10px; max-width: 95%; }
  .lp-prev-chat-user {
    background: linear-gradient(135deg, var(--lp-accent), var(--lp-accent-secondary));
    color: var(--lp-accent-fg); align-self: flex-end; border-bottom-right-radius: 4px;
  }
  .lp-prev-chat-assistant {
    background: var(--lp-card); color: var(--lp-fg);
    border: 1px solid var(--lp-border); align-self: flex-start; border-bottom-left-radius: 4px;
  }
  .lp-prev-citation {
    display: inline-block; font-family: var(--lp-mono); font-size: 0.5625rem;
    padding: 2px 6px; background: rgba(0,82,255,0.08); color: var(--lp-accent);
    border-radius: 4px; margin-top: 4px; margin-right: 4px;
  }
  .lp-prev-chat-input {
    padding: 10px 12px; border-top: 1px solid var(--lp-border);
    display: flex; align-items: center; gap: 8px;
  }
  .lp-prev-chat-input-field {
    flex: 1; background: var(--lp-card); border: 1px solid var(--lp-border);
    border-radius: 8px; padding: 6px 10px; font-size: 0.6875rem; color: var(--lp-muted-fg);
  }
  .lp-prev-chat-send {
    width: 28px; height: 28px; border-radius: 8px; display: flex;
    align-items: center; justify-content: center;
    background: linear-gradient(135deg, var(--lp-accent), var(--lp-accent-secondary));
  }
  .lp-prev-chat-send svg { width: 12px; height: 12px; stroke: white; fill: none; stroke-width: 2; }

  .lp-cursor-blink::after { content: '|'; animation: lp-blink 1s step-end infinite; color: var(--lp-accent); }
  @keyframes lp-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

  /* CTA — Inverted Section */
  .lp-cta {
    background: var(--lp-fg); color: var(--lp-bg); padding: clamp(100px, 14vh, 180px) 0;
    text-align: center; position: relative; overflow: hidden;
  }
  .lp-cta::before {
    content: ''; position: absolute; inset: 0;
    background-image: radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 32px 32px; pointer-events: none;
  }
  .lp-cta::after {
    content: ''; position: absolute; bottom: -20%; left: 50%; transform: translateX(-50%);
    width: 800px; height: 500px;
    background: radial-gradient(ellipse, rgba(0,82,255,0.08) 0%, transparent 70%);
    pointer-events: none;
  }
  .lp-cta-title {
    font-size: clamp(2rem, 4vw, 3.5rem); margin-bottom: 16px; position: relative;
    color: rgba(255,255,255,0.95);
  }
  .lp-cta-sub {
    font-size: 1.0625rem; color: rgba(255,255,255,0.5); margin-bottom: 40px; font-weight: 400;
  }
  .lp-cta-email {
    display: flex; gap: 12px; max-width: 420px; margin: 0 auto;
  }
  .lp-cta-input {
    flex: 1; height: 48px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.15);
    background: rgba(255,255,255,0.05); padding: 0 16px; font-size: 0.875rem;
    color: rgba(255,255,255,0.8); font-family: var(--lp-sans); outline: none;
    transition: border-color 0.2s;
  }
  .lp-cta-input::placeholder { color: rgba(255,255,255,0.3); }
  .lp-cta-input:focus { border-color: var(--lp-accent); }

  /* Footer */
  .lp-footer { border-top: 1px solid var(--lp-border); padding: 48px 0; text-align: center; }
  .lp-footer-brand { font-family: var(--lp-serif); font-size: 1rem; color: var(--lp-muted-fg); margin-bottom: 8px; }
  .lp-footer-tagline { font-size: 0.8125rem; color: var(--lp-muted-fg); font-weight: 400; opacity: 0.7; }

  /* Reveal */
  .lp-reveal { opacity: 0; transform: translateY(28px); transition: opacity 0.7s var(--lp-ease), transform 0.7s var(--lp-ease); }
  .lp-reveal.visible { opacity: 1; transform: translateY(0); }
  .lp-reveal-d1 { transition-delay: 0.1s; }
  .lp-reveal-d2 { transition-delay: 0.2s; }
  .lp-reveal-d3 { transition-delay: 0.3s; }
  .lp-reveal-d4 { transition-delay: 0.4s; }
  .lp-reveal-d5 { transition-delay: 0.5s; }

  /* Responsive */
  @media (max-width: 900px) {
    .lp-nav-links { display: none; }
    .lp-hero-inner { grid-template-columns: 1fr; }
    .lp-hero-right-col { display: none; }
    .lp-hero-content { max-width: 100%; text-align: center; }
    .lp-hero-actions { justify-content: center; }
    .lp-hero-actions .lp-btn { width: 100%; justify-content: center; }
    .lp-stats-grid { grid-template-columns: repeat(2, 1fr); }
    .lp-stat:not(:last-child)::after { display: none; }
    .lp-features-grid { grid-template-columns: 1fr; }
    .lp-how-flow { flex-direction: column; align-items: center; }
    .lp-how-connector { transform: rotate(90deg); }
    .lp-deep-feature { grid-template-columns: 1fr; gap: 32px; }
    .lp-deep-feature-reverse .lp-deep-text { order: 0; }
    .lp-preview-app { grid-template-columns: 1fr; }
    .lp-prev-left { display: none; }
    .lp-prev-right { min-height: 200px; }
    .lp-contradiction-demo { flex-direction: column; }
    .lp-contradiction-vs { flex-direction: row; }
    .lp-vs-line { width: 20px; height: 1px; }
    .lp-schema-demo { flex-direction: column; }
    .lp-cta-email { flex-direction: column; }
    .lp-cta-email .lp-btn { width: 100%; justify-content: center; }
  }
  @media (max-width: 600px) {
    .lp-stats-grid { grid-template-columns: 1fr; }
    .lp-prev-grid-header, .lp-prev-grid-row { grid-template-columns: 1.2fr 0.8fr 1fr; }
    .lp-prev-grid-header span:nth-child(n+4), .lp-prev-grid-row span:nth-child(n+4) { display: none; }
  }

  @media (prefers-reduced-motion: reduce) {
    .lp-hero-ring, .lp-hero-float-a, .lp-hero-float-b, .lp-section-label-dot { animation: none; }
    .lp-reveal { transition: none; opacity: 1; transform: none; }
  }
`

interface LandingPageProps {
  onEnterApp: () => void
}

export function LandingPage({ onEnterApp }: LandingPageProps) {
  const rootRef = useRef<HTMLDivElement>(null)

  const scrollTo = useCallback((id: string) => {
    const el = document.getElementById(id)
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" })
  }, [])

  useEffect(() => {
    const root = rootRef.current
    if (!root) return

    const reveals = root.querySelectorAll(".lp-reveal")
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible")
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.15, rootMargin: "0px 0px -60px 0px" }
    )
    reveals.forEach((el) => observer.observe(el))

    // Counter animation
    let counted = false
    const counterEl = root.querySelector<HTMLElement>("[data-count]")
    const counterObserver = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !counted) {
          counted = true
          const target = parseInt(counterEl!.dataset.count!)
          const start = performance.now()
          const duration = 1200
          function tick(now: number) {
            const progress = Math.min((now - start) / duration, 1)
            const eased = 1 - Math.pow(1 - progress, 3)
            counterEl!.textContent = String(Math.round(eased * target))
            if (progress < 1) requestAnimationFrame(tick)
          }
          requestAnimationFrame(tick)
        }
      },
      { threshold: 0.5 }
    )
    if (counterEl) counterObserver.observe(counterEl)

    // Schema columns stagger
    const schemaCols = root.querySelectorAll(".lp-schema-col")
    const schemaParent = schemaCols[0]?.parentElement
    const schemaObserver = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          schemaCols.forEach((col, i) => {
            setTimeout(() => col.classList.add("visible"), 200 + i * 150)
          })
          schemaObserver.disconnect()
        }
      },
      { threshold: 0.3 }
    )
    if (schemaParent) schemaObserver.observe(schemaParent)

    // Entity connector lines
    const entityDemo = root.querySelector(".lp-entity-demo")
    const entityObserver = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          const lines = entityDemo!.querySelectorAll(".lp-connector-line")
          lines.forEach((line, i) => {
            setTimeout(() => line.classList.add("visible"), 300 + i * 200)
          })
          const fill = root.querySelector(".lp-confidence-fill")
          setTimeout(() => fill?.classList.add("visible"), 1000)
          entityObserver.disconnect()
        }
      },
      { threshold: 0.3 }
    )
    if (entityDemo) entityObserver.observe(entityDemo)

    // Pipeline steps
    const steps = root.querySelectorAll(".lp-how-step")
    const stepsObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible")
            stepsObserver.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.3 }
    )
    steps.forEach((el) => stepsObserver.observe(el))

    // Nav scroll
    const nav = root.querySelector<HTMLElement>(".lp-nav")
    function handleScroll() {
      if (nav) {
        nav.classList.toggle("scrolled", window.scrollY > 60)
      }
    }
    window.addEventListener("scroll", handleScroll, { passive: true })

    return () => {
      observer.disconnect()
      counterObserver.disconnect()
      schemaObserver.disconnect()
      entityObserver.disconnect()
      stepsObserver.disconnect()
      window.removeEventListener("scroll", handleScroll)
    }
  }, [])

  return (
    <>
      <style>{LANDING_STYLES}</style>
      <div className="lp" ref={rootRef}>

        {/* Nav */}
        <nav className="lp-nav">
          <div className="lp-nav-wordmark">Spindle</div>
          <div className="lp-nav-links">
            <a onClick={() => scrollTo("lp-features")}>Features</a>
            <a onClick={() => scrollTo("lp-how")}>How it works</a>
            <a onClick={() => scrollTo("lp-preview")}>Preview</a>
          </div>
          <button className="lp-btn-nav" onClick={onEnterApp}>Open Spindle <span className="lp-btn-arrow">&rarr;</span></button>
        </nav>

        {/* Hero */}
        <section className="lp-hero">
          <div className="lp-hero-inner">
            <div className="lp-hero-content">
              <div style={{ marginBottom: 24, animation: "lp-fadeUp 0.7s cubic-bezier(0.16,1,0.3,1) 0.1s both" }}>
                <div className="lp-section-label">
                  <span className="lp-section-label-dot" />
                  <span className="lp-section-label-text">Investor Report Intelligence</span>
                </div>
              </div>
              <h1 className="lp-hero-title">
                Intelligence from{" "}
                <span className="lp-hero-title-underline">
                  <span className="lp-gradient-text">your reports</span>
                  <span style={{
                    position: "absolute", bottom: "-4px", left: 0, right: 0, height: "12px",
                    borderRadius: 2,
                    background: "linear-gradient(to right, rgba(0,82,255,0.15), rgba(77,124,255,0.1))"
                  }} />
                </span>
              </h1>
              <p className="lp-hero-sub">
                Drop in analyst reports. In 30 seconds, know what changed,
                what conflicts, and what matters.
              </p>
              <div className="lp-hero-actions">
                <button className="lp-btn lp-btn-primary" onClick={onEnterApp}>
                  Open Spindle <span className="lp-btn-arrow">&rarr;</span>
                </button>
                <button className="lp-btn lp-btn-outline" onClick={() => scrollTo("lp-how")}>
                  See how it works
                </button>
              </div>
            </div>

            {/* Hero Right Column */}
            <div className="lp-hero-right-col">
              <div className="lp-hero-quote">
                <p>&ldquo;Every analyst I&rsquo;ve worked with spends hours cross-referencing reports manually &mdash; checking if revenue numbers match, figuring out that &lsquo;Tan Kim Bock&rsquo; and &lsquo;Bock Kim Tan&rsquo; are the same person, spotting which report supersedes which. Spindle does that in 30 seconds.&rdquo;</p>
              </div>
              <div className="lp-hero-graphic">
                <div className="lp-hero-ring" />
                <div className="lp-hero-center-shape" />
                <div className="lp-hero-dots">
                  {Array.from({ length: 9 }).map((_, i) => (
                    <span key={i} />
                  ))}
                </div>
                <div className="lp-hero-float-card lp-hero-float-a">
                  <div className="lp-float-label">Revenue Q2</div>
                  <div className="lp-float-value">$4.2M</div>
                  <div className="lp-float-tag">Most Recent</div>
                </div>
                <div className="lp-hero-float-card lp-hero-float-b">
                  <div className="lp-float-label">Entities Resolved</div>
                  <div className="lp-float-value">24</div>
                  <div className="lp-float-tag">94% confidence</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Stats — Inverted */}
        <section className="lp-stats-section lp-reveal">
          <div className="lp-container">
            <div className="lp-stats-grid">
              <div className="lp-stat">
                <span className="lp-stat-number" data-count="30">0</span>
                <span className="lp-stat-unit">seconds</span>
                <span className="lp-stat-label">To cross-reference what takes hours</span>
              </div>
              <div className="lp-stat">
                <span className="lp-stat-number">Zero</span>
                <span className="lp-stat-unit">configuration</span>
                <span className="lp-stat-label">Discovers the schema from your documents</span>
              </div>
              <div className="lp-stat">
                <span className="lp-stat-number">Every</span>
                <span className="lp-stat-unit">contradiction</span>
                <span className="lp-stat-label">Surfaced, not buried in a footnote</span>
              </div>
              <div className="lp-stat">
                <span className="lp-stat-number">100%</span>
                <span className="lp-stat-unit">traceable</span>
                <span className="lp-stat-label">Every value linked to its source page</span>
              </div>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="lp-features-section" id="lp-features">
          <div className="lp-container">
            <div className="lp-features-header">
              <div className="lp-section-label lp-reveal">
                <span className="lp-section-label-dot" />
                <span className="lp-section-label-text">Features</span>
              </div>
              <h2 className="lp-features-title lp-reveal lp-reveal-d1">
                Everything you need to <span className="lp-gradient-text">know your reports</span>
              </h2>
              <p className="lp-features-sub lp-reveal lp-reveal-d2">
                Autonomous discovery, structured extraction, and intelligent cross-referencing — all in one tool.
              </p>
            </div>

            <div className="lp-features-grid">
              {[
                {
                  icon: (
                    <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
                  ),
                  title: "Schema Discovery",
                  desc: "AI reads your documents and decides what dimensions matter. No configuration needed."
                },
                {
                  icon: (
                    <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /></svg>
                  ),
                  title: "Structured Extraction",
                  desc: "Values pulled from every page, table, and chart — with confidence scores and source pages."
                },
                {
                  icon: (
                    <svg viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>
                  ),
                  title: "Entity Resolution",
                  desc: "Same person, different name? Spindle matches entities across reports by context."
                },
                {
                  icon: (
                    <svg viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
                  ),
                  title: "Contradiction Detection",
                  desc: "Conflicting values flagged with temporal awareness — it knows August supersedes July."
                },
                {
                  icon: (
                    <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                  ),
                  title: "Intelligent Chat",
                  desc: "Ask questions about your reports. Get answers with inline citations and source pages."
                },
                {
                  icon: (
                    <svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                  ),
                  title: "Multi-Format Support",
                  desc: "PDF, Word, Excel, CSV — drop any analyst report and Spindle handles the rest."
                },
              ].map((f, i) => (
                <div className={`lp-feature-card lp-reveal lp-reveal-d${Math.min(i + 1, 5)}`} key={f.title}>
                  <div className="lp-feature-icon">{f.icon}</div>
                  <h3>{f.title}</h3>
                  <p>{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="lp-how-section" id="lp-how">
          <div className="lp-container">
            <div className="lp-how-header">
              <div className="lp-section-label lp-reveal">
                <span className="lp-section-label-dot" />
                <span className="lp-section-label-text">How It Works</span>
              </div>
              <h2 className="lp-how-title lp-reveal lp-reveal-d1">
                Five steps. One click. <span className="lp-gradient-text">Full intelligence.</span>
              </h2>
              <p className="lp-how-sub lp-reveal lp-reveal-d2">Upload your reports and let the pipeline do the rest.</p>
            </div>

            <div className="lp-how-flow">
              {[
                { num: "01", icon: <svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>, title: "Drop", desc: "Upload analyst reports — PDF, Word, or Excel" },
                { num: "02", icon: <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>, title: "Discover", desc: "AI reads documents and decides what matters" },
                { num: "03", icon: <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /></svg>, title: "Extract", desc: "Structured data from every page and table" },
                { num: "04", icon: <svg viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>, title: "Resolve", desc: "Entities matched across documents" },
                { num: "05", icon: <svg viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>, title: "Detect", desc: "Contradictions flagged with temporal context" },
              ].map((step, i) => (
                <div key={step.num} style={{ display: "contents" }}>
                  <div className={`lp-how-step lp-reveal lp-reveal-d${Math.min(i + 1, 5)}`}>
                    <div className="lp-how-step-number">{step.num}</div>
                    <div className="lp-how-step-icon-wrap">{step.icon}</div>
                    <h3>{step.title}</h3>
                    <p>{step.desc}</p>
                  </div>
                  {i < 4 && (
                    <div className={`lp-how-connector lp-reveal lp-reveal-d${Math.min(i + 1, 5)}`}>
                      <div className="lp-how-connector-badge">
                        <svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6" /></svg>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Deep Dive Features */}
        <section className="lp-deep-section">
          {/* Schema Discovery */}
          <div className="lp-deep-feature">
            <div className="lp-deep-visual lp-reveal">
              <div className="lp-schema-demo">
                <div className="lp-schema-doc">
                  <div className="lp-doc-lines">
                    <div className="lp-doc-line" />
                    <div className="lp-doc-line" />
                    <div className="lp-doc-line short" />
                    <div className="lp-doc-line" />
                    <div className="lp-doc-line short" />
                    <div className="lp-doc-line" />
                  </div>
                </div>
                <div className="lp-schema-arrow">&rarr;</div>
                <div className="lp-schema-columns">
                  {["Company Name", "Revenue", "Reporting Period", "Key Personnel", "Risk Factors"].map((col) => (
                    <div className="lp-schema-col" key={col}>{col}</div>
                  ))}
                </div>
              </div>
            </div>
            <div className="lp-deep-text lp-reveal lp-reveal-d2">
              <div className="lp-section-label" style={{ marginBottom: 16 }}>
                <span className="lp-section-label-dot" />
                <span className="lp-section-label-text">Schema Discovery</span>
              </div>
              <h2>These columns weren&rsquo;t <span className="lp-gradient-text">configured.</span></h2>
              <p>The system read your documents and decided what matters. No predefined categories. No setup wizard. No schema file.</p>
              <p className="lp-deep-detail">Upload investor reports and Spindle discovers dimensions like Revenue, Reporting Period, Key Personnel — all from the content itself.</p>
            </div>
          </div>

          {/* Entity Resolution */}
          <div className="lp-deep-feature lp-deep-feature-reverse">
            <div className="lp-deep-text lp-reveal">
              <div className="lp-section-label" style={{ marginBottom: 16 }}>
                <span className="lp-section-label-dot" />
                <span className="lp-section-label-text">Entity Intelligence</span>
              </div>
              <h2>Same person. <span className="lp-gradient-text">Different name.</span></h2>
              <p>Spindle matches entities across reports by context. When it&rsquo;s not confident, it asks you to confirm.</p>
              <p className="lp-deep-detail">Full traceability: every alias, every source document, every confidence score.</p>
            </div>
            <div className="lp-deep-visual lp-reveal lp-reveal-d2">
              <div className="lp-entity-demo">
                <div className="lp-entity-group">
                  <div className="lp-entity-before-list">
                    <div className="lp-entity-name-tag">Tan Kim Bock</div>
                    <div className="lp-entity-name-tag">Bock Kim Tan</div>
                    <div className="lp-entity-name-tag">T.K. Bock</div>
                  </div>
                  <div className="lp-entity-connector">
                    <div className="lp-connector-line" />
                    <div className="lp-connector-line" />
                    <div className="lp-connector-line" />
                  </div>
                  <div className="lp-entity-canonical-card">
                    <div className="lp-canonical-label">Canonical</div>
                    <div className="lp-canonical-value">Tan Kim Bock</div>
                  </div>
                </div>
                <div className="lp-entity-confidence">
                  <div className="lp-confidence-bar">
                    <div className="lp-confidence-fill" />
                  </div>
                  <div className="lp-confidence-text">94% confidence</div>
                </div>
              </div>
            </div>
          </div>

          {/* Contradictions */}
          <div className="lp-deep-feature">
            <div className="lp-deep-visual lp-reveal">
              <div className="lp-contradiction-demo">
                <div className="lp-contradiction-card lp-contradiction-card-a">
                  <div className="lp-contra-source">Q2 Report &mdash; Aug 2025</div>
                  <div className="lp-contra-value">$4.2M</div>
                  <div className="lp-contra-badge">Most Recent</div>
                </div>
                <div className="lp-contradiction-vs">
                  <div className="lp-vs-line" />
                  <div className="lp-vs-symbol">&ne;</div>
                  <div className="lp-vs-line" />
                </div>
                <div className="lp-contradiction-card lp-contradiction-card-b">
                  <div className="lp-contra-source">Q1 Report &mdash; Jul 2025</div>
                  <div className="lp-contra-value">$3.9M</div>
                  <div className="lp-contra-badge lp-contra-badge-old">Superseded</div>
                </div>
              </div>
            </div>
            <div className="lp-deep-text lp-reveal lp-reveal-d2">
              <div className="lp-section-label" style={{ marginBottom: 16 }}>
                <span className="lp-section-label-dot" />
                <span className="lp-section-label-text">Contradictions</span>
              </div>
              <h2>It knows August <span className="lp-gradient-text">supersedes</span> July.</h2>
              <p>Revenue was $4.2M in the August report. $3.9M in July. Spindle cross-references every report and knows which is newer.</p>
              <p className="lp-deep-detail">Contradictions are surfaced as alerts, not hidden in cells. You decide what to trust — with full context.</p>
            </div>
          </div>
        </section>

        {/* Preview */}
        <section className="lp-preview-section" id="lp-preview">
          <div className="lp-container">
            <div className="lp-preview-header">
              <div className="lp-section-label lp-reveal">
                <span className="lp-section-label-dot" />
                <span className="lp-section-label-text">Preview</span>
              </div>
              <h2 className="lp-preview-title lp-reveal lp-reveal-d1">
                See it in <span className="lp-gradient-text">action</span>
              </h2>
              <p className="lp-preview-sub lp-reveal lp-reveal-d2">Three panels. Complete intelligence.</p>
            </div>

            <div className="lp-preview-frame lp-reveal lp-reveal-d3">
              <div className="lp-preview-chrome">
                <div className="lp-chrome-dots"><span /><span /><span /></div>
                <div className="lp-chrome-url">localhost:5173</div>
              </div>
              <div className="lp-preview-topbar">
                <div>
                  <span className="lp-preview-topbar-brand">Spindle</span>
                  <span className="lp-preview-topbar-subtitle">Intelligence from your reports</span>
                </div>
                <div className="lp-preview-progress">
                  <div className="lp-progress-seg" /><div className="lp-progress-seg" /><div className="lp-progress-seg" /><div className="lp-progress-seg" /><div className="lp-progress-seg" />
                </div>
              </div>
              <div className="lp-preview-app">
                {/* Left: Documents */}
                <div className="lp-prev-left">
                  <div className="lp-prev-panel-title">Documents</div>
                  <div className="lp-prev-upload">Drop files here</div>
                  {[
                    { icon: "P", name: "Q2_2025_Report.pdf", date: "Aug 25" },
                    { icon: "P", name: "Q1_2025_Report.pdf", date: "Jul 25" },
                    { icon: "W", name: "Annual_Review_2024.docx", date: "Jan 25" },
                    { icon: "P", name: "Q4_2024_Report.pdf", date: "Oct 24" },
                    { icon: "X", name: "Financial_Data_2024.xlsx", date: "Dec 24" },
                  ].map((doc) => (
                    <div className="lp-prev-doc" key={doc.name}>
                      <div className="lp-prev-doc-icon">{doc.icon}</div>
                      <span className="lp-prev-doc-name">{doc.name}</span>
                      <span className="lp-prev-doc-date">{doc.date}</span>
                      <span className="lp-prev-doc-check">&#10003;</span>
                    </div>
                  ))}
                </div>

                {/* Center: Grid */}
                <div className="lp-prev-center">
                  <div className="lp-prev-tabs">
                    <span className="lp-prev-tab active">Insights</span>
                    <span className="lp-prev-tab">Taxonomy</span>
                    <span className="lp-prev-tab">Templates</span>
                  </div>
                  <div className="lp-prev-grid">
                    <div className="lp-prev-grid-header">
                      <span>Document</span><span>Revenue</span><span>CEO</span><span>Period</span><span>Risk</span>
                    </div>
                    <div className="lp-prev-grid-row">
                      <span>Q2 2025 Report</span>
                      <span className="lp-prev-cell-red">
                        $4.2M
                        <div className="lp-cell-tooltip">
                          <div className="lp-tooltip-title">Contradiction Detected</div>
                          <div className="lp-tooltip-values">
                            <div className="lp-tooltip-val">$4.2M<small>Q2 Report, Aug</small></div>
                            <div className="lp-tooltip-val">$3.9M<small>Q1 Report, Jul</small></div>
                          </div>
                          <div className="lp-tooltip-temporal">Aug supersedes Jul &rarr;</div>
                        </div>
                      </span>
                      <span className="lp-prev-cell-amber">Tan Kim Bock</span>
                      <span>Q2 2025</span><span>Medium</span>
                    </div>
                    <div className="lp-prev-grid-row">
                      <span>Q1 2025 Report</span>
                      <span className="lp-prev-cell-red">$3.9M</span>
                      <span className="lp-prev-cell-amber">Bock Kim Tan</span>
                      <span>Q1 2025</span><span>Med-High</span>
                    </div>
                    <div className="lp-prev-grid-row">
                      <span>Annual Review 2024</span>
                      <span className="lp-prev-cell-green">$14.8M</span>
                      <span className="lp-prev-cell-green">Tan Kim Bock</span>
                      <span>FY 2024</span><span>Low</span>
                    </div>
                    <div className="lp-prev-grid-row">
                      <span>Q4 2024 Report</span><span>$3.6M</span>
                      <span className="lp-prev-cell-amber">T.K. Bock</span>
                      <span>Q4 2024</span><span>Low</span>
                    </div>
                    <div className="lp-prev-grid-row">
                      <span>Financial Data 2024</span><span>$14.8M</span>
                      <span>Tan Kim Bock</span><span>FY 2024</span><span>Low</span>
                    </div>
                  </div>
                </div>

                {/* Right: Chat */}
                <div className="lp-prev-right">
                  <div className="lp-prev-panel-title">Chat</div>
                  <div className="lp-prev-chat-messages">
                    <div className="lp-prev-chat-msg lp-prev-chat-user">How did revenue change over the last 3 reports?</div>
                    <div className="lp-prev-chat-msg lp-prev-chat-assistant">
                      Revenue increased from <strong>$3.6M</strong> (Q4 2024) to <strong>$3.9M</strong> (Q1 2025) to <strong>$4.2M</strong> (Q2 2025), representing 16.7% growth over three quarters.
                      <br />
                      <span className="lp-prev-citation">Q2 Report, p.3</span>
                      <span className="lp-prev-citation">Q1 Report, p.5</span>
                      <span className="lp-prev-citation">Q4 Report, p.4</span>
                      <br /><br />
                      <em style={{ color: "#F59E0B", fontSize: "0.625rem" }}>Note: Q2 revenue ($4.2M) contradicts Q1 ($3.9M) for the overlapping period. Q2 is more recent.</em>
                    </div>
                  </div>
                  <div className="lp-prev-chat-input">
                    <div className="lp-prev-chat-input-field lp-cursor-blink">Ask about your reports</div>
                    <div className="lp-prev-chat-send">
                      <svg viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA — Inverted */}
        <section className="lp-cta">
          <div className="lp-container" style={{ position: "relative" }}>
            <h2 className="lp-cta-title lp-reveal">
              Stop cross-referencing.<br />
              <span className="lp-gradient-text">Start knowing.</span>
            </h2>
            <p className="lp-cta-sub lp-reveal lp-reveal-d1">Your reports already have the answers. Spindle finds them.</p>
            <div className="lp-reveal lp-reveal-d2">
              <div className="lp-cta-email">
                <input className="lp-cta-input" type="email" placeholder="Enter your email" />
                <button className="lp-btn lp-btn-primary" onClick={onEnterApp} style={{ whiteSpace: "nowrap" }}>
                  Get Started <span className="lp-btn-arrow">&rarr;</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="lp-footer">
          <div className="lp-container">
            <div className="lp-footer-brand">Spindle</div>
            <p className="lp-footer-tagline">Built for analysts who&rsquo;d rather analyze than organize.</p>
          </div>
        </footer>

      </div>
    </>
  )
}
