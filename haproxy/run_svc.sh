d=`echo $0 | cut -d '/' -f 1`
cur_nss=`ip netns | awk '{print $1}' | sort`
for i in `ls $d | grep yaml`; do
    nss=`grep -v '^ ' ${d}/$i | grep -v "n[0-9]" | cut -d ':' -f 1 | sort`
    if [[ $nss == $cur_nss ]]; then
        case=`echo $i | cut -d '.' -f 1`
    fi
done

if [[ $case == "lb-lb" ]]; then
    ip netns exec node1 gunicorn -b 0.0.0.0:80 haproxy.flask-svc:application -D
    ip netns exec node2 gunicorn -b 0.0.0.0:80 haproxy.flask-svc:application -D
    ip netns exec node3 gunicorn -b 0.0.0.0:80 haproxy.flask-svc:application -D

    outer_pid=""
    if test -f /tmp/haproxy-outer.pid; then
        outer_pid="-sf `cat /tmp/haproxy-outer.pid`"
    fi
    ip netns exec lb-outer haproxy -f haproxy/haproxy-outer.config $outer_pid

    pid=""
    if test -f /tmp/haproxy.pid; then
        pid="-sf `cat /tmp/haproxy.pid`"
    fi
    ip netns exec lb haproxy -f haproxy/haproxy.config $pid
    exit
fi

if [[ $case == "lb" ]] ; then
    ip netns exec node1 gunicorn -b 0.0.0.0:80 haproxy.flask-svc:application -D
    ip netns exec node2 gunicorn -b 0.0.0.0:80 haproxy.flask-svc:application -D
    ip netns exec node3 gunicorn -b 0.0.0.0:80 haproxy.flask-svc:application -D

    pid=""
    if test -f /tmp/haproxy.pid; then
        pid="-sf `cat /tmp/haproxy.pid`"
    fi
    ip netns exec lb haproxy -f haproxy/haproxy.config $pid
    exit
fi

if [[ $case == "lb-http-check" ]]; then
    ip netns exec node1 gunicorn -b 0.0.0.0:80 haproxy.flask-svc:application -D
    ip netns exec node2 gunicorn -b 0.0.0.0:80 haproxy.flask-svc:application -D
    ip netns exec node3 gunicorn -b 0.0.0.0:80 haproxy.flask-svc-300:application -D

    pid=""
    if test -f /tmp/haproxy.pid; then
        pid="-sf `cat /tmp/haproxy.pid`"
    fi
    ip netns exec lbhttpchk haproxy -f haproxy/haproxy-http-check.config $pid
    exit
fi

if [[ $case == "lb-lb-http-check" ]]; then
    ip netns exec node gunicorn -b 0.0.0.0:80 haproxy.flask-svc-timeout:application -D

    for i in {1..3}; do
        pid=""
        if test -f /tmp/haproxy${i}.pid; then
            pid="-sf `cat /tmp/haproxy${i}.pid`"
        fi
        ip netns exec lb${i} haproxy -f haproxy/haproxy2.config -p /tmp/haproxy${i}.pid $pid
    done

    outer_pid=""
    if test -f /tmp/haproxy-outer.pid; then
        outer_pid="-sf `cat /tmp/haproxy-outer.pid`"
    fi
    ip netns exec lb-outer haproxy -f haproxy/haproxy-outer2.config $outer_pid
    exit
fi

echo "Unknown case"
