# Filing Intelligence Design System

## 1. Visual Theme & Atmosphere

Build Filing Intelligence like an institutional research desk with boutique editorial polish.

- Mood: calm, sharp, high-trust, data-literate
- Personality: a cross between a modern equities terminal and a premium annual report
- Density: information-rich, but never cramped
- Aesthetic direction: luminous dark-navy surfaces, mineral blues, pale paper panels, restrained emerald signals
- Visual goal: make financial analysis feel precise and expensive without becoming cold

## 2. Color Palette & Roles

- `midnight` `#0B1324`
  Primary background and deepest text areas
- `slate` `#15233C`
  Elevated dark surfaces
- `paper` `#F6F4EE`
  Main light surface for readable detail panels
- `ink` `#112033`
  Primary text color on light surfaces
- `steel` `#5F7086`
  Secondary text and subdued labels
- `line` `#D5DEEA`
  Borders, table dividers, input outlines
- `cobalt` `#2D5BFF`
  Primary action and key brand accent
- `aqua` `#67D6FF`
  Supporting accent for charts, glows, and data highlights
- `emerald` `#0C8A6A`
  Positive/completed state
- `amber` `#D38A1F`
  Warning/in-progress state
- `rose` `#B94A5A`
  Error/failed state

## 3. Typography Rules

### Families

- Headings: `"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif`
- UI/body: `"Avenir Next", "Trebuchet MS", sans-serif`
- Data/mono: `"Cascadia Code", "SFMono-Regular", Consolas, monospace`

### Hierarchy

- Display: oversized serif, tight line-height, used sparingly
- Section headings: serif, medium weight, compact
- Labels: uppercase or small caps feel, wide tracking
- Body: clean sans with generous line-height
- Tables and identifiers: monospace for numbers, accession IDs, and status chips

## 4. Component Stylings

### Buttons

- Primary: cobalt fill, white text, pill radius, slight lift on hover
- Secondary: tinted paper or pale-blue fill with dark text
- Tertiary: quiet outline only, for table actions

### Cards

- Large rounded corners, layered surfaces, visible but soft shadows
- Light cards sit on dark surroundings
- Dark cards can be used for high-level overview blocks and hero statistics

### Inputs

- Light backgrounds with crisp borders
- Clear focus ring in aqua or cobalt
- Spacious touch targets

### Tables

- Alternating row treatment should be subtle, not zebra-striped
- Row hover should feel like a research tool, not a consumer app
- Important IDs use monospace

### Status pills

- Completed: emerald tint
- Running/pending: amber tint
- Failed: rose tint

## 5. Layout Principles

- Use wide breathing room around major sections
- Prefer asymmetrical layouts with one strong control column and one larger analysis column
- Group related controls into compact “command deck” panels
- Use generous vertical rhythm between sections
- Avoid full-width walls of tables without summary context

## 6. Depth & Elevation

- Background should feel atmospheric, not flat
- Use layered gradients and very subtle radial highlights
- Shadows should be soft and low-contrast
- Borders must remain visible enough to organize dense financial content

## 7. Do's and Don'ts

### Do

- Pair editorial serif headings with precise sans and mono details
- Use color to signal state, not decoration
- Make the dashboard feel intentional and trustworthy
- Let the most important numbers dominate visually

### Don't

- Don’t use generic startup purple gradients
- Don’t make everything dark; mix dark framing with lighter data surfaces
- Don’t bury controls under excessive chrome
- Don’t use playful rounded toy-like styling

## 8. Responsive Behavior

- Collapse two-column layouts into one clean stack on tablets/mobile
- Keep controls grouped at the top on mobile
- Tables must scroll horizontally instead of crushing columns
- Touch targets should remain at least 44px tall

## 9. Agent Prompt Guide

When extending the UI, preserve this feel:

- “Institutional research terminal with editorial polish”
- “Navy atmosphere, pale paper data cards, cobalt primary actions”
- “Serif headlines, clean sans body, monospace for data”
- “Dense but calm, elegant not flashy”
