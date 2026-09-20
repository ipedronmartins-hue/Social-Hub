# Social Hub — Lumia TLS Gateway

This folder contains the cloud gateway needed because the Lumia 830 running Windows Phone 8.1 cannot negotiate the current Vercel TLS configuration.

## Architecture

Lumia 830 / IE11
→ HTTPS TLS 1.2 compatible gateway
→ modern HTTPS
→ Vercel Social Hub

The gateway is cloud-hosted. No home PC needs to remain powered on or logged in.

## Required infrastructure

- A small Linux VPS with a public IPv4 address
- A domain or subdomain pointing to that VPS
- Nginx with OpenSSL
- A publicly trusted RSA certificate, preferably Let's Encrypt
- Ports 80 and 443 open

## TLS compatibility

The gateway deliberately accepts TLS 1.2 with ECDHE-RSA-AES128-SHA256 and ECDHE-RSA-AES128-SHA.
TLS 1.0 and TLS 1.1 are not enabled.

The upstream connection remains modern TLS to Vercel.

## Certificate

Use a public CA certificate for the gateway domain. Do not use a self-signed certificate for the Lumia.

The exact certificate chain matters for old clients, so after deployment we must test the real endpoint from the Lumia.

## Next step

1. Point the DNS A record at the VPS.
2. Obtain the certificate.
3. Replace socialhub.example.com in nginx.conf.
4. Start or reload Nginx.
5. Open the gateway URL on the Lumia.
6. Only after the TLS test succeeds, connect the gateway to the real Social Hub feeds and Supabase backend.

Do not put Supabase service-role keys in the Lumia-facing HTML or JavaScript.