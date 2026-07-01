# Publishing — Motifect-AI / motifect-ai-addon

**One public repo** for all DCC add-ons (Blender, Unreal, Unity):

https://github.com/Motifect-AI/motifect-ai-addon

| What | GitHub account | Repo |
|------|----------------|------|
| Web app (frontend / backend) | Your developer account | `Motifect/motifect-ai` |
| **All DCC add-ons** | Motifect-AI official | `Motifect-AI/motifect-ai-addon` |

The monorepo `addons/` folder is local dev only — never push it to `Motifect/motifect-ai`.

---

## Repo layout

```
motifect-ai-addon/
  blender/motifect_ai_motion/   ← Blender add-on
  unreal/MotifectMotion/        ← Unreal plugin
  unity/MotifectMotion/         ← Unity UPM package
  scripts/sync_all.py
```

---

## Daily workflow

### 1. Edit local sources (not in web repo git)

```
addons/blender/motifect_motion/
addons/unreal/MotifectMotion/
addons/unity/MotifectMotion/
```

### 2. Sync into this repo

```bash
cd addons/blender/motifect-ai-addon
python scripts/sync_all.py
```

Builds `blender/motifect_ai_motion.zip` (gitignored — attach to GitHub Release).

### 3. Commit & push (Motifect-AI account)

```bash
git add -A
git commit -m "Motifect Motion: ..."
git push origin main
```

SSH remote (this repo only):

```bash
git remote set-url origin git@github.com-motifect-ai:Motifect-AI/motifect-ai-addon.git
```

Use the `github.com-motifect-ai` SSH host alias so your personal GitHub credentials are untouched.  
Generate a dedicated key and add it to the Motifect-AI GitHub account — see previous Blender-only notes or GitHub SSH docs.

---

## Releases

**Blender:** attach `blender/motifect_ai_motion.zip` (run `sync_all.py` first).  
Tag examples: `v2.2.1`, `blender-v2.2.1`.

**Unreal / Unity:** users install from repo folders or Unity git URL — optional zip of `unreal/MotifectMotion` for Unreal-only release assets.

```bash
gh release create v2.3.0 blender/motifect_ai_motion.zip \
  --title "Motifect Motion 2.3.0" \
  --notes "Blender, Unreal, and Unity add-ons. Requires motifect.io API key and credits."
```

---

## Unity install URL (for README / docs)

```
https://github.com/Motifect-AI/motifect-ai-addon.git?path=/unity/MotifectMotion
```
