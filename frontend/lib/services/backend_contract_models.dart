/// Typed representation of the existing FastAPI `/health` response.
class BackendHealthResponse {
  final String status;

  const BackendHealthResponse({required this.status});

  factory BackendHealthResponse.fromJson(Object? json) {
    final map = _strictObject(json, const {'status'});
    final status = map['status'];
    if (status != 'ok') {
      throw const FormatException('Unexpected health response status.');
    }
    return BackendHealthResponse(status: status as String);
  }
}

/// Typed representation of FastAPI's current `/capabilities` response.
class BackendCapabilitiesResponse {
  final String service;
  final String version;
  final List<String> implemented;
  final List<String> notImplemented;

  const BackendCapabilitiesResponse({
    required this.service,
    required this.version,
    required this.implemented,
    required this.notImplemented,
  });

  factory BackendCapabilitiesResponse.fromJson(Object? json) {
    final map = _strictObject(json, const {
      'service',
      'version',
      'implemented',
      'not_implemented',
    });
    final implemented = map['implemented'];
    final notImplemented = map['not_implemented'];
    if (map['service'] != 'aegiscore-api' ||
        map['version'] != '0.1.0' ||
        implemented is! List ||
        notImplemented is! List ||
        !implemented.every((item) => item is String) ||
        !notImplemented.every((item) => item is String) ||
        !_capabilityIds.containsAll(implemented.cast<String>()) ||
        !_capabilityIds.containsAll(notImplemented.cast<String>())) {
      throw const FormatException('Unexpected capabilities response shape.');
    }
    return BackendCapabilitiesResponse(
      service: map['service'] as String,
      version: map['version'] as String,
      implemented: List<String>.unmodifiable(implemented.cast<String>()),
      notImplemented: List<String>.unmodifiable(notImplemented.cast<String>()),
    );
  }
}

const _capabilityIds = <String>{
  'api.health_endpoint',
  'api.capabilities_endpoint',
  'api.approved_evidence_endpoints',
  'api.persisted_workflow_read_endpoints',
  'api.dashboard_summary_endpoint',
  'api.local_authentication',
  'api.read_permission_authorization',
  'api.loopback_access_boundary',
  'safety.in_memory_policy_contracts',
  'safety.fake_transport_only_guarded_execution_contract',
  'backend.real_target_transport',
  'backend.rag',
  'backend.multi_agent_orchestration',
  'backend.vulnerability_assessment_workflow',
  'backend.external_llm_provider',
  'backend.persistent_application_storage',
};

Map<String, Object?> _strictObject(Object? json, Set<String> expectedKeys) {
  if (json is! Map<String, dynamic> ||
      json.keys.toSet().length != expectedKeys.length ||
      !json.keys.toSet().containsAll(expectedKeys)) {
    throw const FormatException('Unexpected backend response shape.');
  }
  return json;
}
