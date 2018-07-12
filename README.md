# netns-topo
A simple script tool to deploy L2-L3 networking environment with netns,
linuxbridge on a single node, for networking tests.

Beside example-topo, you can check topo and test in keepalived and haproxy,
hope helpful.


Known issue
===========
Sometime restarting network service is needed, or virtual network topology
won't work, virtual node is not reachable for each other.
