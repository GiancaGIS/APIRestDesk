# APIRestDesk visual assets

The application mark uses white JSON braces around opposing cyan and teal arrows on a rounded blue tile. The editable source is `api_rest_desk/assets/app_icon.svg`.

Run `python scripts/generate_icon_assets.py` to render the PNG used by the app, the seven-resolution Windows ICO (16–256 px), and the macOS ICNS (including 1024 px and Retina elements). This conversion uses PyQt6 and Python's standard library.

The README cover is `images/readme_banner.png`. It was generated with the built-in **imagegen** tool, with an opaque background, then copied into the repository without image edits. The editable SVG icon was drawn directly to preserve the project's vector source and reliable small-size rendering.

## Banner generation prompt

```text
Use case: ads-marketing.
Asset type: wide GitHub README hero banner for APIRestDesk, a desktop REST API client.
Create a polished, visually striking software project cover in a wide landscape aspect ratio, ideally 3:1. Design it as one coherent professional illustration, with generous margins, balanced negative space, and crisp typography readable when displayed at 900 pixels wide.
Scene/backdrop: deep midnight navy (#081427) with a subtle fine technical grid and a soft cobalt-to-teal ambient gradient. Keep the background elegant and calm.
Subject: on the right, an isometric arrangement of two or three beautiful floating REST request/response interface cards, with simple white JSON curly braces, cyan and teal directional arrows, a few small connected workflow nodes, and a subtle green success indicator. Clean, softly dimensional glass-like cards with restrained light trails. This is abstract software artwork, not a screenshot of a real application.
Typography: on the left, a large, exceptionally clear, beautifully spaced sans-serif wordmark reading exactly "APIRestDesk" (A P I R e s t D e s k), in near-white. Under it, the smaller exact text "Desktop REST client". These are the ONLY words anywhere in the image. Leave ample space around the text.
Color palette: deep navy, cobalt blue (#2563eb), bright cyan (#67e8f9), teal (#5eead4), near-white. The artwork should complement a rounded blue application icon with white JSON braces and two opposing cyan/teal arrows.
Style: premium developer software branding, sophisticated editorial composition, clean geometric forms, controlled soft lighting, strong silhouette, subtle depth. Modern and inviting.
Constraints: no extra text, no lorem ipsum, no watermarks, no third-party logos, no photographs, no code paragraphs, no crowded dashboard, no neon overload. Keep all content safely inside the canvas and prioritize accurate project-name typography.
```
