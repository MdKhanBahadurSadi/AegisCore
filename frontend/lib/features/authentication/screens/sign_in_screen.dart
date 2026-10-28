import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../services/authentication.dart';

class SignInScreen extends ConsumerStatefulWidget {
  final String? message;

  const SignInScreen({super.key, this.message});

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final _username = TextEditingController();
  final _password = TextEditingController();
  bool _hidePassword = true;

  @override
  void dispose() {
    _username.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _signIn() async {
    final username = _username.text;
    final password = _password.text;
    _password.clear();
    await ref.read(authenticationProvider.notifier).signIn(username, password);
  }

  @override
  Widget build(BuildContext context) {
    final authentication = ref.watch(authenticationProvider);
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Icon(
                      Icons.shield_outlined,
                      color: AppTheme.primaryTeal,
                      size: 42,
                    ),
                    const SizedBox(height: 14),
                    const Text(
                      'Sign in to AEGISCORE AI',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Live Backend Mode · local account required',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: AppTheme.textSecondary),
                    ),
                    const SizedBox(height: 24),
                    if (widget.message != null) ...[
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceVariant,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: AppTheme.cardBorder),
                        ),
                        child: Text(
                          widget.message!,
                          style: const TextStyle(color: AppTheme.textSecondary),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    TextField(
                      controller: _username,
                      enabled: authentication.status != AuthenticationStatus.loading,
                      textInputAction: TextInputAction.next,
                      autofillHints: const [AutofillHints.username],
                      decoration: const InputDecoration(
                        labelText: 'Username',
                        prefixIcon: Icon(Icons.person_outline),
                      ),
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: _password,
                      enabled: authentication.status != AuthenticationStatus.loading,
                      obscureText: _hidePassword,
                      onSubmitted: (_) => _signIn(),
                      autofillHints: const [AutofillHints.password],
                      decoration: InputDecoration(
                        labelText: 'Password',
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          tooltip: _hidePassword ? 'Show password' : 'Hide password',
                          onPressed: () => setState(() => _hidePassword = !_hidePassword),
                          icon: Icon(
                            _hidePassword ? Icons.visibility : Icons.visibility_off,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 22),
                    ElevatedButton.icon(
                      onPressed: authentication.status == AuthenticationStatus.loading
                          ? null
                          : _signIn,
                      icon: authentication.status == AuthenticationStatus.loading
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.login),
                      label: const Text('Sign in'),
                    ),
                    const SizedBox(height: 14),
                    const Text(
                      'Live data is unavailable until the local backend is configured and authenticated. Demo Fixture Mode remains separate and is never used as an authentication fallback.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: AppTheme.textMuted,
                        fontSize: 11,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
