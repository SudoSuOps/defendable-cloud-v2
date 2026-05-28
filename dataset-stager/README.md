# dataset-stager · DefendableCloud Sprint 9

Rails-side cron worker that bridges the NAS (`/mnt/swarm/swarm-and-bee-datasets/...`)
to the Tigris download bucket and triggers the API to email members when their
download grant flips to ready.

## Where it runs

| | |
|---|---|
| **Host** | `swarmrails` (192.168.0.100) |
| **User** | `swarm` |
| **Install path** | `/home/swarm/defendable-stager/` |
| **Cadence** | systemd timer, every 2 min |
| **Why here, not Fly** | the NAS is mounted on rails. The Fly API stays on its fail-open lane (see *sidecar-fails-open* doctrine, 2026-05-25). |

## The loop

```
  every 2 min ┐
              │  GET  https://api.defendablecloud.com/internal/staging-tasks
              │       → list of pending tigris_keys (unique across all members)
              │
              │  for each task:
              │      aws s3 ls   s3://defendable-cloud-v2/<tigris_key>
              │      ├─ exists → "already-staged"
              │      └─ missing →  aws s3 cp /mnt/swarm/<source_path>
              │                              s3://defendable-cloud-v2/<tigris_key>
              │
              │  POST https://api.defendablecloud.com/internal/stage-complete
              │       { tigris_key, bytes_uploaded }
              │
              │  ← API sweeps every receipt with that tigris_key whose
              │    ready_at_grant=false, sends a Resend "your dataset is
              │    ready" email, and records the notification in
              │    download_notifications (one row per receipt).
              │
              ┘  exit code: 0 (idle/ok), 1 (config), 2 (api unreachable),
                            3 (one or more uploads failed)
```

Idempotency lives in `download_notifications` on the API side, not here. The
script can run twice for the same key — the second pass sees the rows and
makes zero new emails.

## Install on swarmrails

```bash
# 1. Place the script + units. From this checkout on your laptop:
scp -r dataset-stager/ swarm@192.168.0.100:/home/swarm/defendable-stager/

# 2. On rails: configure secrets.
ssh swarm@192.168.0.100
cd ~/defendable-stager
cp .env.example .env
chmod 600 .env
${EDITOR:-nano} .env        # paste INTERNAL_API_KEY + Tigris creds

# 3. Confirm the NAS mount + aws cli are healthy.
ls /mnt/swarm/swarm-and-bee-datasets/ | head
which aws

# 4. Dry-run once interactively before handing to systemd.
STAGER_DRY_RUN=1 python3 stage.py

# 5. Hand to systemd.
sudo cp defendable-stage.service /etc/systemd/system/
sudo cp defendable-stage.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now defendable-stage.timer

# 6. Tail the log.
journalctl -u defendable-stage.service -f
```

## Operator commands

| | |
|---|---|
| Run once now (skip the timer) | `sudo systemctl start defendable-stage.service` |
| Check timer state | `systemctl list-timers \| grep defendable-stage` |
| Pause the cron | `sudo systemctl stop defendable-stage.timer` |
| Resume | `sudo systemctl start defendable-stage.timer` |
| Dry-run a one-off | `STAGER_DRY_RUN=1 /home/swarm/defendable-stager/stage.py` |

## What it does NOT do

- Doesn't garbage-collect old objects from Tigris. A future sprint adds a
  `prune` mode that removes objects whose receipts have all expired.
- Doesn't validate the file content (e.g. line count vs catalog). The
  receipt seals package identity; the file the rails worker uploads is
  trusted as-is.
- Doesn't backfill missed notifications outside the receipt-driven sweep.
  If a member was in `no_email_available` (account deleted etc.), they
  stay there until an operator intervenes.

## Health check pattern

```bash
# After install, confirm the API sees the timer alive by manually requesting
# a download for a member, then watching:
journalctl -u defendable-stage.service --since "5 min ago"
# Expect:  [cre_cre_honey] uploaded · pending=1 · matched=1 notified=1 already=0
```

To the shed.
