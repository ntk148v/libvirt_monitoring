===============================
Libvirt Monitoring
===============================



.. image:: https://pyup.io/repos/github/ntk148v/libvirt_monitoring/shield.svg
     :target: https://pyup.io/repos/github/ntk148v/libvirt_monitoring/
     :alt: Updates

Keywords:

* Monitor.

* Virtual Machine.

* Zabbix.

* Libvirt.

Components:

* Inspector: inspect metric using libvirt.

* Agent: get metric from Inspector and send it to Zabbix Server.

* Daemon: execute Agent in background. 

Using
--------

* Clone this repo in server which already has Zabbix agent::

	git clone http://github.com/ntk148v/libvirt_monitoring

* Update configuration in config.ini and logging.ini (if you want it) files.

* Run command::

	python main.py start|stop|restart

* Check log at /var/log/libvirt_agent.log

Features
--------

* TODO

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

