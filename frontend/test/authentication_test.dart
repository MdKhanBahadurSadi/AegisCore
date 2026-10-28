import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:aegiscore_ui/core/navigation/authenticated_shell.dart';
import 'package:aegiscore_ui/services/aegiscore_configuration.dart';
import 'package:aegiscore_ui/services/authentication.dart';
import 'package:aegiscore_ui/services/providers.dart';

void main() {
  final token = List.filled(43, 'Q').join();
  final liveConfiguration = AegisCoreConfiguration(
    mode: AegisCoreMode.live,
    baseUri: Uri.parse('http://127.0.0.1:8000/api/'),
  );

  test('Live Mode only accepts loopback backend addresses', () {
    expect(
      () => AegisCoreConfiguration(
        mode: AegisCoreMode.live,
        baseUri: Uri.parse('http://api.example.test/'),
      ),
      throwsArgumentError,
    );
    expect(
      AegisCoreConfiguration(
        mode: AegisCoreMode.live,
        baseUri: Uri.parse('http://[::1]:8000/'),
      ).baseUri.host,
      '::1',
    );
  });

  test('sign in stores only the bearer and sign out invalidates it', () async {
    final store = _MemoryTokenStorage();
    final authorizationHeaders = <String?>[];
    final client = MockClient((request) async {
      if (request.url.path == '/api/auth/login') {
        expect(jsonDecode(request.body), {
          'username': 'local-user',
          'password': 'local-password-never-stored',
        });
        return http.Response(
          jsonEncode({'access_token': token, 'token_type': 'bearer', 'expires_in': 1800}),
          200,
        );
      }
      if (request.url.path == '/api/auth/session') {
        authorizationHeaders.add(request.headers['Authorization']);
        return http.Response(
          jsonEncode({
            'authenticated': true,
            'username': 'local-user',
            'permissions': ['records:read', 'evidence:read'],
            'expires_in': 1799,
          }),
          200,
        );
      }
      if (request.url.path == '/api/auth/logout') {
        authorizationHeaders.add(request.headers['Authorization']);
        return http.Response('{"status":"signed_out"}', 200);
      }
      return http.Response('{}', 404);
    });
    final container = _container(liveConfiguration, store, client);
    addTearDown(container.dispose);
    addTearDown(client.close);

    container.read(authenticationProvider);
    await container
        .read(authenticationProvider.notifier)
        .signIn('local-user', 'local-password-never-stored');

    final signedIn = container.read(authenticationProvider);
    expect(signedIn.status, AuthenticationStatus.signedIn);
    expect(signedIn.accessToken, token);
    expect(store.token, token);
    expect(authorizationHeaders, ['Bearer $token']);

    await container.read(authenticationProvider.notifier).signOut();
    expect(container.read(authenticationProvider).status, AuthenticationStatus.signedOut);
    expect(store.token, isNull);
    expect(authorizationHeaders, ['Bearer $token', 'Bearer $token']);
  });

  test('expired restored session is deleted and shown as signed out', () async {
    final store = _MemoryTokenStorage()..token = token;
    final client = MockClient((request) async {
      expect(request.headers['Authorization'], 'Bearer $token');
      return http.Response('{"detail":"generic"}', 401);
    });
    final container = _container(liveConfiguration, store, client);
    addTearDown(container.dispose);
    addTearDown(client.close);

    container.read(authenticationProvider);
    await Future<void>.delayed(const Duration(milliseconds: 20));

    expect(container.read(authenticationProvider).status, AuthenticationStatus.signedOut);
    expect(container.read(authenticationProvider).message, contains('expired'));
    expect(store.token, isNull);
  });

  test('login failure leaves Live Mode unauthenticated without demo fallback', () async {
    final store = _MemoryTokenStorage();
    final client = MockClient((request) async {
      expect(request.url.path, '/api/auth/login');
      return http.Response('{"detail":"do not display backend body"}', 503);
    });
    final container = _container(liveConfiguration, store, client);
    addTearDown(container.dispose);
    addTearDown(client.close);

    container.read(authenticationProvider);
    await container
        .read(authenticationProvider.notifier)
        .signIn('local-user', 'wrong-password');

    expect(container.read(authenticationProvider).status, AuthenticationStatus.signedOut);
    expect(container.read(authenticationProvider).message, contains('not configured'));
    expect(container.read(aegisCoreRepositoryProvider).mode, AegisCoreMode.live);
    expect(store.token, isNull);
  });

  testWidgets('Live Mode hides the app until auth; Demo Mode stays separate', (
    tester,
  ) async {
    final store = _MemoryTokenStorage();
    final client = MockClient((_) async => http.Response('{}', 404));
    addTearDown(client.close);
    final liveRouter = _authTestRouter();
    addTearDown(liveRouter.dispose);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          aegisCoreConfigurationProvider.overrideWithValue(liveConfiguration),
          backendHttpClientProvider.overrideWithValue(client),
          sessionTokenStorageProvider.overrideWithValue(store),
        ],
        child: MaterialApp.router(routerConfig: liveRouter),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Sign in to AEGISCORE AI'), findsOneWidget);
    expect(find.text('private live page'), findsNothing);

    final demoClient = MockClient((_) async => http.Response('{}', 404));
    addTearDown(demoClient.close);
    final demoRouter = _authTestRouter();
    addTearDown(demoRouter.dispose);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          aegisCoreConfigurationProvider.overrideWithValue(
            AegisCoreConfiguration(
              mode: AegisCoreMode.demo,
              baseUri: Uri.parse('http://127.0.0.1:8000/'),
            ),
          ),
          backendHttpClientProvider.overrideWithValue(demoClient),
          sessionTokenStorageProvider.overrideWithValue(store),
        ],
        child: MaterialApp.router(routerConfig: demoRouter),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Sign in to AEGISCORE AI'), findsNothing);
    expect(find.text('private live page'), findsOneWidget);
  });
}

GoRouter _authTestRouter() => GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) =>
          const AuthenticatedShell(child: Text('private live page')),
    ),
  ],
);

ProviderContainer _container(
  AegisCoreConfiguration configuration,
  SessionTokenStorage storage,
  http.Client client,
) => ProviderContainer(
  overrides: [
    aegisCoreConfigurationProvider.overrideWithValue(configuration),
    sessionTokenStorageProvider.overrideWithValue(storage),
    backendHttpClientProvider.overrideWithValue(client),
  ],
);

class _MemoryTokenStorage implements SessionTokenStorage {
  String? token;

  @override
  Future<String?> read() async => token;

  @override
  Future<void> write(String value) async => token = value;

  @override
  Future<void> delete() async => token = null;
}
