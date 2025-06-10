#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import socket, errno

from libbaram.exception import CanceledException
from libbaram.run import RunUtility

from baramFlow.openfoam.file_system import FileSystem

PORT_START = 8888


def isPortInUse(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.bind(("127.0.0.1", port))
    except socket.error as e:
        if e.errno == errno.EADDRINUSE:
            return True
        else:
            # something else raised the socket.error exception
            print(e)

    s.close()

    return False


class FluentToFoamControl:
    def __init__(self):
        self._server = None
        self._future = None
        self._reader = None
        self._writer = None

    def future(self):
        return self._future

    async def listen(self, port):
        while isPortInUse(port):
            port += 1

        self._server = await asyncio.start_server(self._handleConnection, '127.0.0.1', port)
        self._future = self._server.get_loop().create_future()

        return port

    async def _handleConnection(self, reader, writer):
        self._reader = reader
        self._writer = writer

        try:
            data = await reader.read(100)

            if self._future is not None:
                self._future.set_result(0)
        except:
            self._future.set_result(1)

            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None

        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def resumeRunning(self):
        self._writer.write('Proceed'.encode('utf-8'))
        await self._writer.drain()

        self._writer.close()
        await self._writer.wait_closed()
        self._writer = None


class FluentMeshConverter(RunUtility):
    def __init__(self, fileName):
        super().__init__('fluentToFoam')

        self._cwd = FileSystem.caseRoot()
        self._fileName = fileName
        self._control = FluentToFoamControl()

    async def waitCellZonesInfo(self):
        port = await self._control.listen(PORT_START)
        self._args = ['-p', str(port), self._fileName]

        await super().start()

        waiter = self._control.future()
        done, pending = await asyncio.wait([waiter, asyncio.create_task(self._proc.wait())], return_when=asyncio.FIRST_COMPLETED)

        # If the process has exited, process exception and return
        if waiter not in done:
            if self.isCanceled():
                raise CanceledException

            return False

        return True

    async def cellZonesToRegions(self):
        await self._control.resumeRunning()
        return await self.wait()







