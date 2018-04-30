ip netns exec node1 gunicorn -b 0.0.0.0:80 haproxy.flask-svc:application -D
ip netns exec node2 gunicorn -b 0.0.0.0:80 haproxy.flask-svc:application -D
ip netns exec node3 gunicorn -b 0.0.0.0:80 haproxy.flask-svc:application -D
