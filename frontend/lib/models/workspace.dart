import 'dart:convert';

class Workspace {
  final String id;
  final String name;
  final String reportType;
  final String description;
  final String ownerEmail;
  final List<String> coEditors;
  final bool isDefault;
  final bool canEdit;
  final int currentPhase;
  final String lastCompletedStep;

  Workspace({
    required this.id,
    required this.name,
    required this.reportType,
    required this.description,
    required this.ownerEmail,
    required this.coEditors,
    required this.isDefault,
    required this.canEdit,
    this.currentPhase = 1,
    this.lastCompletedStep = 'welcome_briefing',
  });

  factory Workspace.fromJson(Map<String, dynamic> json) {
    List<String> editors = [];
    if (json['co_editors_json'] != null) {
      try {
        final parsed = jsonDecode(json['co_editors_json']);
        if (parsed is List) {
          editors = parsed.map((e) => e.toString()).toList();
        }
      } catch (_) {}
    } else if (json['co_editors'] != null && json['co_editors'] is List) {
      editors = (json['co_editors'] as List).map((e) => e.toString()).toList();
    }

    return Workspace(
      id: json['id']?.toString() ?? '',
      name: json['name'] ?? 'Untitled Workspace',
      reportType: json['report_type'] ?? 'DevSecOps Platforms, 2026',
      description: json['description'] ?? '',
      ownerEmail: json['owner_email'] ?? 'enterprise-analyst@google.com',
      coEditors: editors,
      isDefault: json['is_default'] ?? false,
      canEdit: json['can_edit'] ?? true,
      currentPhase: json['current_phase'] ?? 1,
      lastCompletedStep: json['last_completed_step'] ?? 'welcome_briefing',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'report_type': reportType,
    'description': description,
    'owner_email': ownerEmail,
    'co_editors': coEditors,
    'is_default': isDefault,
    'can_edit': canEdit,
    'current_phase': currentPhase,
    'last_completed_step': lastCompletedStep,
  };
}
