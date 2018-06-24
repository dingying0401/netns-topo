#             /- node1 -> node4
# node3 -> VIP
#             \- node2 -> node4
# 
# running keepalived in node1 and node2, node1 and node2 will run flask server
# node3 will be client for flask running in node1 and node2 via keepalived VIP
# node4 will run flask server, and node1 and node2 will be client for that

ip netns exec node1 gunicorn -b 0.0.0.0:80 keepalived.flask-svc:application -D
ip netns exec node2 gunicorn -b 0.0.0.0:80 keepalived.flask-svc:application -D
ip netns exec node4 gunicorn -b 0.0.0.0:80 keepalived.flask-svc:application -D

ip netns exec node1 keepalived -P -f ${PWD}/keepalived/node1_keepalived.conf -p /var/lib/node1_keeplived.pid -r /var/lib/node1_keepalived.pid-vrrp
ip netns exec node2 keepalived -P -f ${PWD}/keepalived/node2_keepalived.conf -p /var/lib/node2_keeplived.pid -r /var/lib/node2_keepalived.pid-vrrp
