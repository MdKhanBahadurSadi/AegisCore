enum AegisCoreMode { demo, live }

/// Runtime configuration supplied with `--dart-define` values.
class AegisCoreConfiguration {
  final AegisCoreMode mode;
  final Uri baseUri;
  final Duration connectTimeout;
  final Duration requestTimeout;

  AegisCoreConfiguration({
    required this.mode,
    required Uri baseUri,
    this.connectTimeout = const Duration(seconds: 5),
    this.requestTimeout = const Duration(seconds: 15),
  }) : baseUri = _validatedBaseUri(baseUri, mode: mode) {
    if (connectTimeout <= Duration.zero || requestTimeout <= Duration.zero) {
      throw ArgumentError('Backend timeouts must be greater than zero.');
    }
  }

  String get displayEndpoint => baseUri.toString();

  Uri endpoint(String relativePath) => baseUri.resolve(relativePath);

  factory AegisCoreConfiguration.fromEnvironment() {
    const modeValue = String.fromEnvironment(
      'AEGIS_MODE',
      defaultValue: 'demo',
    );
    const baseUrl = String.fromEnvironment(
      'AEGIS_API_BASE_URL',
      defaultValue: 'http://127.0.0.1:8000/',
    );
    const connectSeconds = int.fromEnvironment(
      'AEGIS_CONNECT_TIMEOUT_SECONDS',
      defaultValue: 5,
    );
    const requestSeconds = int.fromEnvironment(
      'AEGIS_REQUEST_TIMEOUT_SECONDS',
      defaultValue: 15,
    );

    final mode = switch (modeValue.toLowerCase()) {
      'demo' => AegisCoreMode.demo,
      'live' => AegisCoreMode.live,
      _ => throw ArgumentError.value(
        modeValue,
        'AEGIS_MODE',
        'Expected `demo` or `live`.',
      ),
    };
    final uri = Uri.tryParse(baseUrl);
    if (uri == null) {
      throw ArgumentError.value(baseUrl, 'AEGIS_API_BASE_URL');
    }
    return AegisCoreConfiguration(
      mode: mode,
      baseUri: uri,
      connectTimeout: Duration(seconds: connectSeconds),
      requestTimeout: Duration(seconds: requestSeconds),
    );
  }

  static Uri _validatedBaseUri(Uri uri, {required AegisCoreMode mode}) {
    if ((uri.scheme != 'http' && uri.scheme != 'https') ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment) {
      throw ArgumentError.value(
        uri,
        'baseUri',
        'Use an HTTP(S) URL without credentials, query parameters, or fragments.',
      );
    }
    if (mode == AegisCoreMode.live &&
        !{'localhost', '127.0.0.1', '::1'}.contains(uri.host.toLowerCase())) {
      throw ArgumentError.value(
        uri,
        'baseUri',
        'Live Backend Mode is restricted to the loopback host.',
      );
    }
    final path = uri.path.endsWith('/') ? uri.path : '${uri.path}/';
    return uri.replace(path: path);
  }
}
