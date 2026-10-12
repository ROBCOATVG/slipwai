# The staging workspace. Everything not said here takes the default in variables.tf.
environment = "staging"
min_tasks   = 1
max_tasks   = 2
# Straight over: staging is where the deploy itself is proved, and production is where the window matters.
bake_minutes = 0

# A flip is a rolling restart. `appconfig` makes it a live re-read instead, at the price of an agent
# container in every task; `flags.tf` has the trade and `docs/deployment.md` says when it is worth taking.
flag_transport = "ssm"
