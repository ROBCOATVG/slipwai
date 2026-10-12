# The staging workspace. Everything not said here takes the default in variables.tf.
environment  = "staging"
min_replicas = 1
max_replicas = 2
# Nothing kept: staging is where the deploy itself is proved, and production is where an instant undo is
# worth an extra replica. `min_replicas = 0` here is the other lever — an environment that sleeps between
# uses, at the price of a cold start on the first request after it has.
kept_revisions = 0

# A flip is a rolling restart. `appconfig` makes it a live re-read instead, at the price of the App
# Configuration SDK in the image; `flags.tf` has the trade and `docs/deployment.md` says when it is worth
# taking.
flag_transport = "keyvault"
