from pysros.ehs import get_event
from pysros.management import connect

# User defined constants:
# - LO_INTF is the name of the loopback interface with the anycast node sid
# - TRACKING_PREFIX is the prefix we are tracking to determine acceptable reachability
LO_INTF = 'lo65002'
TRACKING_PREFIX = '1.1.1.1/32' 

def parse_event(event):
    if event.name == 'linkDown':
        modify_anycast_sid_advertise(LO_INTF, 'disable', TRACKING_PREFIX)
    if event.name == 'linkUp':
        modify_anycast_sid_advertise(LO_INTF, 'enable', TRACKING_PREFIX)
    if event.name == 'bgpBackwardTransNotification':
        if event.eventparameters['old_state_str'] == "ESTABLISHED":
            modify_anycast_sid_advertise(LO_INTF, 'disable', TRACKING_PREFIX)


def modify_anycast_sid_advertise(lo_intf, state, tracking_prefix):
    # the state of the loopback interface will determine whether or not the anycast sid will be 
    # advertised into isis
    c = connect()
    tracking_response = False
    # lo_intf is the name of the loopback interface that is configured with the anycast node sid
    path = '/nokia-conf:configure/router[router-name=Base]/interface[interface-name=%s]/admin-state' % lo_intf
    # state is either enable or disable
    data = state
    if state == 'enable':
        try:
            tracking_response = c.running.get('/nokia-state:state/router[router-name=Base]/route-table/unicast/ipv4/route[ipv4-prefix="%s"]' % tracking_prefix)
        except LookupError as err:
            print('LOOKUP ERROR: %s' % err)
        if tracking_response:
            c.candidate.set(path, data)
    else:
        c.candidate.set(path, data)


def main():
    event = get_event()
    parse_event(event)

if __name__ == "__main__":
    main()