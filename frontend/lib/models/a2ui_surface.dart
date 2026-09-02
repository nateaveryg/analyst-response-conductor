import 'dart:convert';

class A2UIButton {
  final String label;
  final String actionId;
  final String style; // primary, secondary, danger, success
  final Map<String, dynamic>? payload;

  A2UIButton({
    required this.label,
    required this.actionId,
    this.style = 'primary',
    this.payload,
  });

  factory A2UIButton.fromJson(Map<String, dynamic> json) => A2UIButton(
    label: json['label'] ?? '',
    actionId: json['action_id'] ?? json['id'] ?? '',
    style: json['style'] ?? (json['primary'] == false ? 'secondary' : 'primary'),
    payload: json['payload'] is Map ? Map<String, dynamic>.from(json['payload']) : null,
  );
}

class A2UIField {
  final String id;
  final String label;
  final String type; // text, textarea, select, file, number
  final dynamic defaultValue;
  final List<String>? options;
  final bool required;

  A2UIField({
    required this.id,
    required this.label,
    this.type = 'text',
    this.defaultValue,
    this.options,
    this.required = false,
  });

  factory A2UIField.fromJson(Map<String, dynamic> json) => A2UIField(
    id: json['id'] ?? json['name'] ?? '',
    label: json['label'] ?? json['name'] ?? '',
    type: json['type'] ?? 'text',
    defaultValue: json['default_value'] ?? json['placeholder'],
    options: json['options'] != null ? List<String>.from(json['options']) : null,
    required: json['required'] ?? false,
  );
}

class A2UISurfaceCard {
  final String cardId;
  final String title;
  final String? subtitle;
  final int phase;
  final double progressPercent;
  final String? markdownContent;
  final List<A2UIField> fields;
  final List<A2UIButton> actions;
  final Map<String, dynamic> metadata;

  A2UISurfaceCard({
    required this.cardId,
    required this.title,
    this.subtitle,
    required this.phase,
    this.progressPercent = 0.0,
    this.markdownContent,
    this.fields = const [],
    this.actions = const [],
    this.metadata = const {},
  });

  factory A2UISurfaceCard.fromJson(Map<String, dynamic> json) {
    var rawFields = List<dynamic>.from(json['fields'] as List? ?? []);
    var rawActions = List<dynamic>.from(json['actions'] as List? ?? []);
    String cardId = json['card_id'] ?? json['id'] ?? 'card-unknown';
    String title = json['title'] ?? '';
    String? subtitle = json['subtitle'];
    int phase = json['phase'] ?? 1;
    double progressPercent = (json['progress_percent'] as num?)?.toDouble() ?? 0.0;
    String? markdownContent = json['markdown_content'] ?? json['content'];
    Map<String, dynamic> metadata = Map<String, dynamic>.from(json['metadata'] as Map? ?? {});

    // Parse nested component properties (components[].properties) from Go backend
    if (json['components'] is List) {
      final components = json['components'] as List;
      for (final comp in components) {
        if (comp is Map) {
          final compMap = Map<String, dynamic>.from(comp);
          final props = compMap['properties'];
          if (props is Map) {
            final propsMap = Map<String, dynamic>.from(props);
            if (propsMap['card_id'] != null && cardId == 'card-unknown') {
              cardId = propsMap['card_id'].toString();
            }
            if (propsMap['title'] != null && title.isEmpty) {
              title = propsMap['title'].toString();
            }
            if (propsMap['subtitle'] != null && (subtitle == null || subtitle.isEmpty)) {
              subtitle = propsMap['subtitle'].toString();
            }
            if (markdownContent == null || markdownContent.isEmpty) {
              if (propsMap['markdown_content'] != null) {
                markdownContent = propsMap['markdown_content'].toString();
              } else if (propsMap['content'] != null) {
                markdownContent = propsMap['content'].toString();
              } else if (propsMap['description'] != null) {
                markdownContent = propsMap['description'].toString();
              }
            }
            if (propsMap['fields'] is List) {
              rawFields.addAll(propsMap['fields'] as List);
            }
            if (propsMap['actions'] is List) {
              rawActions.addAll(propsMap['actions'] as List);
            }
            // Preserve other properties into metadata
            propsMap.forEach((key, val) {
              if (!const {'fields', 'actions', 'title', 'subtitle', 'description', 'markdown_content', 'content', 'children'}.contains(key)) {
                metadata[key] = val;
              }
            });
          }
        }
      }
    }

    return A2UISurfaceCard(
      cardId: cardId,
      title: title,
      subtitle: subtitle,
      phase: phase,
      progressPercent: progressPercent,
      markdownContent: markdownContent,
      fields: rawFields.map((f) {
        if (f is Map) {
          return A2UIField.fromJson(Map<String, dynamic>.from(f));
        }
        return null;
      }).whereType<A2UIField>().toList(),
      actions: rawActions.map((a) {
        if (a is Map) {
          return A2UIButton.fromJson(Map<String, dynamic>.from(a));
        }
        return null;
      }).whereType<A2UIButton>().toList(),
      metadata: metadata,
    );
  }

  static A2UISurfaceCard? tryParseA2UIBlock(String rawContent) {
    final regex = RegExp(r'<a2ui-json>([\s\S]*?)<\/a2ui-json>');
    final match = regex.firstMatch(rawContent);
    if (match != null && match.group(1) != null) {
      try {
        final decoded = jsonDecode(match.group(1)!.trim());
        if (decoded is Map<String, dynamic>) {
          return A2UISurfaceCard.fromJson(decoded);
        }
      } catch (_) {}
    }
    return null;
  }
}
