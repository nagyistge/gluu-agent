#!/bin/sh
### BEGIN INIT INFO
# Provides:          gluu-agent
# Required-Start:    $remote_fs $network
# Required-Stop:     $remote_fs $network
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: gluu-agent control
# Description:       This is a daemon that controls the gluu-agent
### END INIT INFO

PATH=/sbin:/usr/sbin:/bin:/usr/bin
DESC="gluu-agent"
NAME=gluu-agent
DAEMON=/usr/bin/gluu-agent
SCRIPTNAME=/etc/init.d/$NAME
DATABASE=/var/lib/gluu-cluster/db/db.json
RECOVER_LOGFILE=/var/log/gluuagent-recover.log
RECOVER_ENCRYPTED=0

# Exit if the package is not installed
[ -x "$DAEMON" ] || exit 0

# Read configuration variable file if it is present
[ -r /etc/default/$NAME ] && . /etc/default/$NAME

. /lib/lsb/init-functions

do_recover() {
    if [[ $RECOVER_ENCRYPTED = 0 ]]; then
        nohup $DAEMON recover --database $DATABASE --logfile $RECOVER_LOGFILE >/dev/null 2>&1 &
    else
        nohup $DAEMON recover --encrypted --database $DATABASE --logfile $RECOVER_LOGFILE >/dev/null 2>&1 &
    fi
}

do_nothing() {
    # a no-op function
    echo "gluu-agent no-op" >/dev/null
}
case "$1" in
    start)
        do_recover
        ;;
    stop|restart|force-reload|status)
        # satisfy init script requirements
        do_nothing
        ;;
    recover)
        do_recover
        ;;
    *)
        echo "Usage: $SCRIPTNAME {start|recover}" >&2
        exit 3
        ;;
esac

exit 0
