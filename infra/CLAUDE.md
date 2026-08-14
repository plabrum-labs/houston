# infra/ — Claude Code guidance

This folder is a **stub**. Houston's infrastructure has not been designed yet.

Do NOT reintroduce marlin's app-deploy model (single-app EC2/ECS, per-deploy
Aurora/Redis/ALB, SES email-in Lambda, Vercel frontend). Houston's infra is a
shared **substrate** + control plane — see [`README.md`](README.md) and
[`docs/planning/v0.md`](../docs/planning/v0.md). Design it ground-up in a
dedicated session before writing Terraform here.
