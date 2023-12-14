from pysros.management import connect

# User defined constants:
# - LO_INTF is the name of the loopback interface with the anycast node sid
# - TRACKING_PREFIX is the prefix we are tracking to determine acceptable reachability
LO_INTF = 'lo65002'
TRACKING_PREFIX = '1.1.1.1/32' 

def main():
    c = connect()
    tracking_response = False
    path = '/nokia-conf:configure/router[router-name=Base]/interface[interface-name=%s]/admin-state' % LO_INTF
    data = 'disable'
    lo_intf_admin_state = c.running.get(path)
    try:
        tracking_response = c.running.get('/nokia-state:state/router[router-name=Base]/route-table/unicast/ipv4/route[ipv4-prefix="%s"]' % TRACKING_PREFIX)
    except LookupError as err:
        #print('LOOKUP ERROR - %s not in route table. ERROR: %s' % (TRACKING_PREFIX, err))
        pass
    # If we do see the tracking ip, we only want to enable the interface if it is currently disabled
    if tracking_response:
        if lo_intf_admin_state.data == 'disable': 
            print("ENABLING::lo65002 is %s and tracking_response is %s" % (lo_intf_admin_state, tracking_response['ipv4-prefix']))
            data = 'enable'
            c.candidate.set(path, data)
    # If we do not see the tracking ip, we only want to disable the interface if it is currently enabled
    elif lo_intf_admin_state.data == 'enable':
        print("DISABLING::lo65002 is %s and tracking_response is %s" % (lo_intf_admin_state, tracking_response))
        c.candidate.set(path, data)
    else:
        pass

if __name__ == "__main__":
    main()