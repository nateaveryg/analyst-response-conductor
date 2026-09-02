import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../models/a2ui_surface.dart';

class A2UICardRenderer extends StatefulWidget {
  final A2UISurfaceCard card;
  final Function(String actionId, Map<String, dynamic> payload) onActionTriggered;
  final bool isReadOnly;

  const A2UICardRenderer({
    Key? key,
    required this.card,
    required this.onActionTriggered,
    this.isReadOnly = false,
  }) : super(key: key);

  @override
  State<A2UICardRenderer> createState() => _A2UICardRendererState();
}

class _A2UICardRendererState extends State<A2UICardRenderer> {
  final Map<String, dynamic> _formData = {};

  @override
  void initState() {
    super.initState();
    for (final field in widget.card.fields) {
      if (field.defaultValue != null) {
        _formData[field.id] = field.defaultValue;
      }
    }
  }

  Color _getButtonColor(String style) {
    switch (style.toLowerCase()) {
      case 'danger':
        return const Color(0xFFD93025);
      case 'success':
        return const Color(0xFF137333);
      case 'secondary':
        return const Color(0xFF5F6368);
      case 'primary':
      default:
        return const Color(0xFF1A73E8);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      elevation: 2,
      margin: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 4.0),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.grey.withOpacity(0.2)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header Row (Phase Badge + Title)
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1A73E8).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0xFF1A73E8).withOpacity(0.3)),
                  ),
                  child: Text(
                    'Phase ${widget.card.phase}',
                    style: const TextStyle(
                      color: Color(0xFF1A73E8),
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.card.title,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      if (widget.card.subtitle != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          widget.card.subtitle!,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: Colors.grey.shade600,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
            const Divider(height: 24),

            // Markdown Content
            if (widget.card.markdownContent != null && widget.card.markdownContent!.isNotEmpty) ...[
              MarkdownBody(
                data: widget.card.markdownContent!,
                selectable: true,
                styleSheet: MarkdownStyleSheet.fromTheme(theme).copyWith(
                  p: theme.textTheme.bodyMedium?.copyWith(height: 1.5),
                  h3: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold, color: const Color(0xFF1A73E8)),
                  tableBorder: TableBorder.all(color: Colors.grey.withOpacity(0.3), width: 1),
                  tableHead: const TextStyle(fontWeight: FontWeight.bold, backgroundColor: Color(0xFFF1F3F4)),
                  tableBody: const TextStyle(fontSize: 13),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Input Fields Form
            if (widget.card.fields.isNotEmpty) ...[
              ...widget.card.fields.map((field) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${field.label}${field.required ? ' *' : ''}',
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                      ),
                      const SizedBox(height: 6),
                      if (field.type == 'select' && field.options != null)
                        DropdownButtonFormField<String>(
                          value: _formData[field.id]?.toString(),
                          decoration: InputDecoration(
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          ),
                          items: field.options!.map((opt) {
                            return DropdownMenuItem(value: opt, child: Text(opt, style: const TextStyle(fontSize: 13)));
                          }).toList(),
                          onChanged: widget.isReadOnly
                              ? null
                              : (val) {
                                  setState(() => _formData[field.id] = val);
                                },
                        )
                      else if (field.type == 'textarea')
                        TextFormField(
                          initialValue: _formData[field.id]?.toString() ?? '',
                          maxLines: 4,
                          readOnly: widget.isReadOnly,
                          decoration: InputDecoration(
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            hintText: 'Enter ${field.label.toLowerCase()}...',
                            contentPadding: const EdgeInsets.all(12),
                          ),
                          onChanged: (val) => _formData[field.id] = val,
                        )
                      else
                        TextFormField(
                          initialValue: _formData[field.id]?.toString() ?? '',
                          readOnly: widget.isReadOnly,
                          decoration: InputDecoration(
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            hintText: 'Enter ${field.label.toLowerCase()}...',
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          ),
                          onChanged: (val) => _formData[field.id] = val,
                        ),
                    ],
                  ),
                );
              }).toList(),
              const SizedBox(height: 8),
            ],

            // Action Buttons
            if (widget.card.actions.isNotEmpty) ...[
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: widget.card.actions.map((act) {
                  final btnColor = _getButtonColor(act.style);
                  return ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: btnColor,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    icon: const Icon(Icons.play_arrow_rounded, size: 18),
                    label: Text(act.label, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    onPressed: widget.isReadOnly
                        ? null
                        : () {
                            final payload = Map<String, dynamic>.from(_formData);
                            if (act.payload != null) {
                              payload.addAll(act.payload!);
                            }
                            widget.onActionTriggered(act.actionId, payload);
                          },
                  );
                }).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
