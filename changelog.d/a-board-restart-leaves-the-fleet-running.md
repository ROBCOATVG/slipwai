PATCH

**Restarting the board no longer stops the fleet it cast off.** The login service had launchd (and systemd) end every process the board ever started whenever the board stopped, detached or not, so each restart or upgrade of the board stopped every captain mid-slice. The launchd agent now says `AbandonProcessGroup` and the systemd unit `KillMode=process`; run `slipwai bridge install` once to write the new file.
