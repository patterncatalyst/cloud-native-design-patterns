-- routing.lua: the routing policy, kept outside the C++ code so domain experts can change it
-- without touching the service. The service hands in the order and the live thresholds
-- (GET/PUT /rules) and takes back the destination topic and the VIP flag.
-- The script runs in a sandbox: base, table, string and math only (no io, os, require, load).
function route(order, rules)
  if order.amount >= rules.vip_threshold then
    return rules.priority_topic, true
  end
  return rules.default_topic, false
end
