# HackUMBC Auth Starter (Nuxt 4)

Simple Nuxt + Vue auth starter with Supabase and route middleware that mirrors the authorization behavior from the source app.

## Setup

1. Copy `.env.example` to `.env` and fill in your Supabase values.
2. Install dependencies:

```bash
npm install
```

3. Start dev server:

```bash
npm run dev
```

## Scripts

```bash
npm run dev
npm run build
npm run preview
npm run typecheck
```

## Auth Behavior

- Public routes include:
	- `/auth/sign-in`
	- `/auth/sign-up` (disabled and redirects to sign-in)
	- `/auth/forgot-password`
	- `/auth/reset-password`
	- `/auth/invite`
	- `/auth/pending-approval`
	- `/auth/deactivated`
	- `/public/surveys`
- All other routes require a valid session.
- Global middleware checks `user_profile.status` and redirects:
	- `deactivated` -> `/auth/deactivated`
	- `pending` -> `/auth/pending-approval`
- Platform super admins (RPC: `is_super_admin`) bypass tenant membership.
- Users with approved tenant membership are allowed through.
- Additional route middleware is available for admin/platform-role pages.
