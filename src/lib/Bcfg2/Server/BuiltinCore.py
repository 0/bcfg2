""" the core of the builtin bcfg2 server """

import sys
import time
import socket
import daemon
from Bcfg2.Server.Core import BaseCore, NoExposedMethod
from Bcfg2.Compat import xmlrpclib, urlparse
from Bcfg2.SSLServer import XMLRPCServer


class Core(BaseCore):
    """ The built-in server core """
    name = 'bcfg2-server'

    def __init__(self, setup):
        BaseCore.__init__(self, setup)
        self.server = None
        self.context = daemon.DaemonContext()

    def _dispatch(self, method, args, dispatch_dict):
        """Custom XML-RPC dispatcher for components.

        method -- XML-RPC method name
        args -- tuple of paramaters to method

        """
        if method in dispatch_dict:
            method_func = dispatch_dict[method]
        else:
            try:
                method_func = self._resolve_exposed_method(method)
            except NoExposedMethod:
                self.logger.error("Unknown method %s" % (method))
                raise xmlrpclib.Fault(xmlrpclib.METHOD_NOT_FOUND,
                                      "Unknown method %s" % method)

        try:
            method_start = time.time()
            try:
                result = method_func(*args)
            finally:
                self.stats.add_value(method, time.time() - method_start)
        except xmlrpclib.Fault:
            raise
        except Exception:
            err = sys.exc_info()[1]
            if getattr(err, "log", True):
                self.logger.error(err, exc_info=True)
            raise xmlrpclib.Fault(getattr(err, "fault_code", 1), str(err))
        return result

    def _daemonize(self):
        self.context.open()
        self.logger.info("%s daemonized" % self.name)

    def _run(self):
        hostname, port = urlparse(self.setup['location'])[1].split(':')
        server_address = socket.getaddrinfo(hostname,
                                            port,
                                            socket.AF_UNSPEC,
                                            socket.SOCK_STREAM)[0][4]
        try:
            self.server = XMLRPCServer(self.setup['listen_all'],
                                       server_address,
                                       keyfile=self.setup['key'],
                                       certfile=self.setup['cert'],
                                       register=False,
                                       timeout=1,
                                       ca=self.setup['ca'],
                                       protocol=self.setup['protocol'])
        except:  # pylint: disable=W0702
            err = sys.exc_info()[1]
            self.logger.error("Server startup failed: %s" % err)
            self.context.close()
        self.server.register_instance(self)

    def _block(self):
        try:
            self.server.serve_forever()
        finally:
            self.server.server_close()
            self.context.close()
        self.shutdown()
