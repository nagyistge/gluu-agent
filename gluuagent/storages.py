# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

from itertools import groupby


def get_cluster_nodes(client, cluster_id):
    """Gets all nodes belong to given cluster.

    If cluster with given ID is not found, ``etcd.EtcdKeyNotFound``
    will be raised.

    :params client: Instance of Etcd client.
    :params cluster_id: Id of cluster.
    :returns: List of cluster's nodes.
    """
    nodes = []

    # this will raise ``etcd.EtcdKeyNotFound`` if key is not exist
    result = client.read(
        "gluucluster/clusters/{}/nodes".format(cluster_id),
        recursive=True,
    )

    # iterates all children and for each node, transform into a ``dict``
    # and append to nodes placeholder; the key being used in ``groupby``
    # is the ID of the node, which is taken from the last 2 element of
    # the original key, for example ``gluucluster/clusters/1/nodes/1/id``
    for k, g in groupby(result.children, lambda x: x.key.split("/")[-2]):
        # given a key such as ``gluucluster/clusters/1/nodes/1/id``,
        # the actual key will be the last element of the original key,
        # which is ``id``
        nodes.append({x.key.split("/")[-1]: x.value for x in g})
    return nodes


def get_provider_nodes(client, provider_id):
    """Gets all nodes belong to given provider.

    If provider with given ID is not found, ``etcd.EtcdKeyNotFound``
    will be raised.

    :params client: Instance of Etcd client.
    :params provider_id: Id of provider.
    :returns: List of provider's nodes.
    """
    nodes = []

    # this will raise ``etcd.EtcdKeyNotFound`` if key is not exist
    result = client.read(
        "gluucluster/providers/{}/nodes".format(provider_id),
        recursive=True,
    )

    # iterates all children and for each node, transform into a ``dict``
    # and append to nodes placeholder; the key being used in ``groupby``
    # is the ID of the node, which is taken from the last 2 element of
    # the original key, for example ``gluucluster/providers/1/nodes/1/id``
    for k, g in groupby(result.children, lambda x: x.key.split("/")[-2]):
        # given a key such as ``gluucluster/providers/1/nodes/1/id``,
        # the actual key will be the last element of the original key,
        # which is ``id``
        nodes.append({x.key.split("/")[-1]: x.value for x in g})
    return nodes


def get_cluster(client, cluster_id):
    """Gets specific cluster.

    If cluster with given ID is not found, ``etcd.EtcdKeyNotFound``
    will be raised.

    :params client: Instance of Etcd client.
    :params cluster_id: ID of cluster.
    :returns: ``dict`` of cluster.
    """
    result = client.read("gluucluster/clusters/{}".format(cluster_id))

    # given a key such as ``gluucluster/clusters/1/id``,
    # the actual key will be the last element of the original key,
    # which is ``id``
    provider = {
        child.key.split("/")[-1]: child.value
        for child in result.children
    }
    return provider


def get_provider(client, provider_id):
    """Gets specific cluster.

    If provider with given ID is not found, ``etcd.EtcdKeyNotFound``
    will be raised.

    :params client: Instance of Etcd client.
    :params provider_id: ID of provider.
    :returns: ``dict`` of provider.
    """
    result = client.read("gluucluster/providers/{}".format(provider_id))

    # given a key such as ``gluucluster/providers/1/id``,
    # the actual key will be the last element of the original key,
    # which is ``id``
    provider = {
        child.key.split("/")[-1]: child.value
        for child in result.children
    }
    return provider


def get_node(client, node_id):
    """Gets specific node.

    If node with given ID is not found, ``etcd.EtcdKeyNotFound``
    will be raised.

    :params client: Instance of Etcd client.
    :params node_id: ID of node.
    :returns: ``dict`` of node.
    """
    result = client.read("gluucluster/nodes/{}".format(node_id))

    # given a key such as ``gluucluster/nodes/1/id``,
    # the actual key will be the last element of the original key,
    # which is ``id``
    node = {
        child.key.split("/")[-1]: child.value
        for child in result.children
    }
    return node
