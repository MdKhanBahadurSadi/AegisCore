import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/authentication/screens/sign_in_screen.dart';
import '../../services/aegiscore_configuration.dart';
import '../../services/authentication.dart';
import '../../services/backend_http_client.dart';
import 'app_scaffold.dart';

/// Live Backend Mode gates the complete application shell on backend auth.
/// Demo Fixture Mode remains an independent local-only path.
class AuthenticatedShell extends ConsumerWidget {
  final Widget child;

  const AuthenticatedShell({super.key, required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final configuration = ref.watch(aegisCoreConfigurationProvider);
    if (configuration.mode == AegisCoreMode.demo) {
      return AppScaffold(child: child);
    }

    final authentication = ref.watch(authenticationProvider);
    return switch (authentication.status) {
      AuthenticationStatus.demo => AppScaffold(child: child),
      AuthenticationStatus.loading => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
      AuthenticationStatus.signedOut => SignInScreen(
        message: authentication.message,
      ),
      AuthenticationStatus.signedIn => AppScaffold(child: child),
    };
  }
}
