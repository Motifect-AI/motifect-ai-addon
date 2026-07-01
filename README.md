# Motifect Motion — DCC Add-ons

Official add-ons for **Blender**, **Unreal Engine**, and **Unity**.  
One product, one repo — generate human motion from text via the [Motifect API](https://motifect.io).

| Platform | Folder | Install |
|----------|--------|---------|
| **Blender** | [`blender/`](blender/) | [Release zip](https://github.com/Motifect-AI/motifect-ai-addon/releases/latest) |
| **Unreal Engine** | [`unreal/`](unreal/) | Copy plugin into `YourProject/Plugins/` |
| **Unity** | [`unity/`](unity/) | Package Manager git URL (below) |

## Requirements (all platforms)

- A **[motifect.io](https://motifect.io)** account
- API key (`mk_live_...`) from **Developer → API Keys**
- **Credits** on your account (each generation consumes credits)

---

## Blender

1. Download **[motifect_ai_motion.zip](https://github.com/Motifect-AI/motifect-ai-addon/releases/latest)** from Releases.
2. Blender → **Edit → Preferences → Add-ons → Install…**
3. Enable **Motifect Motion**, set API key in preferences.
4. 3D Viewport **N** → **Motifect** → prompt → **Generate Motion**.

See [blender/README.md](blender/README.md) for troubleshooting.

---

## Unreal Engine

1. Copy [`unreal/MotifectMotion`](unreal/MotifectMotion) into `YourProject/Plugins/`.
2. Enable **Python Editor Script Plugin**, restart editor.
3. **Tools → Motifect → Open Config Folder** → set `api_key` in `config.json`.
4. **Tools → Motifect → Generate Motion**.

See [unreal/README.md](unreal/README.md) for config fields.

---

## Unity

**Package Manager → Add package from git URL:**

```
https://github.com/Motifect-AI/motifect-ai-addon.git?path=/unity/MotifectMotion
```

1. **Window → Motifect → Motion Generator**
2. API key + English prompt → **Generate Motion**
3. FBX appears in `Assets/Motifect/Generated/`.

See [unity/README.md](unity/README.md) for details.

---

## API & models

Docs: [motifect.io/docs](https://motifect.io/en/docs)

| model_key | Credits | Length |
|-----------|---------|--------|
| `motifect-v3-fast` | 8 | 2–10 s |
| `motifect-v3` | 16 | 2–10 s |
| `kimodo-human` | 20 | 2–10 s |

Prompts: English, action-focused, 10–180 characters.

---

## Development

Local sources live in the `motifect-ai` monorepo under `addons/` (not committed to the web app repo).

From this directory:

```bash
python scripts/sync_all.py
```

Syncs `blender/`, `unreal/`, and `unity/` from local dev sources and builds the Blender release zip.

---

## License

[MIT](LICENSE). Motifect API usage is subject to [motifect.io](https://motifect.io) terms.

## Links

- Website: https://motifect.io  
- Issues: https://github.com/Motifect-AI/motifect-ai-addon/issues  
