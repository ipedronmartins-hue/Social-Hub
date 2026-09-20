# Social Hub Cloud

Independent cloud project for the Nokia Lumia 830 / Windows Phone 8.1.

This project is intentionally independent from YTB/Sentinel and Beast Mode.

## Goal

Make the Lumia 830 useful again by serving old-IE-compatible HTML from cloud infrastructure.

Initial proof of concept:

Lumia 830 → compatible HTTPS endpoint → simple HTML

Later:

Lumia 830 → gateway → Social Hub renderer → feeds/APIs

## Design principles

- No home PC required.
- No desktop login required.
- No modern JavaScript required on the Lumia.
- Keep the Lumia-facing pages simple HTML/CSS.
- Keep Social Hub data isolated from YTB and Beast Mode.
- Do not expose Supabase service-role credentials to the client.
- Do not weaken TLS below TLS 1.2.

## Current blocker

The Lumia can reach HTTP, but the current Vercel edge endpoint fails during HTTPS negotiation on Windows Phone 8.1 IE11.

The next experiment is to find a free cloud endpoint/gateway that can accept the TLS 1.2 cipher suites supported by the Lumia.

Only after the TLS endpoint works will we add Reddit, YouTube, news and other feeds.
