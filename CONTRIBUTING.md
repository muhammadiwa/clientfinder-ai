# Contributing & Git Workflow

> Catatan singkat biar kerjaan tetap rapi dan gak ganggu `main`.

## Branch Strategy

Kita pakai **Gitflow-lite** untuk project ini:

```
main              ← production-ready code only (protected)
  │
  └─ develop     ← integration branch
       │
       ├─ feature/<name>   ← per-module kerja
       ├─ feature/<name>
       └─ ...
```

### Aturan
- ❌ **JANGAN** commit langsung ke `main` atau `develop`
- ✅ Selalu kerja di branch `feature/<nama-phase>` atau `fix/<nama-bug>`
- ✅ Merge ke `develop` setelah phase selesai & tested
- ✅ `develop` di-promote ke `main` saat release-ready (via PR)
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
git merge --no-ff develop
git tag -a v0.2.0 -m "Release: T2 backend core"
git push origin main --tags
```

## Protected Branches (Recommended di GitHub)

Set di GitHub Settings → Branches:
- `main`: require PR review, no direct push
- `develop`: require PR atau admin only

## Tools Pendukung

- **Pre-commit hook** (opsional): auto-run lint sebelum commit
- **Conventional Commits linter**: enforce format
- **Branch name validator**: warn kalau nama不符合 pattern

Akan di-setup di T8 (production hardening).

---

Happy committing! 🚀
