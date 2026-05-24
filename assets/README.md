# Brand assets

| File | Purpose | Notes |
|---|---|---|
| `banner.svg` | Social preview / OpenGraph image | 1280 × 640. Upload via *Settings → Social preview* on GitHub. |
| `logo.svg`   | Square logo for README, favicons | 200 × 200, scales cleanly. |

To regenerate a PNG of the banner (for Twitter/X cards, etc.):

```bash
# Linux/macOS — needs `rsvg-convert` or `inkscape`
rsvg-convert -w 1280 assets/banner.svg -o assets/banner.png
```
