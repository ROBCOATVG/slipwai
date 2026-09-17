# The production workspace. Raise the task size and the ceiling here when the product needs it; the
# database instance class and the callback URLs are variables too.
environment = "production"
min_tasks   = 1
max_tasks   = 4
# Five minutes with the previous revision still up after every deploy: a rollback in that window is instant.
bake_minutes = 5

# A flip is a rolling restart. `appconfig` makes it a live re-read instead, at the price of an agent
# container in every task; `flags.tf` has the trade and `docs/deployment.md` says when it is worth taking.
flag_transport = "ssm"
