# Motifect Motion — Blender Add-on

Generate human motion from text prompts inside Blender, powered by the [Motifect API](https://motifect.io).

## Requirements

- **Blender 3.6+** (tested on 4.4)
- A **[motifect.io](https://motifect.io)** account
- An **API key** (`mk_live_...`) from **Developer → API Keys**
- **Credits** on your account (each generation consumes credits based on the model)

This add-on does not include free generations — it connects to your Motifect account over the internet.

## Quick start

1. Download **[motifect_ai_motion.zip](https://github.com/Motifect-AI/motifect-ai-addon/releases/latest)** from Releases (or build from this repo).
2. Blender → **Edit → Preferences → Add-ons → Install…** → select the zip.
3. Enable **Motifect Motion**.
4. Expand add-on preferences → paste your **API key**.
5. 3D Viewport → **N** → **Motifect** tab → enter an English prompt → **Generate Motion**.

Imported motion appears in the **Motifect** collection as an armature with FBX animation.

## Account setup

| Step | Where |
|------|--------|
| Sign up | [motifect.io](https://motifect.io) |
| API key | motifect.io → **Developer → API Keys** |
| Credits | motifect.io → billing / credits (required before generating) |
| Docs | [motifect.io/docs](https://motifect.io/en/docs) |

## Retargeting

Character retargeting in Blender is **coming soon**. Until then, use [motifect.io retarget](https://motifect.io) in the browser.

## Reinstall / troubleshooting

If install fails, quit Blender and delete:

- Windows: `%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\motifect_ai_motion`
- macOS: `~/Library/Application Support/Blender/<version>/scripts/addons/motifect_ai_motion`
- Linux: `~/.config/blender/<version>/scripts/addons/motifect_ai_motion`

Then install the zip again.

## Development

Source add-on folder: `motifect_ai_motion/`

To refresh from the internal monorepo, run from this directory:

```bash
python scripts/sync_addon.py
```

## License

See [LICENSE](LICENSE). Motifect API usage is subject to [motifect.io](https://motifect.io) terms.

## Links

- Website: https://motifect.io  
- API docs: https://motifect.io/en/docs  
- Issues: https://github.com/Motifect-AI/motifect-ai-addon/issues  
