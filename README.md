# ISIS Conditional Route Advertisement using EHS and Cron

### Nokia SROS provides network-operators great flexibility to extend existing functionality or to create custom behavior by means of the event handling system (ehs) and cron.



<img align="left" src="https://github.com/drewelliott/clab_ehs_and_cron/blob/main/images/net_topo.png">

## understanding the topology
- only the `asbr01` is running SROS, the others are all running SR Linux
- `rr13` will be originating a tracking ip `1.1.1.1/32` into 65001 via iBGP. 
- `cs01` runs eBGP over a point-to-point link to `asbr01`
- `asbr01` runs ISIS and iBGP with `tcr01` and `tcr02`, NH on all iBGP routes is rewritten to `2.2.2.2/32`

## conditions
Advertise `2.2.2.2/32` into ISIS only if:
- The point-to-point link between `asbr01` and `cs01` is up
- The eBGP session between `asbr01` and `cs01` is up
- The tracking ip `1.1.1.1/32` is in the route table

---

The lab is deployed using [containerlab](https://containerlab.dev)

The BGP session and link between `asbr01` and `cs01` can be monitored using event triggers in ehs, but we will have to use cron to scan the route-table for `1.1.1.1/32`.

## EHS Configuration

Before we look at the script itself, we will review the required configuration in SROS. Configuring an ehs script can be thought of as basically defining a trigger, defining a filter, defining a script and then tying them together. 

### Defining a trigger
There are a large number of log events that can be used as event triggers. This is a very [helpful tool to search through the available triggers](https://documentation.nokia.com/html/LETOOL2210R1/LETOOL2210R1/events.html). 

I will use the `bgpBackwardTransNotification` as the example going forward.

> When defining a trigger, we will enable the log event and we create a filter for the trigger because we want to be as specific as possible.

```
log {
    log-events {
        bgp event bgpBackwardTransNotification {
            generate true
        }
    event-trigger {
        bgp event bgpBackwardTransNotification {
            admin-state disable
            entry 10 {
                filter "bgp_trans_from_established"
                handler "bgp_trans_handler"
            }
        }
    }
}
```
### Defining a filter

> In this filter we are looking specifically at the particular peer we are tracking and also we only want to trigger on a move from ESTABLISHED (this event would be triggered everytime bgp tries to connect as it moves through the fsm and drops back to ACTIVE otherwise)

```
log {
    filter "bgp_trans_from_established" {
        default-action drop
        named-entry "bgp_trans_from_established" {
            action forward
            match {
                message {
                    eq "Peer 65.0.0.1: moved from higher state ESTABLISHED to lower state"
                    regexp true
                }
            }
        }
    }
}
```
### Defining a script

> In this case, we are using a python script so we provide the details for the python script and then associate it with a script-policy
```
python {
    python-script "ehs_cond_adv_script" {
        admin-state enable
        urls ["tftp://172.31.255.29/scripts/ehs_cond_adv.py"]
        version python3
    }
}
system {
    script-control {
        script-policy "bgp_trans_policy" owner "admin" {
            admin-state enable
            max-completed 5
            results "/null"
            python-script {
                name "ehs_cond_adv_script"
            }
        }
    }
}
```

### Configuring the event handler
> The event handler associates the script-policy with the event-trigger, it basically stiches everything together

```
log {
    event-handling {
        handler "bgp_trans_handler" {
            admin-state enable
            entry 10 {
                script-policy {
                    name "bgp_trans_policy"
                    owner "admin"
                }
            }
        }
    }
}
```

### Putting is all together

This is what the whole configuration looks like:

```
log {
    log-events {
        bgp event bgpBackwardTransNotification {
            generate true
        }
    event-handling {
        handler "bgp_trans_handler" {
            admin-state enable
            entry 10 {
                script-policy {
                    name "bgp_trans_policy"
                    owner "admin"
                }
            }
        }
    event-trigger {
        bgp event bgpBackwardTransNotification {
            admin-state disable
            entry 10 {
                filter "bgp_trans_from_established"
                handler "bgp_trans_handler"
            }
        }
    filter "bgp_trans_from_established" {
        default-action drop
        named-entry "bgp_trans_from_established" {
            action forward
            match {
                message {
                    eq "Peer 65.0.0.1: moved from higher state ESTABLISHED to lower state"
                    regexp true
                }
            }
        }
    }
}
python {
    python-script "ehs_cond_adv_script" {
        admin-state enable
        urls ["tftp://172.31.255.29/scripts/ehs_cond_adv.py"]
        version python3
    }
}
system {
    script-control {
        script-policy "bgp_trans_policy" owner "admin" {
            admin-state enable
            max-completed 5
            results "/null"
            python-script {
                name "ehs_cond_adv_script"
            }
        }
    }
}
```

## Cron

### Cron is very straightforward to configure - we already know how to define the script and instead of an event trigger, we just need to define a schedule

```
system {
    script-control {
        script-policy "cron_cond_adv" owner "admin" {
            admin-state enable
            max-completed 5
            results "/null"
            python-script {
                name "cron_cond_adv"
            }
        }
    }
    cron {
        schedule "cron_cond_adv" owner "admin" {
            admin-state enable
            interval 60
            type periodic
            script-policy {
                name "cron_cond_adv"
                owner "admin"
            }
        }
    }
}
python {
    python-script "cron_cond_adv" {
        admin-state enable
        urls ["tftp://172.31.255.29/scripts/cron_cond_adv.py"]
        version python3
    }
}
```
