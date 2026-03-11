# Fingerprint Authentication Setup

Manual post-install steps for hardware fingerprint readers.

**Behavior:**

- **TTY Boot:** Prompts for typed username → prompts for fingerprint (falls back to password).
- **Sudo:** Prompts for fingerprint (falls back to password).
- **Hyprlock:** Native D-Bus integration (parallel password/fingerprint).

---

## 1. Install & Enroll

```bash
sudo pacman -S fprintd
fprintd-enroll
```

## 2. Enable for `sudo`

**File:** `/etc/pam.d/sudo`

Add `auth sufficient pam_fprintd.so` to the very top, immediately after the header:

```text
#%PAM-1.0
auth		sufficient	pam_fprintd.so
auth		include		system-auth
account		include		system-auth
session		include		system-auth
```

## 3. Enable for TTY Login

**File:** `/etc/pam.d/system-local-login`

Add `auth sufficient pam_fprintd.so` as the first auth rule, before `system-login`. _(Do not edit `pam.d/login` or `pam.d/system-auth` to ensure remote SSH remains strictly password-only)._

```text
#%PAM-1.0
auth      sufficient pam_fprintd.so
auth      include   system-login
account   include   system-login
password  include   system-login
session   include   system-login
```

## 4. Enable in Hyprlock

**File:** `~/.config/hypr/hyprlock.conf`

Ensure this block exists (Hyprlock natively talks to fprintd via D-Bus; no PAM hacks required):

```text
auth {
    fingerprint {
        enabled = true
        ready_message = Scan fingerprint to unlock
        present_message = Scanning...
        retry_delay = 250
    }
}
```
