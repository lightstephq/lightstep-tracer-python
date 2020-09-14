""" Connection class establishes HTTP connection with server.
    Utilized to send Thrift Report Requests.
"""
import threading
from thrift import Thrift
from thrift.transport import THttpClient
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from .crouton import ReportingService

CONSECUTIVE_ERRORS_BEFORE_RECONNECT = 200


class _ThriftConnection(object):
    """Instances of _Connection are used to establish a connection to the
    server via HTTP protocol.

    Only one instance of this class should be created per process. The object
    itself is thread-safe, but the underlying Thrift library has shared state
    that makes unsafe to call multiple instances of this class concurrrently.
    """
    def __init__(self, collector_url):
        self._collector_url = collector_url
        self._lock = threading.Lock()
        self._http_client = None
        self._transport = None
        self._client = None
        self.ready = False
        self._open_exceptions_count = 0
        self._report_eof_count = 0
        self._report_socket_errors = 0
        self._report_exceptions_count = 0
        self._report_consecutive_errors = 0

    def open(self):
        """Establish HTTP connection to the server.

        Note: THttpClient also supports https and will use http/https according
        to the scheme in the URL it is given.
        """
        self._lock.acquire()
        try:
            self._http_client = THttpClient.THttpClient(self._collector_url)
            self._transport = TTransport.TBufferedTransport(self._http_client)
            self._transport.open()
            protocol = TBinaryProtocol.TBinaryProtocolAccelerated(self._transport, fallback=True)
            self._client = ReportingService.Client(protocol)
        except Thrift.TException:
            self._open_exceptions_count += 1
        else:
            self.ready = True
        finally:
            self._lock.release()


    # May throw an Exception on failure.
    def report(self, *args, **kwargs):
        """Report to the server."""
        # Notice the annoying case change on the method name. I chose to stay
        # consistent with casing in this class vs staying consistent with the
        # casing of the pass-through method.
        resp = None
        with self._lock:
            try:
                if self._client:
                    headers = {"Lightstep-Access-Token": args[0].access_token}
                    self._http_client.setCustomHeaders(headers)
                    resp = self._client.Report(*args, **kwargs)
                    self._report_consecutive_errors = 0
            except Thrift.TException:
                self._report_consecutive_errors += 1
                self._report_exceptions_count += 1
                raise Exception('Thrift exception')
            except EOFError:
                self._report_consecutive_errors += 1
                self._report_eof_count += 1
                raise Exception('EOFError')
            finally:
                # In case the Thrift client has fallen into an unrecoverable state,
                # recreate the Thrift data structure if there are continued report
                # failures
                if self._report_consecutive_errors == CONSECUTIVE_ERRORS_BEFORE_RECONNECT:
                    self._report_consecutive_errors = 0
                    self.ready = False

        return resp

    def close(self):
        """Close HTTP connection to the server."""
        if self._transport is None:
            return
        if self._client is None:
            return

        with self._lock:
            self._transport.close()
            self.ready = False
