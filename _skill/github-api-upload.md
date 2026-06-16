# GitHub API Upload via Python (GFW-safe)

When `git push` is blocked by GFW (github.com:443 unreachable), use the GitHub Contents API via Python's `urllib`. `api.github.com` is reachable from China.

## Prerequisites

- `gh auth login` must have been run (token in keyring)
- Token scopes need `repo` access

## Upload Script Template

```python
import subprocess, json, base64, urllib.request, urllib.parse, time

token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
owner = "yushengchen519-cmd"
repo = "stall-replenishment-tool"

def api_call(url, method="GET", body=None):
    """GitHub API call with GFW retry."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=body, method=method)
            req.add_header("Authorization", f"Bearer {token}")
            req.add_header("Accept", "application/vnd.github+json")
            if body:
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except:
            if attempt < 2: time.sleep(2)
            else: raise

def upload_file(filepath, filename, message):
    """Upload a single file to GitHub repo."""
    encoded = urllib.parse.quote(filename)  # MUST encode Chinese filenames

    # Get SHA if file exists
    sha = None
    try:
        resp = api_call(f"https://api.github.com/repos/{owner}/{repo}/contents/{encoded}?ref=master")
        sha = json.loads(resp).get("sha")
    except: pass

    # Read and encode
    with open(filepath, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    body = {"message": message, "content": content, "branch": "master"}
    if sha:
        body["sha"] = sha

    api_call(
        f"https://api.github.com/repos/{owner}/{repo}/contents/{encoded}",
        method="PUT",
        body=json.dumps(body).encode()
    )
    print(f"Uploaded: {filename}")
```

## Common Pitfalls

1. **Chinese filename → UnicodeEncodeError**: Always `urllib.parse.quote()` the filename in the URL
2. **SSL EOF errors**: GFW interference causes `[SSL: UNEXPECTED_EOF_WHILE_READING]`. 3-retry loop handles this.
3. **SHA required for updates**: Must fetch existing file SHA before PUT, otherwise 409 Conflict
4. **Large files may timeout**: ~50KB HTML files work; larger files may need chunked upload or increased timeout
