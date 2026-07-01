# Unity Asset Store — fast track

**Product:** Motifect Motion (free UPM tool)  
**Package ID:** `com.motifect.motion`  
**Unity:** 2022.3 LTS+

> Git URL alone does **not** publish to the store. You upload via **Asset Store Publishing Tools** inside Unity Editor ([Unity docs](https://docs.unity3d.com/Manual/asset-store-upm-validate.html)).

---

## Phase A — Publisher Portal (browser)

1. Open https://publisher.unity.com/
2. **Create publisher profile** (if needed) + complete identity verification.
3. **Enroll as UPM publisher** (Publisher Portal → UPM / Packages section).
4. **Create product draft**
   - Type: **Tool** (or Add-Ons / Tools)
   - Price: **Free** (paid UPM not supported on portal yet)
   - **Package technical name:** `com.motifect.motion` — must match `package.json` `"name"` exactly
   - Reserve namespace `com.motifect` if prompted

---

## Phase B — Local package in Unity (2022.3 LTS)

1. Create or open any project with **Unity 2022.3 LTS** (e.g. 2022.3.62f1).
2. Copy this folder into the project:

   ```
   YourProject/Packages/com.motifect.motion/
   ```

   Source (dev):

   ```
   addons/unity/MotifectMotion/
   ```

   Or clone from GitHub after push:

   ```
   https://github.com/Motifect-AI/motifect-ai-addon.git?path=/unity/MotifectMotion
   ```

   Then rename folder to `com.motifect.motion` under `Packages/` (folder name should match package name).

3. Wait for Package Manager to resolve `com.unity.nuget.newtonsoft-json`.
4. **Smoke test**
   - Window → Motifect → Motion Generator
   - API key + prompt → Generate Motion (needs motifect.io credits)
   - Confirm no Console errors after import

---

## Phase C — Asset Store Publishing Tools

1. Install **Asset Store Publishing Tools**  
   Window → Package Manager → Unity Registry → search `Asset Store Publishing Tools`

2. **Validate**  
   Window → Tools → Asset Store → **Validator**  
   - Type: **UPM**  
   - Fix any errors (documentation, asmdef, paths)

3. **Upload**  
   Window → Tools → Asset Store → **Uploader**  
   - Tab: **UPM Packages**  
   - Select `com.motifect.motion` → **Upload**  
   - Technical name must match Portal draft

---

## Phase D — Listing (Publisher Portal)

Paste at **top of description**:

```
FREE — no Asset Store purchase price.

Requires a motifect.io account, API key (Developer → API Keys), and paid credits per generation. Internet connection required.

This is an editor client for the Motifect cloud API (AI text-to-motion). No AI models are bundled in the package. Generated motion is downloaded as FBX into Assets/Motifect/Generated/.

Third-party: Newtonsoft.Json via com.unity.nuget.newtonsoft-json (see Third-Party Notices.txt).

Terms: https://motifect.io/terms
Docs: https://motifect.io/en/docs
Support: https://github.com/Motifect-AI/motifect-ai-addon/issues
```

**AI description field** (required):

```
Uses the Motifect cloud API for AI-based text-to-human-motion generation.
This package is a Unity Editor client only; no AI models are bundled locally.
Generated motion is downloaded as FBX and imported into the project.
```

**Media (minimum for review):**
- Icon 160×160 (JPEG)
- Card image 420×280
- Screenshots: Motion Generator window, imported FBX in Project, (optional) Animator preview
- Short video recommended

**Category:** Tools → Animation (or Add-Ons)

**Submit for approval** → review typically several days to ~2 weeks

---

## Before you upload — repo push

From monorepo:

```bash
cd addons/blender/motifect-ai-addon
python scripts/sync_all.py
git add unity/
git commit -m "Unity Asset Store prep: com.motifect.motion v1.0.1"
git push origin main
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Validator: package name mismatch | Portal draft name = `com.motifect.motion` = `package.json` name |
| Newtonsoft missing | Package Manager → resolve dependencies |
| Path too long (Windows) | Project near `C:\dev\motifect-test\` |
| Paid price greyed out | Free only for UPM on portal — correct for us |

---

## Optional later

- [Verified Solutions](https://unity.com/partners/verified-solutions) inquiry (SaaS SDK)
- Update version in `package.json` → re-validate → upload new version
