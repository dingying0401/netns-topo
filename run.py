#!/usr/bin/python2.7
#
# run as root

import netaddr
import os
import yaml


TOP = True
BOTTOM = False
DEFAULT_MTU = 1500


def get_topo(filename):
    ret = {}
    with open(filename) as f:
        ret.update(yaml.safe_load(f) or {})
    return ret


def get_dev_name(dev_type, name, **kwargs):
    ret = ''
    if dev_type == 'switch':
        ret = 'vsw' + name
    elif dev_type in ('node', 'router'):
        prefix = 'vn-' if kwargs.get('is_peer', False) else 'vb-'
        subfix = '-%s' % kwargs['switch']
        ret = prefix + name + subfix
    elif dev_type == 'ovn_node':
        subfix = 'n' if kwargs.get('is_peer', False) else 'o'
        ret = 'ovn-%s%s%s' % (kwargs['switch'], name, subfix)
    if len(ret) > 15:
        raise ValueError(
            "%(dev)s %(name)s is too long after trans. "
            "%(len)s(len(%(ret)s)) > 15." % {
                'dev': dev_type, 'name': name, 'ret': ret, 'len': len(ret)})
    return ret


def add_bridge(name):
    bridge_name = get_dev_name('switch', name)
    return '\n'.join([
        'brctl addbr %(bridge)s',
        'ip l set %(bridge)s up']) % {'bridge': bridge_name}


def del_bridge(name):
    bridge_name = get_dev_name('switch', name)
    return '\n'.join([
        'ip l set %(bridge)s down',
        'brctl delbr %(bridge)s']) % {'bridge': bridge_name}


def add_bridge_intf(bridge, intf):
    return 'brctl addif %s %s' % (bridge, intf)


def add_netns(ns_name):
    return 'ip netns add %s' % ns_name


def del_netns(ns_name):
    return 'ip netns del %s' % ns_name


def set_dev_up(dev_name, ns_name=None):
    prefix = 'ip netns exec %(ns)s ' if ns_name else ''
    return (prefix + 'ip l set %(dev)s up') % {'ns': ns_name, 'dev': dev_name}


def set_dev_netns(dev_name, ns_name):
    return 'ip l set %(dev)s netns %(ns)s' % {'ns': ns_name, 'dev': dev_name}


def set_dev_mac(dev_name, mac, ns_name=None):
    prefix = 'ip netns exec %(ns)s ' if ns_name else ''
    return (prefix + 'ip l set %(dev)s address %(mac)s') % {
        'ns': ns_name, 'dev': dev_name, 'mac': mac}


def add_veth_peer_with_netns(dev_name, peer_name, ns_name):
    return 'ip l add %(dev)s type veth peer name %(peer)s netns %(ns)s' % {
        'dev': dev_name, 'peer': peer_name, 'ns': ns_name}


def del_veth_peer_with_netns(dev_name, ns_name):
    return 'ip netns exec %(ns)s ip l del %(dev)s' % {
        'ns': ns_name, 'dev': dev_name}


def del_interface(dev_name, ns_name=None):
    prefix = 'ip netns exec %(ns)s ' if ns_name else ''
    return (prefix + 'ip l del %(dev)s') % {'ns': ns_name, 'dev': dev_name}


def add_dev_cidr(dev_name, cidr, ns_name=None):
    prefix = 'ip netns exec %(ns)s ' if ns_name else ''
    return (prefix + 'ip a add %(cidr)s dev %(dev)s') % {
        'ns': ns_name, 'dev': dev_name, 'cidr': cidr}


def add_ovs_port(db_sock, port, ns_name, br='br-int'):
    prefix = 'ip netns exec %(ns)s '
    return (prefix + 'ovs-vsctl --db=unix:%(sock)s add-port %(br)s %(p)s') % {
        'ns': ns_name, 'sock': db_sock, 'br': br, 'p': port}


def del_ovs_port(db_sock, port, br='br-int'):
    return 'ovs-vsctl --db=unix:%(sock)s del-port %(br)s %(p)s' % {
        'sock': db_sock, 'br': br, 'p': port}


def set_ovs_intf_external_ids(db_sock, port, ext_ids_dict):
    ext_ids = ['']
    ext_ids.extend(['%s=%s' % (k, v) for (k, v) in ext_ids_dict.iteritems()])
    return 'ovs-vsctl --db=unix:%(sock)s set interface %(p)s %(ext_ids)s' % {
        'sock': db_sock, 'p': port,
        'ext_ids': 'external_ids:'.join(ext_ids)}


def set_ovs_intf_iface_id(db_sock, port):
    return set_ovs_intf_external_ids(db_sock, port, {'iface-id': port})


def ovn_ls_add(ls):
    return 'ovn-nbctl ls-add %s' % ls


def ovn_ls_del(ls):
    return 'ovn-nbctl ls-del %s' % ls


def ovn_lsp_add(ls, lsp):
    return 'ovn-nbctl lsp-add %(ls)s %(p)s' % {'ls': ls, 'p': lsp}


def ovn_lsp_del(lsp):
    return 'ovn-nbctl lsp-del %s' % lsp


def ovn_lsp_set_addresses(lsp, addresses):
    return 'ovn-nbctl lsp-set-addresses %(p)s "%(addrs)s"' % {
        'p': lsp, 'addrs': addresses}


def ovn_lsp_set_dhcpv4_opts(lsp, ls, lsp_cidr):
    lsp_ipnet = netaddr.IPNetwork(lsp_cidr)
    return (
        'ovn-nbctl find dhcp_options external_ids:ls=%(ls)s '
        'cidr=\\"%(cidr)s\\" | '
        "awk '/_uuid/{print $3}' | "
        'xargs -I {} ovn-nbctl lsp-set-dhcpv4-options %(p)s {}' % {
            'ls': ls, 'p': lsp,
            'cidr': str(lsp_ipnet.network) + '/' + str(lsp_ipnet.prefixlen)}
        )


def ovn_dhcp_options_create(ls, cidr):
    return 'ovn-nbctl dhcp-options-create %s ls=%s' % (cidr, ls)


def ovn_dhcp_options_del(ls, cidr):
    return ('ovn-nbctl find dhcp_options external_ids:ls=%(ls)s '
            'cidr=\\"%(cidr)s\\" | '
            "awk '/_uuid/{print $3}' | "
            'xargs -I {} ovn-nbctl dhcp-options-del {}') % {
        'ls': ls, 'cidr': cidr}


def _ovn_dhcp_set_options(ls, cidr, opts):
    return ('ovn-nbctl find dhcp_options external_ids:ls=%(ls)s '
            'cidr=\\"%(cidr)s\\" | '
            "awk '/_uuid/{print $3}' | "
            'xargs -I {} ovn-nbctl dhcp-options-set-options {} %(opts)s') % {
        'ls': ls, 'cidr': cidr, 'opts': opts}


def ovn_dhcp_set_options(ls, cidr, mtu, router, server_id, server_mac):
    opts = ('lease_time="86400" mtu="%(mtu)s" router="%(router)s" '
            'server_id="%(server_id)s" server_mac="%(server_mac)s"') % {
        'mtu': mtu, 'router': router, 'server_id': server_id,
        'server_mac': server_mac}
    return _ovn_dhcp_set_options(ls, cidr, opts)


def setup_bridge_interface(ns_name, dev_type, switch, cidr):
    dev_name = get_dev_name(dev_type, ns_name, switch=switch)
    peer_name = get_dev_name(dev_type, ns_name, switch=switch, is_peer=True)
    bridge_name = get_dev_name('switch', switch)
    cmds = [
        add_veth_peer_with_netns(dev_name, peer_name, ns_name),
        set_dev_up(dev_name),
        set_dev_up(peer_name, ns_name),
        add_bridge_intf(bridge_name, dev_name),
        add_dev_cidr(peer_name, cidr, ns_name)]
    return '\n'.join(cmds)


def destroy_bridge_interface(ns_name, dev_type, switch):
    dev_name = get_dev_name(dev_type, ns_name, switch=switch)
    return del_interface(dev_name)


def setup_ovn_interface(ns_name, dev_type, ls, addresses, chassis,
                        chassis_sock, via_dhcp):
    chassis_dev = get_dev_name(dev_type, ns_name, switch=ls)
    node_dev = get_dev_name(dev_type, ns_name, switch=ls, is_peer=True)
    mac_cidrs = addresses.split()
    mac = mac_cidrs[0]
    cmds = [
        add_veth_peer_with_netns(chassis_dev, node_dev, ns_name),
        set_dev_mac(node_dev, mac, ns_name),
        set_dev_netns(chassis_dev, chassis),
        set_dev_up(chassis_dev, chassis),
        set_dev_up(node_dev, ns_name),
        add_ovs_port(chassis_sock, chassis_dev, ns_name),
        set_ovs_intf_iface_id(chassis_sock, chassis_dev)]
    if not via_dhcp:
        cmds.extend([
            add_dev_cidr(node_dev, cidr, ns_name) for cidr in mac_cidrs[1:]])
    return '\n'.join(cmds)


def destroy_ovn_interface(ns_name, dev_type, ls, chassis, chassis_sock):
    chassis_dev = get_dev_name(dev_type, ns_name, switch=ls)
    cmds = [
        del_ovs_port(chassis_sock, chassis_dev),
        del_veth_peer_with_netns(chassis_dev, chassis),
        del_netns(ns_name)]
    return '\n'.join(cmds)


def enable_forwarding(ns_name):
    return '\n'.join([
        'ip netns exec %(ns)s sysctl net.ipv4.conf.all.forwarding=1',
        'ip netns exec %(ns)s sysctl net.ipv4.conf.all.rp_filter=0']) % {
            'ns': ns_name}


def add_route(ns_name, dest, nexthop):
    ret = ''
    if nexthop:
        ret = 'ip netns exec %(ns_name)s ip r add %(dest)s via %(nh)s' % {
            'ns_name': ns_name, 'dest': dest, 'nh': nexthop}
    return ret


def setup_bridge_node(name, info):
    ret = [
        setup_bridge_interface(name, 'node', switch, cidr)
        for (switch, cidr) in info['interfaces'].iteritems()]
    ret.insert(0, add_netns(name))
    ret.append(add_route(name, 'default', info.get('default_route')))
    ret.append(set_dev_up('lo', name))
    ret.extend([
        add_route(name, dest, nexthop)
        for (dest, nexthop) in info.get('extra_routes', {}).iteritems()])
    return '\n'.join(ret), BOTTOM


def destroy_bridge_node(name, info):
    ret = [
        destroy_bridge_interface(name, 'node', s) for s in info['interfaces']]
    ret.append(del_netns(name))
    return '\n'.join(ret), TOP


def setup_bridge_switch(name, info):
    return add_bridge(name), TOP


def destroy_bridge_switch(name, info):
    return del_bridge(name), BOTTOM


def setup_bridge_router(name, info):
    ret = [
        setup_bridge_interface(name, 'router', switch, cidr)
        for (switch, cidr) in info['interfaces'].iteritems()]
    ret.insert(0, add_netns(name))
    ret.append(enable_forwarding(name))
    return '\n'.join(ret), BOTTOM


def destroy_bridge_router(name, info):
    ret = [destroy_bridge_interface(name, 'router', sw)
           for sw in info['interfaces']]
    ret.append(del_netns(name))
    return '\n'.join(ret), TOP


def setup_ovn_switch(name, info):
    cmds = [ovn_ls_add(name)]
    server_mac = None
    for cidr in info['cidr'].split():
        router = info.get('router') or str(netaddr.IPNetwork(cidr)[1])
        server_id = info.get('server_id') or str(netaddr.IPNetwork(cidr)[1])
        server_mac = server_mac or info.get('server_mac') or str(
            netaddr.EUI(netaddr.IPNetwork(cidr).value)).replace('-', ':')
        cmds.extend([
            ovn_dhcp_options_create(name, cidr),
            ovn_dhcp_set_options(name, cidr, info.get('mtu', DEFAULT_MTU),
                                 router, server_id, server_mac)])
    return '\n'.join(cmds), TOP


def destroy_ovn_switch(name, info):
    cmds = [ovn_ls_del(name)]
    cmds.extend([
        ovn_dhcp_options_del(name, cidr) for cidr in info['cidr'].split()])
    return '\n'.join(cmds), BOTTOM


def setup_ovn_node(name, info):
    ret = []
    for ls, addresses in info['interfaces'].iteritems():
        lsp_name = get_dev_name('ovn_node', name, switch=ls)
        ret.append(ovn_lsp_add(ls, lsp_name))
        ret.append(ovn_lsp_set_addresses(lsp_name, addresses))
        for cidr in addresses.split()[1:]:
            ret.append(ovn_lsp_set_dhcpv4_opts(lsp_name, ls, cidr))
    ret.append(add_netns(name))
    ret.extend([
        setup_ovn_interface(
            name, 'ovn_node', ls, addresses, info['chassis'],
            info['chassis_sock'], info.get('dhcp', True))
        for (ls, addresses) in info['interfaces'].iteritems()])
    ret.append(add_route(name, 'default', info.get('default_route')))
    ret.append(set_dev_up('lo', name))
    ret.extend([
        add_route(name, dest, nexthop)
        for (dest, nexthop) in info.get('extra_routes', {}).iteritems()])
    return '\n'.join(ret), BOTTOM


def destroy_ovn_node(name, info):
    ret = [
        destroy_ovn_interface(
            name, 'ovn_node', ls, info['chassis'], info['chassis_sock'])
        for ls in info['interfaces']]
    ret.extend([ovn_lsp_del(get_dev_name('ovn_node', name, switch=ls))
                for ls in info['interfaces']])
    return '\n'.join(ret), TOP


def pre_check(topo_d, name, info):
    for switch, cidr in info.get('interfaces', {}).iteritems():
        switch_cidr = topo_d.get(switch, {}).get('cidr')
        if not switch_cidr:
            raise ValueError('switch %s not found or has no cidr' % switch)
        net = netaddr.IPNetwork(switch_cidr)
        if netaddr.IPNetwork(cidr) != net:
            raise ValueError(
                "%(name)s interface cidr doesn't match its %(switch)s" % {
                    'name': name, 'switch': switch})
        ip = netaddr.IPNetwork(cidr.split('/')[0])
        if not (net.first < ip._value < net.last):
            raise ValueError(
                "%(name)s interface doesn't have a valid IP in %(switch)s" % {
                    'name': name, 'switch': switch})


def ovn_pre_check(topo_d, name, info):
    for ls, mac_cidrs in info.get('interfaces', {}).iteritems():
        mtu = topo_d.get(ls, {}).get('mtu')
        if mtu and not (str(mtu).isdigit() and 0 < mtu < 1500):
            raise ValueError('ovn_ls %s not found or has invalid mtu' % ls)
        ls_cidrs = topo_d.get(ls, {}).get('cidr')
        if not ls_cidrs:
            raise ValueError('ovn_ls %s not found or has no cidr' % ls)
        ls_cidrs = ls_cidrs.split()
        try:
            ls_ip_nets = [netaddr.IPNetwork(cidr) for cidr in ls_cidrs]
        except Exception as e:
            raise ValueError('ovn_ls %s has an invalid cidr: %s' % (
                ls, e.message))
        mac, cidrs = mac_cidrs.split(' ', 1)
        if not (netaddr.valid_mac(mac) and mac[1] != '1'):
            raise ValueError(
                "%(name)s interface has an invalid mac %(mac)s" % {
                    'name': name, 'mac': mac})
        cidrs = cidrs.split()
        try:
            intf_nets = [netaddr.IPNetwork(cidr) for cidr in cidrs]
        except Exception as e:
            raise ValueError(
                '%(name)s interface on %(ls)s has an invalid cidr: %(e)s' % {
                    'name': name, 'ls': ls, 'e': e.message})
        if set(intf_nets) - set(ls_ip_nets):
            raise ValueError(
                "Not all %(name)s interface cidr in its %(ls)s" % {
                    'name': name, 'ls': ls})
        chassis = info.get('chassis')
        if not (chassis and os.path.exists('/var/run/netns/%s' % chassis)):
            raise ValueError(
                ("%s interface doesn't have an valid 'chassis' to indicate "
                 "which chassis it resides on") % name)
        chassis_sock = info.get('chassis_sock')
        if not (chassis_sock and os.path.exists(chassis_sock)):
            raise ValueError(
                "%s interface doesn't have an valid 'chassis_sock'" % name)


def setup_or_destroy(topo_d, method, debug):
    cmds = []
    setup_methods = {
        'node': setup_bridge_node,
        'switch': setup_bridge_switch,
        'router': setup_bridge_router,
        'ovn_ls': setup_ovn_switch,
        'ovn_node': setup_ovn_node}
    destroy_methods = {
        'node': destroy_bridge_node,
        'switch': destroy_bridge_switch,
        'router': destroy_bridge_router,
        'ovn_ls': destroy_ovn_switch,
        'ovn_node': destroy_ovn_node}
    methods = {'setup': setup_methods, 'destroy': destroy_methods}

    try:
        for name, info in topo_d.iteritems():
            if name == 'services':
                continue
            _type = info['type']
            if _type not in setup_methods:
                raise ValueError(
                    "Invalid type: %s. Not in (node, switch, router)." % _type)

            if method == 'setup':
                if _type.startswith('ovn'):
                    ovn_pre_check(topo_d, name, info)
                else:
                    pre_check(topo_d, name, info)
            cmd, top = methods[method][_type](name, info)
            if method == 'setup':
                svc_cmds = [
                    "ip netns exec %s %s" % (
                        name, topo_d.get('services').get(svc, 'echo ""'))
                    for svc in info.get('service', [])]
                cmd += '\n' + '\n'.join(svc_cmds)
            elif info.get('service'):
                cmd = 'ip netns pids %s | xargs kill -9\n' % name  + cmd
            if top:
                cmds.insert(0, cmd)
            else:
                cmds.append(cmd)
    except ValueError as e:
        print e.message
        return
    else:
        cmd_file = './%s_netns_topo_cmds' % method
        with open(cmd_file, 'w+') as f:
            f.write('\n'.join(cmds))
        if debug:
            print "you can check %s for debug" % cmd_file
        else:
            os.system('bash %s' % cmd_file)
            os.remove(cmd_file)


if __name__ == '__main__':
    def _help():
        print 'python run.py {setup|destroy} topo.yaml [-d|d|debug]'
        os.sys.exit(0)

    if len(os.sys.argv) >= 3:
        method, topo_yaml = os.sys.argv[1:3]
        debug = False
        if len(os.sys.argv) == 4:
            debug = os.sys.argv[3]
            if debug not in ('d', 'debug'):
                _help()
            else:
                debug = True
        if method not in ('setup', 'destroy'):
            _help()
        if not os.path.exists(topo_yaml):
            print 'Need a topology yaml file'
            os.sys.exit(1)
        topo_d = get_topo(topo_yaml)
        if not topo_d:
            print "No invalid yaml topo found."
            os.sys.exit(1)
        setup_or_destroy(topo_d, method, debug)
    else:
        _help()
