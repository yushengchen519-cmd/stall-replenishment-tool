# GitHub CLI File Upload (bypass GFW)

## Working Pattern (for 50KB+ files)

```bash
cd /path/to/workdir

# 1. Get current file SHA
SHA=$(gh api repos/OWNER/REPO/contents/FILENAME --jq '.sha')

# 2. Base64-encode without line wrapping
B64=$(base64 -w0 FILENAME)

# 3. Write JSON body to temp file (NOT inline — "Argument list too long" above ~10KB)
echo "{\"message\":\"commit msg\",\"content\":\"$B64\",\"sha\":\"$SHA\",\"branch\":\"master\"}" > /tmp/gh_body.json

# 4. Upload via --input (avoids argument size limits)
gh api --method PUT repos/OWNER/REPO/contents/FILENAME --input /tmp/gh_body.json --jq '.commit.message'
```

## Branch Detection

```bash
# Check which branch to use
gh api repos/OWNER/REPO --jq '.default_branch'
# → usually 'master' for older repos, 'main' for newer ones
```

## Pages Build Verification

```bash
# Check latest build status
gh api repos/OWNER/REPO/pages/builds/latest --jq '{status, commit: .commit[:8]}'

# Check Pages config
gh api repos/OWNER/REPO/pages --jq '{source: .source.branch, build_type}'
```

## CDN Cache Issue

GitHub Pages CDN can serve stale content even after build completes ("built"). Solutions:
- Add `?v=N` cache-busting param
- Wait 15-30s after upload, then retry
- Download to temp file: `curl -s "$URL" -o /tmp/page.html` then inspect locally
- Do NOT use piped grep (`curl | grep`) — sequential requests may hit different CDN nodes
