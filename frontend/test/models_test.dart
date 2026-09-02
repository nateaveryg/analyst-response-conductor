import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import '../lib/models/workspace.dart';
import '../lib/models/a2ui_surface.dart';
import '../lib/models/governance.dart';
import '../lib/models/rfi_questionnaire.dart';

void main() {
  group('Workspace Model Tests', () {
    test('Deserializes workspace with co_editors_json', () {
      final json = {
        'id': 'ws-123',
        'name': 'Gartner MQ 2026',
        'report_type': 'CNAP',
        'description': 'Test workspace',
        'owner_email': 'owner@google.com',
        'co_editors_json': jsonEncode(['editor1@google.com', 'editor2@google.com']),
        'is_default': true,
        'can_edit': true,
        'current_phase': 2,
        'last_completed_step': 'narrative_strategy',
      };

      final ws = Workspace.fromJson(json);
      expect(ws.id, 'ws-123');
      expect(ws.name, 'Gartner MQ 2026');
      expect(ws.coEditors.length, 2);
      expect(ws.currentPhase, 2);
      expect(ws.canEdit, true);
    });
  });

  group('A2UI Surface Model Tests', () {
    test('Parses <a2ui-json> tag block successfully', () {
      final raw = '''
Here is the briefing:
<a2ui-json>
{
  "card_id": "card-intake",
  "title": "Phase 1: Criteria Document Intake",
  "phase": 1,
  "progress_percent": 14.0,
  "markdown_content": "### Upload Criteria Document",
  "fields": [
    {
      "id": "report_name",
      "label": "Analyst Report Name",
      "type": "text",
      "default_value": "DevSecOps Platforms, 2026",
      "required": true
    }
  ],
  "actions": [
    {
      "label": "Run Evaluation",
      "action_id": "submit_criteria_analysis",
      "style": "primary"
    }
  ]
}
</a2ui-json>
''';

      final surface = A2UISurfaceCard.tryParseA2UIBlock(raw);
      expect(surface, isNotNull);
      expect(surface!.cardId, 'card-intake');
      expect(surface.phase, 1);
      expect(surface.fields.length, 1);
      expect(surface.actions.length, 1);
      expect(surface.actions.first.actionId, 'submit_criteria_analysis');
    });

    test('Parses nested components[].properties from Go backend', () {
      final nestedJson = {
        'surface_id': 'phase1_intake',
        'card_id': 'card-intake',
        'phase': 1,
        'progress_percent': 14.0,
        'title': 'Phase 1: Universal Analyst Document Intake & Evaluation Scope',
        'components': [
          {
            'type': 'Container',
            'properties': {
              'style': {'padding': '12px'},
            }
          },
          {
            'type': 'Card',
            'properties': {
              'title': 'Phase 1: Universal Analyst Document Intake & Evaluation Scope',
              'subtitle': 'Step 1A: Document Link Intake & Context Ingestion',
              'description': 'Active Evaluation Scope: DevSecOps. 1A: Document Link Intake confirmed.',
              'fields': [
                {
                  'name': 'welcome_packet_url',
                  'label': 'Welcome Packet URL',
                  'type': 'text',
                  'placeholder': 'https://docs.google.com/...'
                }
              ],
              'actions': [
                {
                  'action_id': 'submit_criteria_analysis',
                  'label': 'Run Portfolio Eligibility Evaluation',
                  'primary': true
                }
              ]
            }
          }
        ]
      };

      final card = A2UISurfaceCard.fromJson(nestedJson);
      expect(card.cardId, 'card-intake');
      expect(card.phase, 1);
      expect(card.subtitle, 'Step 1A: Document Link Intake & Context Ingestion');
      expect(card.markdownContent, contains('Active Evaluation Scope'));
      expect(card.fields.length, 1);
      expect(card.fields.first.id, 'welcome_packet_url');
      expect(card.fields.first.label, 'Welcome Packet URL');
      expect(card.actions.length, 1);
      expect(card.actions.first.actionId, 'submit_criteria_analysis');
      expect(card.actions.first.style, 'primary');
    });
  });

  group('Governance Model Tests', () {
    test('Deserializes GovernanceRadarReport and DeficitAttestationWaiver', () {
      final json = {
        'workspace_id': 'ws-456',
        'overall_compliance_score': 0.98,
        'rag_grounding_fidelity': 0.99,
        'active_waivers_count': 1,
        'waivers_approved': true,
        'sovereign_residency_compliant': true,
        'sovereign_region': 'europe-west3',
        'oss_licenses_cleared': true,
        'commercial_rates_verified': true,
        'waivers': [
          {
            'waiver_id': 'w-1',
            'workspace_id': 'ws-456',
            'feature_name': 'Agent Mode',
            'current_status': 'PUBLIC_PREVIEW',
            'target_ga_date': '2026-10-01',
            'fallback_mitigation': 'Isolate to Module 5',
            'product_gm_approver': 'gm@google.com',
            'legal_counsel_approver': 'legal@google.com',
            'is_approved': true,
            'manifest_sha256': 'abc123sha'
          }
        ]
      };

      final report = GovernanceRadarReport.fromJson(json);
      expect(report.workspaceId, 'ws-456');
      expect(report.overallComplianceScore, 0.98);
      expect(report.waivers.length, 1);
      expect(report.waivers.first.isApproved, true);
      expect(report.waivers.first.productGmApprover, 'gm@google.com');
    });
  });

  group('RFI Questionnaire Model Tests', () {
    test('Deserializes RfiQuestionRow', () {
      final json = {
        'section_id': '1.1.1',
        'worksheet_tab': 'Tab 1: Architecture',
        'question_text': 'Describe serverless cold start latency.',
        'assigned_sme': 'serverless-sme@google.com',
        'source_rfi_title': 'Google Cloud Run Architecture 2026',
        'grounding_confidence_score': 98.8,
        'draft_response': 'Cloud Run delivers sub-50ms cold starts.',
        'offered_natively': 'Yes (Built-in)',
        'status': 'Approved'
      };

      final q = RfiQuestionRow.fromJson(json);
      expect(q.sectionId, '1.1.1');
      expect(q.groundingConfidenceScore, 98.8);
      expect(q.status, 'Approved');
    });
  });
}
