# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-04

### Added
- Semantic Versioning (SemVer) support.
- `VERSION` file for centralized version management.
- `src/version.py` utility for retrieving version and Git SHA.
- `/version` command in LINE Bot to check current system version.
- OLED display update to show version number.
- `docs/release.md` for release procedures.
- `scripts/release.sh` for automated release handling.
- Gunicorn support for LINE Bot server.
- Hybrid Voice system (Nurse Robot + OpenAI TTS).
- Latency logging for audio operations.
- "Think-ahead" notifications for long AI processes.
- Enhanced logging in LINE Bot for troubleshooting.
- BCNOFNe branding across the system.
- Network info (LAN/Tailscale) integrated display on OLED.
