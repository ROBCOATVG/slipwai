# The feature flags each service reads, and the value a *new* environment starts them at.
#
# This file is yours: the factory ships it empty, and a flag is added here in the same change that adds the
# code reading it. `flags.tf` says how one reaches the container and why a seed only ever applies once.
#
# The key is the flag's name in one spelling — `checkout-v2` — and the service reads it as
# `FLAG_CHECKOUT_V2`. Seed it at whatever the service already does today, so an environment created from
# this file behaves the way the one beside it does, and flip it afterwards:
#
#   make flag ENV=staging KEY=checkout-v2 VALUE=on
#   make flags ENV=staging
#
# A flag being *introduced* is therefore always seeded `off`: it is not released yet, and an environment
# created tomorrow must not behave differently from the one beside it. `make check-flags` holds a new key
# to that, and to being read somewhere, and to having both of its paths tested.
#
# One key covers a **releasable capability**, which is usually more than one slice — three slices that are
# not coherent to a customer until all three land want one flag held off across all three, not three
# flags. The constitution also asks each flag for an owner and a removal date; nothing gates those, so
# write them in a comment beside the key, and delete the key, its branch and the test of its off path in
# one change once the capability is released.
#
# Applied to every environment this project has, because a flag that exists in only one is a flag whose
# staging run proves nothing. Where they differ is at runtime, which is the whole point of the parameter.
# A project that does not auto-promote has only staging until it first promotes; the seeds
# here are what production is given on the day it is created, which is the same thing they are anywhere.
#
# A browser app reads the same flag by asking the service for it, over `GET /api/flags`, so one key here is
# one value on both sides of `/api` and a flip moves both halves at once. Declare a flag the browser reads
# under the service its `/api` goes to, which is the service that enforces it and the one that answers for
# it; declared anywhere else, nothing reads it and `make check-flags` says so.

flags = {
  # api = {
  #   checkout-v2 = "off"
  # }
}
