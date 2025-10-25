# Cloudflare Workers - Deployment Setup

This directory contains Cloudflare Workers that are automatically deployed via GitHub Actions.

## Structure

Each worker lives in its own subdirectory with:
- `worker.js` - The worker code
- `wrangler.toml` - Configuration file

## Current Workers

### github-auth
- **Worker Name**: `winter-cherry-2261`
- **Location**: `cloudflare-workers/github-auth/`
- **Purpose**: GitHub OAuth authentication flow
- **Dashboard**: https://dash.cloudflare.com/6f057ad2bb65bccc304820611c01dae5/workers/services/view/winter-cherry-2261/production

## Setup Instructions

### 1. Install Wrangler CLI (Optional - for local development)

```bash
npm install -g wrangler
```

### 2. Configure GitHub Secrets

Add these secrets to your GitHub repository at Settings → Secrets and variables → Actions:

- `CLOUDFLARE_API_TOKEN` - Create at https://dash.cloudflare.com/profile/api-tokens
  - Use the "Edit Cloudflare Workers" template
  - Or create custom token with these permissions:
    - Account > Workers Scripts > Edit
    - Account > Account Settings > Read

- `CLOUDFLARE_ACCOUNT_ID` - Your account ID: `6f057ad2bb65bccc304820611c01dae5`

### 3. Configure Worker Environment Variables

The github-auth worker requires these environment variables (secrets):

```bash
# Set these in Cloudflare Dashboard or via Wrangler CLI
wrangler secret put GITHUB_CLIENT_ID --env production
wrangler secret put GITHUB_CLIENT_SECRET --env production
wrangler secret put GITHUB_REDIRECT_URI --env production
```

Or set them in the Cloudflare Dashboard:
https://dash.cloudflare.com/6f057ad2bb65bccc304820611c01dae5/workers/services/view/winter-cherry-2261/production/settings/variables

## Automatic Deployment

The GitHub Actions workflow (`.github/workflows/deploy-cloudflare-workers.yml`) will automatically deploy workers when:

1. Changes are pushed to the `main` branch
2. Files in `cloudflare-workers/**` are modified
3. The workflow is manually triggered

Each worker is deployed independently - only workers with changed files are deployed.

## Manual Deployment

To deploy manually from your local machine:

```bash
cd cloudflare-workers/github-auth
wrangler deploy --env production
```

You'll need to authenticate with Wrangler first:
```bash
wrangler login
```

## Adding New Workers

To add a new worker to this monorepo:

1. Create a new directory: `cloudflare-workers/your-worker-name/`
2. Add your worker code as `worker.js`
3. Create a `wrangler.toml` configuration (copy from github-auth as template)
4. Add a new job to `.github/workflows/deploy-cloudflare-workers.yml` (see commented example)
5. Push to main branch

## Local Development

To test a worker locally:

```bash
cd cloudflare-workers/your-worker-name
wrangler dev
```

This starts a local server at http://localhost:8787

## Troubleshooting

### Deployment fails in GitHub Actions
- Check that secrets are properly configured
- Verify the worker name in `wrangler.toml` matches your Cloudflare worker
- Check the Actions logs for specific error messages

### "Unauthorized" errors
- Regenerate your CLOUDFLARE_API_TOKEN with correct permissions
- Ensure the token hasn't expired

### Worker not updating
- Check the GitHub Actions logs to see if deployment ran
- Verify the file path filter in the workflow matches your changed files
- Try manually triggering the workflow
