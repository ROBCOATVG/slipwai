# The skiff has one environment. HTTP ingress and its scale rule wake a replica from zero.
environment    = "production"
cpu            = 0.25
memory         = "0.5Gi"
min_replicas   = 0
max_replicas   = 1
kept_revisions = 0
flag_transport = "keyvault"
