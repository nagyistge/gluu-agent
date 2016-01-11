Changelog
=========

Here you can see the full list of changes between each gluu-agent release.

Version 0.2.2
-------------

Released on January 12th, 2016.

* Updated recovery process for oxIdp node.
* Added feature to convert SSL pem-based to der-based format.

Version 0.2.1
-------------

Released on December 4th, 2015.

* Added support for docker v1.8.3.
* tinydb is upgraded to v3.0.0.
* Fixed bug where recover task unable to find provider by its hostname.
* Fixed bug where recover task bypassed the cluster/provider check.


Version 0.2.0
-------------

Released on November 13th, 2015.

* Added executor for `saml` node.
* Local domain name for each node is added.
* A preserved `weave` IP address is now properly attached to `prometheus` container.
* Added delay after recovering `ldap` node to prevent other executors running simultaneously.
