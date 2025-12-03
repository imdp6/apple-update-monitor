# AI Coding Agent Instructions for apple-update-monitor

## Project Overview
This is a Python-based Apple Developer update monitor that polls the Apple RSS feed, detects new releases, and sends notifications via Bark push service. It runs automatically via GitHub Actions on every push to main.

## Architecture & Data Flow
- **Entry Point**: `check_update.py` - Single-file application with no external modules
- **Data Source**: Apple Developer RSS feed (`https://developer.apple.com/news/releases/rss/releases.rss`)
- **State Management**: `last_update_id.txt` - Persists the ID of the last processed update to prevent duplicates
- **Notification**: Bark API (`https://api.day.app/{BARK_KEY}/`) for push notifications
- **Execution**: GitHub Actions workflow triggered on every push to main branch

## Key Workflows & Commands
- **Local Testing**: `python check_update.py` (requires `BARK_KEY` environment variable)
- **Dependencies**: Install with `pip install feedparser requests`
- **GitHub Deployment**: Changes pushed to main automatically trigger the workflow in `.github/workflows/check_update.yml`

## Critical Patterns & Conventions

### RSS Feed Retry Logic
The `fetch_rss_with_retry()` function implements resilient polling:
- Retries 6 times by default with 10-second delays between attempts
- Returns None if all attempts fail (not an exception)
- Called with configurable `retries` and `delay` parameters
- **Important**: Always check if feed is None before processing entries

### State Persistence Strategy
- ID-based deduplication: Uses `item.get("id")` with `item.get("link")` as fallback
- Stores latest ID in `last_update_id.txt` AFTER successful notification loop
- GitHub Actions auto-commits changes to track state across runs
- Critical: Only save ID if processing succeeds to maintain recovery ability

### Notification Batching
- Processes new items in chronological order (reversed: `new_items[::-1]`)
- Sends notifications oldest-first for logical ordering
- Skips notification if Bark request fails (no error handling currently)
- Uses URL parameters: `?url={link}&group=AppleUpdate` for grouping

### Environment & Secrets
- `BARK_KEY` is required - passed via GitHub secrets
- Local development: Set `BARK_KEY` in shell environment before running
- No other configuration files needed

## Integration Points
- **External APIs**: 
  - Apple RSS: No authentication needed, but may rate-limit
  - Bark API: Requires `BARK_KEY` secret in GitHub repo settings
- **Git Integration**: Automatic commit/push by workflow to persist state
- **Python Dependencies**: feedparser (RSS parsing), requests (HTTP)

## Common Modifications
- **Change monitoring frequency**: Edit `on:` trigger in `.github/workflows/check_update.yml` (currently: every push to main)
- **Add notification filtering**: Filter `new_items` before push loop (e.g., by title regex)
- **Store more metadata**: Extend `last_update_id.txt` to JSON format with timestamps
- **Multiple notification channels**: Add conditional logic in the notification loop

## Testing & Debugging
- Test RSS parsing: `feedparser.parse(RSS_URL)` returns feed object with `.entries` list
- Verify state file: Check `last_update_id.txt` after running (should contain latest item ID/link)
- Debug Bark requests: Print response status code (currently done, check workflow logs)
- Dry-run mode: Modify workflow to run on PR or manual trigger via `workflow_dispatch`
