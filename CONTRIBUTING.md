# Contributing & Git Workflow

> Catatan singkat biar kerjaan tetap rapi dan gak ganggu `main`.

## ⚠️ ATURAN KRITIS: Target PR SELALU `develop`

```
✅ PR → develop
❌ PR → main    ← JANGAN, kecuali ini PR release
```

**Semua PR dari branch `feature/*` HARUS target `develop`, BUKAN `main`.**
- `develop` = integration branch (semua kerjaan baru masuk sini dulu)
- `main` = production-ready code only
- `main` di-update HANYA via PR dari `develop` saat release-ready

> 📌 **Historical note:** PR #5 dan #6 (Jun 2026) accidentally merged ke main, langsung di-revert + dipindah ke develop. Workflow ini enforced dengan warning ini dan akan ditambah branch protection di GitHub (T8).

## Branch Strategy

Kita pakai **Gitflow-lite** untuk project ini:

```
main              ← production-ready code only (PROTECTED)
  │
  └─ develop     ← integration branch (semua PR target sini)
       │
       ├─ feature/<name>   ← per-module kerja
       ├─ feature/<name>
       └─ ...
```

### Aturan
- ❌ **JANGAN** commit langsung ke `main` atau `develop`
- ❌ **JANGAN** bikin PR dari `feature/*` ke `main` (harus ke `develop`)
- ✅ Selalu kerja di branch `feature/<nama-phase>` atau `fix/<nama-bug>`
- ✅ PR dari `feature/*` SELALU target `develop`
- ✅ Merge ke `main` HANYA via PR dari `develop` setelah semua phase di phase itu selesai & tested
- ✅ Commit message pakai **Conventional Commits**

## Naming Branch

```
feature/t2-backend-core
feature/t3-frontend-core
feature/t4-scout-module
feature/t5-analyst-module
feature/t6-outreach-module
feature/t7-analytics
feature/t8-hardening
fix/login-bug
fix/celery-task-crash
chore/update-deps
docs/api-reference
```

## Commit Message Format

Gunakan [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body (optional)>

<footer (optional)>
```

### Types
- `feat` — fitur baru
- `fix` — bug fix
- `docs` — dokumentasi
- `style` — formatting (no code change)
- `refactor` — code change yang bukan feat/fix
- `test` — tambah/fix test
- `chore` — maintenance (deps, config, dll)
- `perf` — performance improvement

### Scopes (per phase)
- `T1-infra`, `T2-backend`, `T3-frontend`, `T4-scout`, `T5-analyst`, `T6-outreach`, `T7-analytics`, `T8-harden`

### Examples
```
feat(T2-backend): add JWT auth with refresh token rotation
fix(T4-scout): handle SearXNG rate limit on Google engine
docs: update API reference for /api/v1/prospects
chore(T1-infra): bump postgres to 16.4-alpine
```

## Workflow Harian

```bash
# 1. Update develop
git checkout develop
git pull origin develop

# 2. Buat branch baru
git checkout -b feature/t2-user-model

# 3. Kerja, commit sering
git add backend/app/models/user.py
git commit -m "feat(T2-backend): add User SQLAlchemy model"

git add backend/app/api/v1/auth.py
git commit -m "feat(T2-backend): add /auth/login endpoint"

# 4. Push branch
git push -u origin feature/t2-user-model

# 5. Buat PR ke develop di GitHub
# ⚠️ PASTIKAN base branch = develop, BUKAN main!

# 6. Setelah merge, balik ke develop & cleanup
git checkout develop
git pull origin develop
git branch -d feature/t2-user-model
```

## Release ke main

```bash
# Dari develop, siap release
git checkout develop
git pull origin develop

# Pastikan semua tested
make test
make lint
make health

# Merge ke main via PR
# (atau langsung jika solo & tested)
git checkout main
git merge --ff-only develop
git tag -a v0.2.0 -m "Release: T2 backend core"
git push origin main --tags
```

## Protected Branches (Recommended di GitHub)

Set di GitHub Settings → Branches:
- `main`: require PR review, no direct push
- `develop`: require PR atau admin only

Akan di-setup di T8 (production hardening).

---

Happy committing! 🚀
