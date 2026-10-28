import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import 'aegiscore_configuration.dart';

/// Runtime configuration is supplied with `--dart-define` values.
final aegisCoreConfigurationProvider = Provider<AegisCoreConfiguration>(
  (ref) => AegisCoreConfiguration.fromEnvironment(),
);

/// Shared injectable transport for authentication and Live Backend requests.
final backendHttpClientProvider = Provider<http.Client>((ref) {
  final client = http.Client();
  ref.onDispose(client.close);
  return client;
});
