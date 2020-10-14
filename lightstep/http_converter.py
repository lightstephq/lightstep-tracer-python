import socket
import sys

from lightstep.collector_pb2 import Auth, ReportRequest, Span, Reporter, KeyValue, Reference, SpanContext
from lightstep.converter import Converter
from . import util
from . import version as tracer_version
from google.protobuf.timestamp_pb2 import Timestamp


class HttpConverter(Converter):

    def create_auth(self, access_token):
        auth = Auth()
        auth.access_token = access_token
        return auth

    def create_runtime(self, component_name, tags, guid):
        if component_name is None:
            component_name = sys.argv[0]

        python_version = '.'.join(map(str, sys.version_info[0:3]))

        if tags is None:
            tags = {}
        tracer_tags = tags.copy()
        tracer_tags['lightstep.hostname'] = tracer_tags.get('lightstep.hostname', socket.gethostname())

        tracer_tags.update({
            'lightstep.tracer_platform': 'python',
            'lightstep.tracer_platform_version': python_version,
            'lightstep.tracer_version': tracer_version.LIGHTSTEP_PYTHON_TRACER_VERSION,
            'lightstep.component_name': component_name,
            'lightstep.guid': util._id_to_hex(guid),
        })

        # Convert tracer_tags to a list of KeyValue pairs.
        runtime_attrs = [KeyValue(key=k, string_value=util._coerce_str(v)) for (k, v) in tracer_tags.items()]

        return Reporter(reporter_id=guid, tags=runtime_attrs)

    def create_span_record(self, span, guid):
        span_context = SpanContext(trace_id=span.context.trace_id,
                                   span_id=span.context.span_id)
        seconds, nanos = util._time_to_seconds_nanos(span.start_time)
        if span.duration < 0:
            span.duration = 0
        span_record = Span(span_context=span_context,
                           operation_name=util._coerce_str(span.operation_name),
                           start_timestamp=Timestamp(seconds=seconds, nanos=nanos),
                           duration_micros=int(util._time_to_micros(span.duration)))
        if span.parent_id is not None:
            reference = span_record.references.add()
            reference.relationship=Reference.CHILD_OF
            reference.span_context.span_id=span.parent_id

        return span_record

    def append_attribute(self, span_record, key, value):
        kv = span_record.tags.add()
        kv.key = key
        kv.string_value = value

    def append_join_id(self, span_record, key, value):
        self.append_attribute(span_record, key, value)

    def append_log(self, span_record, log):
        if log.key_values is not None and len(log.key_values) > 0:
            seconds, nanos = util._time_to_seconds_nanos(log.timestamp)

            proto_log = span_record.logs.add()
            proto_log.timestamp.seconds=seconds
            proto_log.timestamp.nanos=nanos
            for k, v in log.key_values.items():
                field = proto_log.fields.add()
                field.key = k
                field.string_value = util._coerce_str(v)

    def create_report(self, runtime, span_records):
        return ReportRequest(reporter=runtime, spans=span_records)

    def combine_span_records(self, report_request, span_records):
        report_request.spans.extend(span_records)
        return report_request.spans

    def num_span_records(self, report_request):
        return len(report_request.spans)

    def get_span_records(self, report_request):
        return report_request.spans

    def get_span_name(self, span_record):
        return span_record.operation_name
