/// UI-side guard matching the project's local-only lab target restriction.
/// This validates the form only; it does not authorize backend execution.
bool isAuthorizedLocalLabTarget(String targetUrl) {
  final uri = Uri.tryParse(targetUrl);
  if (uri == null || uri.scheme != 'http' || uri.userInfo.isNotEmpty) {
    return false;
  }
  // The backend binds authorization to a numeric loopback literal; DNS names
  // such as localhost are deliberately not accepted for target execution.
  final isLocal = uri.host == '127.0.0.1';
  return isLocal && (uri.port == 3000 || uri.port == 8080);
}
