Changelog
=========

Here you can see the full list of changes between each gluu-agent release.

Version 0.2.1
-------------

Release date to be announced later.

* Added support for docker v1.8.3.
* tinydb is upgraded to v3.0.0.


Version 0.2.0
-------------

Released on November 13th, 2015.

* Added executor for `saml` node.
* Local domain name for each node is added.
* A preserved `weave` IP address is now properly attached to `prometheus` container.
* Added delay after recovering `ldap` node to prevent other executors running simultaneously.
