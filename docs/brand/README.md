# RAVAGE brand guide · v1.0

25 October 2026. The custom motorsport wordmark is approved. The standalone V is a proposed companion icon awaiting approval. Colors, typography and rules below are the proposed brand system. This package does not apply a theme to the game or website.

[Visual guide](index.html) · [CSS tokens](tokens.css) · [JSON tokens](tokens.json)

## Brand idea

Competitive precision. RAVAGE should feel like a sport: fast, controlled and confident. Use strong silhouettes, generous space and direct language. Avoid medieval decoration, distressed metal, mascot shields and excessive neon.

## Identity

Use assets/ravage-wordmark-approved.png as the approved appearance reference. Use assets/ravage-icon-concept.png for the proposed square icon. These are generated raster artworks with black backgrounds, not transparent or production vector masters. Earlier Jaro, Cinzel, Chakra and gothic explorations are not brand logos. Never recreate the custom wordmark by typing the name in a font.

Before shipping, redraw the approved shapes as vector paths, reconcile curves and spacing, optically align the V, and export transparent light/dark SVG and PNG masters plus platform icons. Review those masters against this reference. Do not automatically trace and call the result approved. Current artwork uses a near-white appearance; normalize it to Ivory during vector production.

Clear space: at least half the visible wordmark cap height on all sides; one quarter of the visible V height for the icon. These measurements exclude image canvas margins. Proposed minimum visible widths: wordmark 160 CSS px / 30 mm print; icon 24 CSS px / 6 mm print. Check native-resolution exports at 16, 24, 32 and 48 px before release. Below 160 px use the icon. For square platform icons, fit the symbol inside the central 64% safe region and test platform masks; do not bake rounded corners into the artwork.

Primary lockup: ivory on Carbon. Future reverse master: Carbon on ivory. One-color marks only. Red is an interface accent, not a default logo recolor. No stretching, rotation, outlines, effects, independent letter recoloring or improvised cuts. Preserve the wordmark's wide proportions. Do not use the black-backed reference on a light surface as if it were transparent.

## Palette

| Token | Hex | Role |
|---|---|---|
| black | #080A0D | Carbon / main background |
| surface | #14181E | Graphite / panels |
| raised | #202630 | Steel / elevated surfaces |
| border | #647080 | Functional borders / control boundaries |
| ivory | #F5F1E8 | Ivory / primary text and future logo masters |
| muted | #A5AFBD | Secondary text |
| red | #F04438 | Race red / primary action and error |
| red-hover | #FF655A | Action hover |
| cyan | #55D9F5 | Keyboard focus and links |
| success | #73D49B | Success state |
| warning | #F4C35A | Warning state |

Aim for 80% dark neutrals, 15% ivory and 5% accent in branded compositions; this is a visual balance, not a required pixel count. Use red on one main action per surface. Keep large backgrounds neutral. Marketing can use more red in a deliberate feature area.

Use Carbon text on Race Red buttons. Ivory text on Race Red does not meet 4.5:1 for normal text. Ivory and muted text work on all three dark surfaces. Cyan links are underlined in body copy. Use the border token for essential control outlines; decorative dividers may be subtler. Always check the final composite, opacity and image background. Target WCAG 2.2 AA contrast: 4.5:1 normal text, 3:1 large text and essential non-text UI. Focus uses a 2 px cyan outline with 3 px offset and must remain visible on every surface.

## Typography

The logo is custom artwork. Supporting display: Chakra Petch Bold Italic (700), uppercase, for short marketing headlines and major game screen titles. Body and controls: Barlow Regular (400) and SemiBold (600). Use system monospace for console, debug output and technical data. Font files and OFL licenses are included under assets/. Website/game support for these fonts still needs implementation.

Suggested desktop scale: display 64/64, H1 48/52, H2 32/36, H3 24/28, body 16/24, labels 14/20, metadata 12/16 px. On small screens use display 40/42 and H1 32/36. Prefer sentence case for readable UI; short navigation labels can be uppercase. Do not italicize body text or long instructions. Use tabular numerals where supported for timers and scores; verify glyph widths in the chosen runtime.

## UI and layout

Use a 4 px spacing grid: 4, 8, 12, 16, 24, 32, 48, 64, 96. Keep controls at least 44 px high as the default touch target. Controls have 4 px corner radii; panels 8 px. Use crisp flat panels, restrained 1 px borders and ample space. An occasional diagonal crop can echo the wordmark in marketing; never crop button labels or important data.

Buttons: red fill / Carbon text for primary, transparent fill / Ivory text / functional border for secondary. Disabled controls use a visible disabled label or unavailable explanation where relevant. Keep focus distinct from selection. Selection uses a red bar plus label or checkmark; error uses an icon and explicit message. Success and warnings always include text or a symbol. Do not rely on hue alone.

Motion: short 120-180 ms fades or small translations for UI, no continuous pulsing. Honor reduced-motion preferences. Avoid flashing transitions and moving HUD decoration.

## Game and competitive clarity

Brand colors style shells, menus, loading screens and broadcast surfaces. Existing Bone Circuit gameplay identifiers remain authoritative: shells orange, bullets amber, rockets red, grenades green, lightning white, rail cyan. Health and armor tiers keep their documented identifiers. See ../art/bone-circuit/README.md. Do not recolor these families to fit the brand palette.

Team colors, enemy/friendly identification and accessibility palettes need dedicated validation. Brand red must not silently mean enemy. Reserve the brightest HUD treatment for actionable information; keep reticles, damage cues, scores and timers legible over real maps. Use labels, shapes and icons alongside color. Test combat readability and user-configurable HUD colors in game before adopting defaults.

## Applications

Game: ivory wordmark on Carbon loading/title screens, Graphite menus, red Play action, cyan keyboard focus. During play, prioritize gameplay semantics over brand decoration.

Website: a quiet dark canvas, custom wordmark in the header, one red primary CTA, Barlow for readable copy, short Chakra display headlines. Avoid giant decorative marks behind text.

Repository: use the approved wordmark on a dark README banner and eventually the production V icon for the project avatar. Keep documentation mostly native Markdown; use standard code formatting and meaningful status labels. Do not embed the full web theme into docs. Add a link to this guide wherever contributors are directed to brand assets.

Broadcast/social: use the wordmark in wide layouts, V in square avatars, neutral score panels, and separate team colors. Leave platform-specific safe areas. Export in sRGB; use actual pixels at small sizes rather than judging a scaled preview.

## Voice

Short, direct, competitive. Say “Find a match”, “Ready to play”, “Connection lost. Reconnecting…” and “Victory”. Avoid military roleplay, exaggerated claims and hostile error copy. Use RAVAGE uppercase as the brand name and lowercase ravage for command names and repository identifiers.

## Handoff and maintenance

Use tokens.json as the shared source of values and tokens.css as the web-ready equivalent. Native game consumers should map semantic roles to those values in their own UI layer; these files are not automatically wired into the engine. Update both files and this guide together. Keep gameplay color tokens separate from brand tokens. Do not claim the brand theme is implemented until runtime surfaces have been checked.

Release checklist: approve the V and palette; create and review vector masters; export transparent assets and platform icon sizes; check light/dark backgrounds and masks; check contrast and keyboard focus; inspect HUD over real maps; verify font attribution and packaging. No build, deployment or existing game assets were changed by this guide.

Sources: approved artwork from this design session; existing Bone Circuit art reference; Google Fonts Chakra Petch and Barlow, bundled with their SIL Open Font License text. Contrast ratios in the visual guide are calculated from the specified sRGB values, not screenshots.

## Retro title treatment exploration

[Wordmark and icon treatment](assets/ravage-retro-treatment-v1.png): a proposed 1990s arena-shooter finish using worn warm steel and shallow bevels, retaining the established silhouette. This is an unapproved raster exploration for large title and promotional applications. It is an exception to the flat-mark rules only when approved as a separate treatment. Keep flat masters for interface and small-icon use.
