import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'aegiscore_configuration.dart';
import 'backend_http_client.dart';

enum AuthenticationStatus { loading, signedOut, signedIn, demo }

class AuthenticationState {
  final AuthenticationStatus status;
  final String? username;
  final String? accessToken;
  final Set<String> permissions;
  final String? message;

  const AuthenticationState._({
    required this.status,
    this.username,
    this.accessToken,
    this.permissions = const {},
    this.message,
  });

  const AuthenticationState.loading()
    : this._(status: AuthenticationStatus.loading);

  const AuthenticationState.signedOut({String? message})
    : this._(status: AuthenticationStatus.signedOut, message: message);

  const AuthenticationState.signedIn({
    required String username,
    required String accessToken,
    required Set<String> permissions,
  }) : this._(
         status: AuthenticationStatus.signedIn,
         username: username,
         accessToken: accessToken,
         permissions: permissions,
       );

  const AuthenticationState.demo()
    : this._(status: AuthenticationStatus.demo);
}

abstract interface class SessionTokenStorage {
  Future<String?> read();
  Future<void> write(String token);
  Future<void> delete();
}

class PlatformSessionTokenStorage implements SessionTokenStorage {
  static const _key = 'aegiscore.local_backend_session';
  final FlutterSecureStorage _storage;

  PlatformSessionTokenStorage([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  @override
  Future<String?> read() => _storage.read(key: _key);

  @override
  Future<void> write(String token) => _storage.write(key: _key, value: token);

  @override
  Future<void> delete() => _storage.delete(key: _key);
}

final sessionTokenStorageProvider = Provider<SessionTokenStorage>(
  (ref) => PlatformSessionTokenStorage(),
);

class AuthenticationController extends Notifier<AuthenticationState> {
  static const _sessionPath = 'auth/session';
  static const _loginPath = 'auth/login';
  static const _logoutPath = 'auth/logout';
  int _restoreAttempt = 0;

  @override
  AuthenticationState build() {
    final configuration = ref.watch(aegisCoreConfigurationProvider);
    final attempt = ++_restoreAttempt;
    if (configuration.mode == AegisCoreMode.demo) {
      return const AuthenticationState.demo();
    }
    unawaited(_restore(configuration, attempt));
    return const AuthenticationState.loading();
  }

  Future<void> _restore(AegisCoreConfiguration configuration, int attempt) async {
    final storage = ref.read(sessionTokenStorageProvider);
    String? token;
    try {
      token = await storage.read();
    } catch (_) {
      _setSignedOut(attempt, 'Secure session storage is unavailable on this device.');
      return;
    }
    if (attempt != _restoreAttempt) return;
    if (token == null || token.isEmpty) {
      _setSignedOut(attempt, null);
      return;
    }

    try {
      final response = await _send(
        configuration.endpoint(_sessionPath),
        method: 'GET',
        token: token,
      );
      if (attempt != _restoreAttempt) return;
      if (response.statusCode == 401) {
        await storage.delete();
        _setSignedOut(attempt, 'Your saved session expired. Sign in again.');
        return;
      }
      if (response.statusCode != 200) {
        _setSignedOut(attempt, _statusMessage(response.statusCode));
        return;
      }
      final body = _decodeMap(response.body);
      final username = body['username'];
      final permissions = body['permissions'];
      if (body['authenticated'] != true ||
          username is! String ||
          permissions is! List ||
          permissions.any((permission) => permission is! String)) {
        throw const FormatException('Invalid backend session response.');
      }
      state = AuthenticationState.signedIn(
        username: username,
        accessToken: token,
        permissions: Set<String>.unmodifiable(permissions.cast<String>()),
      );
    } on _AuthenticationTransportFailure catch (error) {
      if (attempt == _restoreAttempt) _setSignedOut(attempt, error.message);
    } catch (_) {
      if (attempt == _restoreAttempt) {
        _setSignedOut(attempt, 'Could not validate the saved backend session.');
      }
    }
  }

  Future<void> signIn(String username, String password) async {
    final configuration = ref.read(aegisCoreConfigurationProvider);
    if (configuration.mode != AegisCoreMode.live) {
      state = const AuthenticationState.demo();
      return;
    }
    ++_restoreAttempt;
    state = const AuthenticationState.loading();
    final storage = ref.read(sessionTokenStorageProvider);
    try {
      final response = await _send(
        configuration.endpoint(_loginPath),
        method: 'POST',
        body: {'username': username, 'password': password},
      );
      if (response.statusCode != 200) {
        state = AuthenticationState.signedOut(
          message: _statusMessage(response.statusCode),
        );
        return;
      }
      final body = _decodeMap(response.body);
      final token = body['access_token'];
      if (token is! String || token.isEmpty || body['token_type'] != 'bearer') {
        throw const FormatException('Invalid login response.');
      }
      final sessionResponse = await _send(
        configuration.endpoint(_sessionPath),
        method: 'GET',
        token: token,
      );
      if (sessionResponse.statusCode != 200) {
        state = AuthenticationState.signedOut(
          message: _statusMessage(sessionResponse.statusCode),
        );
        return;
      }
      final session = _decodeMap(sessionResponse.body);
      final sessionUsername = session['username'];
      final permissions = session['permissions'];
      if (session['authenticated'] != true ||
          sessionUsername is! String ||
          permissions is! List ||
          permissions.any((permission) => permission is! String)) {
        throw const FormatException('Invalid session response.');
      }
      try {
        await storage.write(token);
      } catch (_) {
        try {
          await _send(
            configuration.endpoint(_logoutPath),
            method: 'POST',
            token: token,
          );
        } catch (_) {
          // The in-memory session expires automatically; never retain it in
          // insecure storage if the platform secure store failed.
        }
        state = const AuthenticationState.signedOut(
          message: 'Secure session storage is unavailable on this device.',
        );
        return;
      }
      state = AuthenticationState.signedIn(
        username: sessionUsername,
        accessToken: token,
        permissions: Set<String>.unmodifiable(permissions.cast<String>()),
      );
    } on _AuthenticationTransportFailure catch (error) {
      state = AuthenticationState.signedOut(message: error.message);
    } catch (_) {
      state = const AuthenticationState.signedOut(
        message: 'The backend returned an invalid authentication response.',
      );
    }
  }

  Future<void> signOut() async {
    ++_restoreAttempt;
    final current = state;
    final token = current.accessToken;
    final configuration = ref.read(aegisCoreConfigurationProvider);
    state = const AuthenticationState.signedOut();
    try {
      if (token != null && configuration.mode == AegisCoreMode.live) {
        await _send(
          configuration.endpoint(_logoutPath),
          method: 'POST',
          token: token,
        );
      }
    } catch (_) {
      // Local token deletion is authoritative for this client. A session
      // whose logout request cannot reach the backend expires on its own.
    } finally {
      try {
        await ref.read(sessionTokenStorageProvider).delete();
      } catch (_) {
        // Keep the UI signed out even when the operating-system vault is down.
      }
    }
  }

  Future<void> expireSession(String token) async {
    if (state.accessToken != token) return;
    state = const AuthenticationState.signedOut(
      message: 'Your backend session expired. Sign in again.',
    );
    try {
      await ref.read(sessionTokenStorageProvider).delete();
    } catch (_) {
      // The backend rejects this expired token on every protected request.
    }
  }

  Future<http.Response> _send(
    Uri uri, {
    required String method,
    String? token,
    Map<String, Object?>? body,
  }) async {
    final configuration = ref.read(aegisCoreConfigurationProvider);
    final headers = <String, String>{
      'Accept': 'application/json',
      if (body != null) 'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
    try {
      final request = http.Request(method, uri)..headers.addAll(headers);
      if (body != null) request.body = jsonEncode(body);
      final response = await ref
          .read(backendHttpClientProvider)
          .send(request)
          .timeout(configuration.connectTimeout);
      return await http.Response.fromStream(response)
          .timeout(configuration.requestTimeout);
    } on TimeoutException {
      throw const _AuthenticationTransportFailure(
        'The backend authentication request timed out.',
      );
    } on http.ClientException {
      throw const _AuthenticationTransportFailure(
        'Could not connect to the configured backend.',
      );
    } catch (error) {
      if (error is _AuthenticationTransportFailure) rethrow;
      throw const _AuthenticationTransportFailure(
        'Could not complete backend authentication.',
      );
    }
  }

  static Map<String, dynamic> _decodeMap(String value) {
    final decoded = jsonDecode(value);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('Expected an authentication object.');
    }
    return decoded;
  }

  static String _statusMessage(int status) => switch (status) {
    401 => 'Username or password is incorrect, or the saved session expired.',
    403 => 'This account is not authorized for the requested operation.',
    503 => 'Backend authentication is not configured or is unavailable. Run the local setup procedure.',
    _ => 'Backend authentication failed (HTTP $status).',
  };

  void _setSignedOut(int attempt, String? message) {
    if (attempt == _restoreAttempt) {
      state = AuthenticationState.signedOut(message: message);
    }
  }
}

class _AuthenticationTransportFailure implements Exception {
  final String message;
  const _AuthenticationTransportFailure(this.message);
}

final authenticationProvider =
    NotifierProvider<AuthenticationController, AuthenticationState>(
      AuthenticationController.new,
    );
