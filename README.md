# lightstep-tracer-python

[![PyPI](https://img.shields.io/pypi/v/lightstep.svg?maxAge=2592000)]() [![Circle CI](https://circleci.com/gh/lightstep/lightstep-tracer-python.svg?style=shield)](https://circleci.com/gh/lightstep/lightstep-tracer-python) [![MIT license](http://img.shields.io/badge/license-MIT-blue.svg)](http://opensource.org/licenses/MIT)

The LightStep distributed tracing library for Python.

## Installation

```bash
apt-get install python-dev
pip install lightstep
```

## Developer Setup

### Prerequisites
* [PyEnv](https://github.com/pyenv/pyenv)

```python
pyenv install 2.7.15
pyenv install 3.4.9
pyenv install 3.5.6
pyenv install 3.6.6
pyenv install 3.7.0
pyenv local 2.7.15 3.4.9
```

* [Tox](https://pypi.org/project/tox/)
```python
tox
```

* Run the examples:
```python
source .tox/py37/bin/activate
python examples/nontrivial/main.py
```

* [Python-Modernize](https://github.com/python-modernize/python-modernize)

Only required for LightStep developers
```python
pip install modernize
```

* [Protobuf Python Compiler](http://google.github.io/proto-lens/installing-protoc.html)

Only required for LightStep developers
```python
brew install protobuf
```

* Generating the proto code
```python
cd ..
git clone https://github.com/googleapis/googleapis.git
git clone https://github.com/lightstep/lightstep-tracer-common.git
cd lightstep-tracer-python
make proto
```

## Getting Started with Tracing

Please see the [example programs](examples/) for examples of how to use this library. In particular:

* [Trivial Example](examples/trivial/main.py) shows how to use the library on a single host.
* [Context in Headers](examples/http/context_in_headers.py) shows how to pass a `TraceContext` through `HTTP` headers.

Or if your python code is already instrumented for OpenTracing, you can simply switch to LightStep's implementation with:

```python
import opentracing
import lightstep

if __name__ == "__main__":
  opentracing.tracer = lightstep.Tracer(
    component_name='your_microservice_name',
    access_token='{your_access_token}')

  with opentracing.tracer.start_active_span('TestSpan') as scope:
    scope.span.log_event('test message', payload={'life': 42})

  opentracing.tracer.flush()
```

### Thrift
When using apache thrift rpc, make sure to both disable use_http by setting it to False as well
as enabling use_thrift.

```python
return lightstep.Tracer(
    ...
    use_http=False,
    use_thrift=True)
```

This library is the LightStep binding for [OpenTracing](http://opentracing.io/). See the [OpenTracing Python API](https://github.com/opentracing/opentracing-python) for additional detail.

## Testing

The LightStep Python Tracer is performance tested in CI using [LightStep Benchmarks](https://github.com/lightstep/lightstep-benchmarks). Performance regression tests are run automatically every commit, and performance graphs can be generated with manual approval. **This repo will show a yellow dot for CI test status even when all of the automatic tests have run. Because LightStep Benchmarks performance graphs are only generated after manual approval and CircleCI counts them as "running" before they've been approved, you won't see a green status check mark unless you've manually approved performance graph generation.**
