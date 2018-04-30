ip netns | grep -q lb-outer
if [[ $? -eq 0 ]]; then
    outer_pid=""
    if test -f /tmp/haproxy-outer.pid; then
        outer_pid="-sf `cat /tmp/haproxy-outer.pid`"
    fi
    ip netns exec lb-outer haproxy -f haproxy/haproxy-outer.config $outer_pid
fi
pid=""
if test -f /tmp/haproxy.pid; then
    pid="-sf `cat /tmp/haproxy.pid`"
fi
ip netns exec lb haproxy -f haproxy/haproxy.config $pid
