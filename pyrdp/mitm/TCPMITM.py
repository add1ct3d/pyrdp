#
# This file is part of the PyRDP project.
# Copyright (C) 2019 GoSecure Inc.
# Licensed under the GPLv3 or later.
#

from logging import LoggerAdapter
from typing import Coroutine

from pyrdp.enum import PlayerMessageType
from pyrdp.layer import TwistedTCPLayer
from pyrdp.recording import Recorder


class TCPMITM:
    """
    MITM component for the TCP layer.
    """

    def __init__(self, client: TwistedTCPLayer, server: TwistedTCPLayer, attacker: TwistedTCPLayer, log: LoggerAdapter, recorder: Recorder, serverConnector: Coroutine):
        """
        :param client: TCP layer for the client side
        :param server: TCP layer for the server side
        :param attacker: TCP layer for the attacker side
        :param log: logger for this component
        :param recorder: recorder for this connection
        :param serverConnector: coroutine that connects to the server side, closed when the client disconnects
        """

        self.client = client
        self.server = server
        self.attacker = attacker
        self.log = log
        self.recorder = recorder
        self.serverConnector = serverConnector

        self.clientObserver = self.client.createObserver(
            onConnection = self.onClientConnection,
            onDisconnection = self.onClientDisconnection,
        )

        self.serverObserver = self.server.createObserver(
            onConnection = self.onServerConnection,
            onDisconnection = self.onServerDisconnection,
        )

        self.attacker.createObserver(
            onConnection = self.onAttackerConnection,
            onDisconnection = self.onAttackerDisconnection,
        )

    def detach(self):
        """
        Remove the observers from the layers.
        """

        self.client.removeObserver(self.clientObserver)
        self.server.removeObserver(self.serverObserver)

    def onClientConnection(self):
        """
        Log the fact that a new client has connected.
        """

        self.log.info("New client connected")

    def onClientDisconnection(self, reason):
        """
        Disconnect all the parts of the connection.
        :param reason: reason for disconnection
        """

        self.recorder.record(None, PlayerMessageType.CONNECTION_CLOSE)
        self.log.info("Client connection closed. %(reason)s", {"reason": reason.value})
        self.serverConnector.close()
        self.server.disconnect(True)

        # For the attacker, we want to make sure we don't abort the connection to make sure that the close event is sent
        self.attacker.disconnect()
        self.detach()

    def onServerConnection(self):
        """
        Log the fact that a connection to the server was established.
        """
        self.log.info("Server connected")

    def onServerDisconnection(self, reason):
        """
        Disconnect all the parts of the connection.
        :param reason: reason for disconnection
        """

        self.recorder.record(None, PlayerMessageType.CONNECTION_CLOSE)
        self.log.info("Server connection closed. %(reason)s", {"reason": reason.value})
        self.client.disconnect(True)

        # For the attacker, we want to make sure we don't abort the connection to make sure that the close event is sent
        self.attacker.disconnect()
        self.detach()

    def onAttackerConnection(self):
        """
        Log the fact that a connection to the attacker was established.
        """
        self.log.info("Attacker connected")

    def onAttackerDisconnection(self, reason):
        """
        Log the disconnection from the attacker side.
        """
        self.log.info("Attacker connection closed. %(reason)s", {"reason": reason.value})