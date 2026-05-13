# CHANGELOG

All notable changes to the companion repository are documented here.
Format: [Date] — [Change description] — [Affected files]

## 2026-04-25 — Initial release
- Repository initialized with all chapter code from Revised Edition 2026
- Pinned requirements: anthropic==0.49.0, openai==1.30.0
- CI pipeline added for automated example testing
- All Chapter 5–21 worked examples verified against April 2026 model versions

## Notes for future updates
- When Anthropic releases a new SDK version with breaking changes, update
  `requirements.txt` and add an entry here with affected chapter files
- Model version pins (e.g., `claude-sonnet-4-6-20250514`) should be updated
  when the pinned version is deprecated by Anthropic
