---
name: RegImpact AI
colors:
  surface: '#fcf8ff'
  surface-dim: '#dad7f3'
  surface-bright: '#fcf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f2ff'
  surface-container: '#efecff'
  surface-container-high: '#e8e5ff'
  surface-container-highest: '#e2e0fc'
  on-surface: '#1a1a2e'
  on-surface-variant: '#43474e'
  inverse-surface: '#2f2e43'
  inverse-on-surface: '#f2efff'
  outline: '#74777f'
  outline-variant: '#c4c6cf'
  surface-tint: '#455f87'
  primary: '#022448'
  on-primary: '#ffffff'
  primary-container: '#1e3a5f'
  on-primary-container: '#8aa4cf'
  inverse-primary: '#adc8f5'
  secondary: '#0051d5'
  on-secondary: '#ffffff'
  secondary-container: '#316bf3'
  on-secondary-container: '#fefcff'
  tertiary: '#341f00'
  on-tertiary: '#ffffff'
  tertiary-container: '#503300'
  on-tertiary-container: '#c69b5f'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d5e3ff'
  primary-fixed-dim: '#adc8f5'
  on-primary-fixed: '#001c3b'
  on-primary-fixed-variant: '#2d486d'
  secondary-fixed: '#dbe1ff'
  secondary-fixed-dim: '#b4c5ff'
  on-secondary-fixed: '#00174b'
  on-secondary-fixed-variant: '#003ea8'
  tertiary-fixed: '#ffddb2'
  tertiary-fixed-dim: '#edbf7f'
  on-tertiary-fixed: '#291800'
  on-tertiary-fixed-variant: '#60410c'
  background: '#fcf8ff'
  on-background: '#1a1a2e'
  surface-variant: '#e2e0fc'
typography:
  h1:
    fontFamily: Noto Sans
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.02em
  h2:
    fontFamily: Noto Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  h3:
    fontFamily: Noto Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Noto Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Noto Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Noto Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  mono-label:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  mono-data:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-padding: 24px
  gutter: 16px
  component-gap-sm: 8px
  component-gap-md: 12px
  section-margin: 32px
---

## Brand & Style
The design system is engineered for high-stakes regulatory environments where clarity, traceability, and speed of decision-making are paramount. The aesthetic is **Corporate / Modern** with a focus on high-density information architecture. It avoids decorative elements in favor of functional precision.

The visual language communicates institutional stability and technological rigor. It utilizes a structured hierarchy to help compliance officers navigate complex datasets without cognitive overload. The interface should feel like a precision instrument—stable, predictable, and transparent.

## Colors
The palette is anchored by "Institutional Navy" to evoke trust and authority. 

- **Primary & Action:** Use `#1E3A5F` for primary navigation and core branding. Use `#2563EB` for interactive elements like links and primary buttons to ensure visibility against the deep navy.
- **Surface & Background:** The background uses a cool gray to reduce screen glare during long auditing sessions. Surfaces (cards, panels) are pure white with distinct borders.
- **Status System:** Highly semantic. Success, Warning, High-Risk, and Info colors must maintain a contrast ratio of at least 4.5:1 against surface colors.
- **Dark Mode:** When inverted, the background shifts to a deep slate (#0F172A), surfaces to #1E293B, and borders to #334155. Primary Navy should lighten slightly to maintain depth perception.

## Typography
This design system utilizes **Noto Sans** for its universal legibility and neutral tone, essential for cross-border fintech applications. 

- **Technical Data:** Use **JetBrains Mono** for all non-prose data points: Document IDs, Policy Citations, Blockchain Hashes, and Transaction Codes. This differentiation allows users to instantly distinguish between descriptive text and unique identifiers.
- **Hierarchy:** Headlines are kept compact to maximize vertical space. 
- **Density:** Body-md (14px) is the standard for dashboard content. Body-sm (12px) is reserved for secondary metadata and table headers.

## Layout & Spacing
The layout follows a **Fixed-Fluid Hybrid** model. Navigation and sidebars are fixed-width to maintain tool accessibility, while the central data workspace is fluid to accommodate wide tables.

- **Grid:** A 12-column system is used for dashboard layouts. In high-density views, use 8px and 16px increments for internal component spacing.
- **Density:** High. Margins between data cells should be minimized (8-12px) to allow for maximum information visibility without scrolling.
- **Breakpoints:**
  - Desktop: 1440px+ (Standard workspace)
  - Laptop: 1024px (Condensed sidebars)
  - Tablet: 768px (Sidebar collapses to icons)

## Elevation & Depth
Depth is conveyed primarily through **Tonal Layers** and **Low-Contrast Outlines** rather than heavy shadows.

- **Level 0 (Background):** #F7F8FA. The canvas.
- **Level 1 (Cards/Panels):** White surface with a 1px #E5E7EB border. No shadow.
- **Level 2 (Modals/Popovers):** White surface with a 1px #E5E7EB border and a subtle, crisp ambient shadow (0px 4px 12px rgba(0,0,0,0.08)).
- **Active State:** Elements being dragged or interacted with use a 2px primary color border or a subtle blue tint (#EFF6FF) background.

## Shapes
The shape language is **Soft** but conservative. 
- **Standard (4px):** Used for buttons, input fields, and small cards. 
- **Large (8px):** Used for main container panels.
- **Pill:** Reserved exclusively for status badges and tags to distinguish them from interactive buttons.

## Components
- **Data Tables:** Use zebra-striping (1px solid #F3F4F6) for row separation. Headers are sticky with a background of #F9FAFB. Text should be 14px Noto Sans, while IDs within the table use 13px JetBrains Mono.
- **Evidence Citation Chips:** Small (20px height) tags with a light gray background (#F3F4F6) and dark gray text. Use monospaced font for the citation ID.
- **Status Badges:** Combinations of a small 8px "dot" icon + text. Colors must strictly follow the Status Palette (e.g., High-Risk uses Red #B42318 text on a #FEF2F2 background).
- **Phase Timeline:** A vertical or horizontal stepped indicator using 24px circles. Completed phases are Primary Navy; Active is Blue; Future is Gray.
- **Input Fields:** 1px solid borders (#D1D5DB). On focus, the border changes to Primary Navy with a 2px light blue outer glow.
- **Scenario Selector:** A persistent dropdown in the top app bar with a distinctive "Target" icon, allowing users to switch between different regulatory environments (e.g., GDPR vs. FINRA).