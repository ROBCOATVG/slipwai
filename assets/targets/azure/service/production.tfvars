# The production workspace. Raise the replica size and the ceiling here when the product needs it; the
# database tier and the callback URLs are variables too.
environment  = "production"
min_replicas = 1
max_replicas = 4
# One revision kept running after it stops taking traffic, so a rollback in the minutes after a deploy is a
# change of traffic weight rather than a cold start. It costs an extra replica for as long as it is kept.
kept_revisions = 1

# A flip is a rolling restart. `appconfig` makes it a live re-read instead, at the price of the App
# Configuration SDK in the image; `flags.tf` has the trade and `docs/deployment.md` says when it is worth
# taking.
flag_transport = "keyvault"
