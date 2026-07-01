# Publishing to GitHub (Motifect-AI account)

This folder is a **standalone repo** for https://github.com/Motifect-AI/motifect-ai-addon  
It is separate from your personal dev git credentials on the monorepo machine.

## 1. Sync latest add-on code

From this directory:

```bash
python scripts/sync_addon.py
```

This copies `../motifect_motion/` → `motifect_ai_motion/` and builds `motifect_ai_motion.zip`.

## 2. Authenticate as Motifect-AI (not your personal account)

**`gh` is optional.** Plain `git` works (Options A or B below).

### Option A — HTTPS + Personal Access Token (no extra tools)

1. Browser: log into GitHub as the **Motifect-AI** account (org owner or bot user with push access).
2. **Settings → Developer settings → Personal access tokens → Tokens (classic)** → **Generate new token**.
3. Enable scope **`repo`**. Copy the token (shown once).
4. Push (section 3). When Git asks:
   - **Username:** Motifect-AI GitHub username  
   - **Password:** paste the **token** (not your GitHub password)

If Windows keeps using your personal account, open **Credential Manager → Windows Credentials** and remove `git:https://github.com` entries, then push again.

### Option B — SSH (separate key, good for long-term)

1. Generate a key used only for Motifect-AI:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_motifect_ai -C "motifect-ai-github"
```

2. Add `~/.ssh/id_ed25519_motifect_ai.pub` to the Motifect-AI GitHub account → **SSH keys**.
3. Push using SSH remote (see below) and `~/.ssh/config`:

```
Host github.com-motifect-ai
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_motifect_ai
```

Remote URL: `git@github.com-motifect-ai:Motifect-AI/motifect-ai-addon.git`

### Option C — GitHub CLI (optional)

Install: https://cli.github.com/ then `gh auth login` with the Motifect-AI account.

## 3. First push (new repo)

```bash
cd path/to/motifect-ai-addon
python scripts/sync_addon.py
git init
git add .
git commit -m "Motifect Motion Blender add-on v2.2.1"
git branch -M main
git remote add origin https://github.com/Motifect-AI/motifect-ai-addon.git
git push -u origin main
```

SSH remote instead:

```bash
git remote add origin git@github.com:Motifect-AI/motifect-ai-addon.git
```

## 4. Create a Release

**Without `gh`:** GitHub web → repo → **Releases → Draft a new release**

- Tag: `blender-v2.2.1`
- Title: `Motifect Motion 2.2.1`
- Attach file: `motifect_ai_motion.zip`

**With `gh` installed:**

```bash
gh release create blender-v2.2.1 motifect_ai_motion.zip \
  --title "Motifect Motion 2.2.1" \
  --notes "Text-to-motion for Blender. Requires motifect.io account, API key, and credits."
```

## 5. Do not mix with monorepo remote

The internal `motifect-ai` monorepo should **not** add this as its only remote.  
Keep this folder as its own git root, or clone `motifect-ai-addon` to a separate directory on your PC.
