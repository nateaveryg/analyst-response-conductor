import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/workspace.dart';
import '../models/governance.dart';
import '../models/a2ui_surface.dart';

class ApiService {
  final String baseUrl;
  final http.Client _client;

  ApiService({
    this.baseUrl = '',
    http.Client? client,
  }) : _client = client ?? http.Client();

  Map<String, String> _headers([String? userEmail]) => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    if (userEmail != null) 'X-Goog-Authenticated-User-Email': userEmail,
  };

  Future<Map<String, dynamic>> sendChatMessage({
    required String message,
    String? actionId,
    Map<String, dynamic>? contextData,
    String? workspaceId,
    String? userEmail,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/a2ui/chat');
    final body = jsonEncode({
      'message': message,
      if (actionId != null) 'action_id': actionId,
      if (contextData != null) 'context_data': contextData,
      if (workspaceId != null) 'workspace_id': workspaceId,
    });

    final res = await _client.post(uri, headers: _headers(userEmail), body: body);
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return jsonDecode(res.body) as Map<String, dynamic>;
    }
    throw Exception('Chat API request failed with status: ${res.statusCode} (${res.body})');
  }

  Future<List<Workspace>> listWorkspaces([String? userEmail]) async {
    final uri = Uri.parse('$baseUrl/api/v1/workspaces');
    final res = await _client.get(uri, headers: _headers(userEmail));
    if (res.statusCode == 200) {
      final List raw = jsonDecode(res.body);
      return raw.map((w) => Workspace.fromJson(w)).toList();
    }
    throw Exception('Failed to list workspaces: ${res.statusCode}');
  }

  Future<Workspace> createWorkspace({
    required String name,
    required String reportType,
    required String description,
    String? userEmail,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/workspaces');
    final body = jsonEncode({
      'name': name,
      'report_type': reportType,
      'description': description,
    });

    final res = await _client.post(uri, headers: _headers(userEmail), body: body);
    if (res.statusCode == 201 || res.statusCode == 200) {
      return Workspace.fromJson(jsonDecode(res.body));
    }
    throw Exception('Failed to create workspace: ${res.statusCode}');
  }

  Future<GovernanceRadarReport> getGovernanceRadar(String workspaceId, [String? userEmail]) async {
    final uri = Uri.parse('$baseUrl/api/v1/governance/scorecard?workspace_id=$workspaceId');
    final res = await _client.get(uri, headers: _headers(userEmail));
    if (res.statusCode == 200) {
      return GovernanceRadarReport.fromJson(jsonDecode(res.body));
    }
    throw Exception('Failed to fetch governance scorecard: ${res.statusCode}');
  }

  Future<DeficitAttestationWaiver> signWaiver({
    required String waiverId,
    required String approverEmail,
    required String role,
    String? userEmail,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/governance/waivers/$waiverId/sign');
    final body = jsonEncode({
      'approver_email': approverEmail,
      'role': role,
    });

    final res = await _client.post(uri, headers: _headers(userEmail), body: body);
    if (res.statusCode == 200) {
      return DeficitAttestationWaiver.fromJson(jsonDecode(res.body));
    }
    throw Exception('Failed to sign waiver: ${res.statusCode}');
  }

  Future<Map<String, dynamic>> queryAgentEngine({
    required String prompt,
    String? workspaceId,
    String? evaluationType,
    String? userEmail,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/agent-engine/query');
    final body = jsonEncode({
      'prompt': prompt,
      if (workspaceId != null) 'workspace_id': workspaceId,
      if (evaluationType != null) 'evaluation_type': evaluationType,
    });

    final res = await _client.post(uri, headers: _headers(userEmail), body: body);
    if (res.statusCode == 200) {
      return jsonDecode(res.body) as Map<String, dynamic>;
    }
    throw Exception('Agent Engine query failed: ${res.statusCode}');
  }
}
