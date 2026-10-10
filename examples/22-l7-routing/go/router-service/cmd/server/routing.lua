-- routing.lua: the routing policy, kept outside the Go code so domain experts can change it
-- without touching the service. The service hands in the order and the live thresholds
-- (GET/PUT /rules) and takes back the destination topic and the VIP flag.
function route(order, rules)
  if order.amount >= rules.vip_threshold then
    return rules.priority_topic, true
  end
  return rules.default_topic, false
end
