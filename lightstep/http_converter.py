from collections import namedtuple

from lightstep.collector_pb2 import Auth, ReportRequest, Span, Reporter, KeyValue, Reference, SpanContext
from lightstep.converter import Converter
from . import util
from . import version as tracer_version
import sys
from google.protobuf.timestamp_pb2 import Timestamp


SpanRecord = namedtuple('SpanRecord', ['span', 'tags', 'logs'])


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
        return SpanRecord(span, [], [])

    def _create_span_record_with_parent(self, span_record, report_request_proto):
        span = span_record.span
        span_proto = report_request_proto.spans.add()
        span_proto.span_context.trace_id = span.context.trace_id
        span_proto.span_context.span_id=span.context.span_id
        span_proto.operation_name = util._coerce_str(span.operation_name)
        seconds, nanos = util._time_to_seconds_nanos(span.start_time)
        span_proto.start_timestamp.seconds=seconds
        span_proto.start_timestamp.nanos=nanos
        span_proto.duration_micros=int(util._time_to_micros(span.duration))

        self._append_logs_with_parent(span_record.logs, span_proto)
        self._append_tags_with_parent(span_record.tags, span_proto)

        if span.parent_id is not None:
            reference = span_proto.references.add()
            reference.relationship=Reference.CHILD_OF
            reference.span_context.span_id=span.parent_id

    def _append_logs_with_parent(self, logs, span_proto):
        for log in logs:
            seconds, nanos = util._time_to_seconds_nanos(log.timestamp)
            proto_log = span_proto.logs.add()
            proto_log.timestamp.seconds=seconds
            proto_log.timestamp.nanos=nanos
            for k, v in log.key_values.items():
                field = proto_log.fields.add()
                field.key = k
                field.string_value = util._coerce_str(v)

    def _append_tags_with_parent(self, tags, span_proto):
        for key, value in tags:
            kv = span_proto.tags.add()
            kv.key = key
            kv.string_value = value

    def append_attribute(self, span_record, key, value):
        span_record.tags.append((key, value))

    def append_join_id(self, span_record, key, value):
        self.append_attribute(span_record, key, value)

    def append_log(self, span_record, log):
        if log.key_values is not None and len(log.key_values) > 0:
            span_record.logs.append(log)

    def create_report(self, runtime, span_records):
        report = ReportRequest(reporter=runtime)
        for span_record in span_records:
            self._create_span_record_with_parent(span_record, report)
        return report

    def combine_span_records(self, report_request, span_records):
        report_request.spans.extend(span_records)
        return report_request.spans

    def num_span_records(self, report_request):
        return len(report_request.spans)

    def get_span_records(self, report_request):
        return report_request.spans

    def get_span_name(self, span_record):
        return span_record.operation_name
