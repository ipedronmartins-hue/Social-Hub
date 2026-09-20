# Social Hub — Cloudflare Worker prototype

This is an independent proxy for the Social Hub Vercel deployment.

Purpose:
- give the Lumia a Cloudflare edge endpoint to test;
- keep the Vercel deployment unchanged;
- proxy requests from the Worker to Vercel over modern HTTPS.

Cloudflare provides a free workers.dev hostname for Workers accounts. The Free plan currently includes Workers with usage limits, so this is suitable for a hobby proof of concept.

Important: this prototype does not guarantee Windows Phone 8.1 compatibility. The decisive test is opening the resulting workers.dev URL on the Lumia.

Deployment can be done from Cloudflare's dashboard or with Wrangler.

After deployment, test:
https://<your-worker>.<your-account>.workers.dev/

Do not put secrets in this Worker. The origin is public and contains no private YTB/Beast Mode data.
