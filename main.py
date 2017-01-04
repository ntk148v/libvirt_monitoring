import logging
import sys

from libvirt_monitoring import daemon
from libvirt_monitoring import utils


LOG = logging.getLogger(__name__)


def main():
    # Load logging config.
    utils.logging_config_loader()
    # Init AgentDaemon.
    LOG.info('Initiliaze AgentDaemon')
    agent_daemon = daemon.AgentDaemon('/tmp/agent-daemon.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            agent_daemon.start()
        if 'stop' == sys.argv[1]:
            agent_daemon.stop()
        if 'restart' == sys.argv[1]:
            agent_daemon.restart()
        else:
            print('Unknow command')
            sys.exit(2)
    else:
        print('usage: %s start|stop|restart' % sys.argv[0])
        sys.exit(2)


if __name__ == '__main__':
    main()