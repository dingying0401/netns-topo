# netns-topo
A simple script tool to deploy L2-L3 networking environment with netns on a single node.


Requirements
============
PyYAML
python-netaddr
bridge-utils


Flask requirements
==================
gunicorn
flask


Keepalived requirements
=======================
keepalived


Known issue
===========
Sometime restarting network service is needed, or virtual network topology won't work,
virtual node is not reachable for each other.
