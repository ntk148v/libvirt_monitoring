===============================
Libvirt Monitoring
===============================



.. image:: https://pyup.io/repos/github/ntk148v/libvirt_monitoring/shield.svg
     :target: https://pyup.io/repos/github/ntk148v/libvirt_monitoring/
     :alt: Updates

Keywords
--------

* Monitor.

* Virtual Machine.

* Zabbix.

* Libvirt.

Components
----------

* Inspector: inspect metric using libvirt.

* Agent: get metric from Inspector and send it to Zabbix Server.

* Daemon: execute Agent in background. 

Using (source)
--------------

* Clone this repo in server which already has Zabbix agent::

	git clone http://github.com/ntk148v/libvirt_monitoring

* Update configuration in config.ini and logging.ini (if you want it) files.

* Go to libvirt_monitoring and run command::

	python main.py start|stop|restart

* Check log at /var/log/libvirt_agent_info.log and /var/log/libvirt_agent_error.log

Using (distribution package)
----------------------------

* Get deb file from dist_packages/::

* Install with dpkg.

* Config in /etc/libvirt_monitoring/config.ini

Features
--------

* TODO

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

