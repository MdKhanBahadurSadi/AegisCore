sealed class BackendException implements Exception {
  final String message;

  const BackendException(this.message);

  @override
  String toString() => message;
}

class BackendConnectionException extends BackendException {
  const BackendConnectionException()
    : super('Could not connect to the configured backend.');
}

class BackendTimeoutException extends BackendException {
  final String phase;

  const BackendTimeoutException(this.phase)
    : super('The backend $phase timed out. Check the service and try again.');
}

class BackendHttpException extends BackendException {
  final int statusCode;

  BackendHttpException(this.statusCode)
    : super('The backend request failed (HTTP $statusCode).');
}

class BackendAuthenticationException extends BackendException {
  const BackendAuthenticationException()
    : super('Your backend session expired. Sign in again.');
}

class BackendAuthorizationException extends BackendException {
  const BackendAuthorizationException()
    : super('The signed-in account is not authorized for this data.');
}

class BackendResponseException extends BackendException {
  const BackendResponseException()
    : super('The backend returned an invalid response.');
}

class UnsupportedBackendCapabilityException extends BackendException {
  final String capability;

  UnsupportedBackendCapabilityException(this.capability)
    : super('The configured backend does not provide $capability.');
}

String userFacingBackendError(Object error) {
  if (error is BackendHttpException) {
    return switch (error.statusCode) {
      400 || 422 =>
        'The backend rejected the target or request. Confirm the endpoint is registered and authorized.',
      404 => 'The requested assessment was not found.',
      409 =>
        'The assessment is running or has already reached a terminal state.',
      503 =>
        'The backend authorization or persistence service is currently unavailable.',
      >= 500 => 'The backend could not complete this request. Try again later.',
      _ => error.message,
    };
  }
  if (error is BackendException) return error.message;
  return 'Could not load data. Please try again.';
}
