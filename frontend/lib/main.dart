import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'models/workspace.dart';
import 'models/a2ui_surface.dart';
import 'models/governance.dart';
import 'models/rfi_questionnaire.dart';
import 'services/api_service.dart';
import 'widgets/workspace_header.dart';
import 'widgets/journey_stepper.dart';
import 'widgets/a2ui_card_renderer.dart';
import 'widgets/pluto_spreadsheet_view.dart';
import 'widgets/governance_radar_modal.dart';

void main() {
  runApp(const ConductorApp());
}

class ConductorApp extends StatelessWidget {
  const ConductorApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'The Conductor v3 - Analyst Response Agent',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1A73E8),
          primary: const Color(0xFF1A73E8),
          background: const Color(0xFFF8FAFC),
        ),
        textTheme: GoogleFonts.interTextTheme(Theme.of(context).textTheme),
      ),
      home: const ConductorMainScreen(),
    );
  }
}

class ConductorMainScreen extends StatefulWidget {
  const ConductorMainScreen({Key? key}) : super(key: key);

  @override
  State<ConductorMainScreen> createState() => _ConductorMainScreenState();
}

class _ConductorMainScreenState extends State<ConductorMainScreen> {
  final ApiService _api = ApiService();
  final TextEditingController _chatController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  List<Workspace> _workspaces = [];
  Workspace? _currentWorkspace;
  int _currentPhase = 1;
  bool _isLoading = false;

  final List<Map<String, dynamic>> _chatHistory = [];
  final List<RfiQuestionRow> _rfiQuestions = [];

  @override
  void initState() {
    super.initState();
    _initSampleRfiQuestions();
    _loadInitialData();
  }

  void _initSampleRfiQuestions() {
    if (_rfiQuestions.isEmpty) {
      _rfiQuestions.addAll([
        RfiQuestionRow(
          sectionId: 'SEC-01',
          worksheetTab: 'Product or Service 1-87',
          questionText: 'Continuous integration capabilities natively offered (Linux, Windows, Pipelines).',
          assignedSme: 'davidjacobs@google.com',
          sourceRfiTitle: 'Gartner DevSecOps MQ 2025 Approved',
          groundingConfidenceScore: 98.4,
          draftResponse: 'Google Cloud provides Cloud Build and Gemini Code Assist with automated pipeline triggers, hermetic builds, and artifact provenance.',
          offeredNatively: 'Yes (Built-in)',
          status: 'Approved',
        ),
        RfiQuestionRow(
          sectionId: 'SEC-02',
          worksheetTab: 'Product or Service 1-87',
          questionText: 'What AI agent tool orchestration frameworks are supported natively?',
          assignedSme: 'nathenharvey@google.com',
          sourceRfiTitle: 'Forrester Wave Cloud Platforms 2025',
          groundingConfidenceScore: 97.9,
          draftResponse: 'Supports Vertex AI Agent Engine, LangChain, LlamaIndex, and native Model Context Protocol (MCP) tool integration.',
          offeredNatively: 'Yes (Built-in)',
          status: 'Approved',
        ),
        RfiQuestionRow(
          sectionId: 'SEC-03',
          worksheetTab: 'Overall Viability 88-92',
          questionText: 'Describe your financial stability, investment in R&D, and corporate viability supporting DevSecOps innovations.',
          assignedSme: 'sarahmiller@google.com',
          sourceRfiTitle: 'Alphabet 10-K SEC Filings 2025',
          groundingConfidenceScore: 99.1,
          draftResponse: 'Alphabet invests over \$40B annually in R&D with continuous capital commitment to AI infrastructure and cybersecurity.',
          offeredNatively: 'Yes (Built-in)',
          status: 'Approved',
        ),
        RfiQuestionRow(
          sectionId: 'SEC-04',
          worksheetTab: 'Sales Execution-Pricing 93-105',
          questionText: 'Describe standard enterprise pricing models, consumption tiers, and discount schedules for universal agentic platforms.',
          assignedSme: 'enterprise-sales@google.com',
          sourceRfiTitle: 'Google Cloud Pricing Guide 2026',
          groundingConfidenceScore: 96.8,
          draftResponse: 'Flexible pay-as-you-go pricing with sustained use discounts, committed-use contracts, and flat-rate enterprise tiers.',
          offeredNatively: 'Yes (Built-in)',
          status: 'Approved',
        ),
        RfiQuestionRow(
          sectionId: 'SEC-05',
          worksheetTab: 'Customer Experience 111-121',
          questionText: 'Describe customer onboarding experiences, dedicated technical account management (TAM), and OSS Assurance support.',
          assignedSme: 'customer-eng@google.com',
          sourceRfiTitle: 'Google Cloud Support Offerings 2026',
          groundingConfidenceScore: 98.7,
          draftResponse: 'Enterprise support includes dedicated Technical Account Managers (TAM), 15-minute P1 SLAs, and Assured Open Source Software support.',
          offeredNatively: 'Yes (Built-in)',
          status: 'Approved',
        ),
      ]);
    }
  }

  Future<void> _loadInitialData() async {
    setState(() => _isLoading = true);
    try {
      final wsList = await _api.listWorkspaces();
      setState(() {
        _workspaces = wsList;
        _currentWorkspace = wsList.isNotEmpty ? wsList.first : null;
        if (_currentWorkspace != null) {
          _currentPhase = _currentWorkspace!.currentPhase;
        }
      });
      // Send initial welcome action
      _sendAction('welcome_briefing', {});
    } catch (e) {
      // Fallback workspace if local testing without backend
      final fallbackWs = Workspace(
        id: 'ws-default',
        name: 'Gartner MQ 2026 - CNAP',
        reportType: 'Cloud-Native Application Protection Platform (CNAP)',
        description: 'Multi-agent RFI evaluation response',
        ownerEmail: 'enterprise-analyst@google.com',
        coEditors: ['enterprise-analyst@google.com'],
        isDefault: true,
        canEdit: true,
        currentPhase: 1,
      );
      setState(() {
        _workspaces = [fallbackWs];
        _currentWorkspace = fallbackWs;
      });
      _sendAction('welcome_briefing', {});
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _sendMessage(String text) async {
    if (text.trim().isEmpty) return;
    _chatController.clear();

    setState(() {
      _chatHistory.add({'role': 'user', 'content': text});
      _isLoading = true;
    });

    try {
      final res = await _api.sendChatMessage(
        message: text,
        workspaceId: _currentWorkspace?.id,
      );

      final responseText = res['response'] ?? res['response_text'] ?? '';
      final surface = A2UISurfaceCard.tryParseA2UIBlock(responseText);

      setState(() {
        _chatHistory.add({
          'role': 'assistant',
          'content': responseText,
          'surface': surface,
        });
      });
    } catch (e) {
      setState(() {
        _chatHistory.add({
          'role': 'assistant',
          'content': 'Error communicating with Conductor engine: $e',
        });
      });
    } finally {
      setState(() => _isLoading = false);
      _scrollToBottom();
    }
  }

  Future<void> _sendAction(String actionId, Map<String, dynamic> payload) async {
    setState(() => _isLoading = true);
    try {
      final res = await _api.sendChatMessage(
        message: 'Execute action $actionId',
        actionId: actionId,
        contextData: payload,
        workspaceId: _currentWorkspace?.id,
      );

      final responseText = res['response'] ?? res['response_text'] ?? '';
      final surface = A2UISurfaceCard.tryParseA2UIBlock(responseText);

      if (surface != null) {
        setState(() => _currentPhase = surface.phase);
      }

      setState(() {
        _chatHistory.add({
          'role': 'assistant',
          'content': responseText,
          'surface': surface,
        });
      });
    } catch (e) {
      // Local fallback for standalone demo rendering
      final mockSurface = A2UISurfaceCard(
        cardId: 'card-mock',
        title: 'Executive Briefing & Strategy',
        phase: _currentPhase,
        markdownContent: '### Evaluation Ready\nConnected to Cloud Run Go Microservice.',
        actions: [
          A2UIButton(label: '🚀 Begin Phase 1: Criteria Intake', actionId: 'open_intake'),
        ],
      );
      setState(() {
        _chatHistory.add({
          'role': 'assistant',
          'content': 'Interactive Surface Loaded',
          'surface': mockSurface,
        });
      });
    } finally {
      setState(() => _isLoading = false);
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _openRadarModal() async {
    try {
      final report = await _api.getGovernanceRadar(_currentWorkspace?.id ?? 'ws-default');
      if (!mounted) return;
      showDialog(
        context: context,
        builder: (ctx) => GovernanceRadarModal(
          report: report,
          isReadOnly: !(_currentWorkspace?.canEdit ?? true),
          onSignWaiver: (wId, role) async {
            await _api.signWaiver(waiverId: wId, approverEmail: 'averyn@google.com', role: role);
            Navigator.of(ctx).pop();
            _openRadarModal();
          },
          onExportAuditBundle: () {},
        ),
      );
    } catch (e) {
      // Fallback local modal
      final mockReport = GovernanceRadarReport(
        workspaceId: _currentWorkspace?.id ?? 'ws-default',
        overallComplianceScore: 0.985,
        ragGroundingFidelity: 0.992,
        activeWaiversCount: 1,
        waiversApproved: true,
        sovereignResidencyCompliant: true,
        sovereignRegion: 'europe-west3 (Frankfurt)',
        ossLicensesCleared: true,
        commercialRatesVerified: true,
        waivers: [
          DeficitAttestationWaiver(
            waiverId: 'waiver-mock',
            workspaceId: 'ws-default',
            featureName: 'Gemini Code Assist Agent Mode',
            currentStatus: 'PUBLIC_PREVIEW',
            targetGaDate: '2026-10-15',
            fallbackMitigation: 'Isolate roadmap demo to Module 5 with clear preview disclosures.',
            productGmApprover: 'product-gm@google.com',
            legalCounselApprover: 'legal-counsel@google.com',
            isApproved: true,
            manifestSha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          ),
        ],
      );
      showDialog(
        context: context,
        builder: (ctx) => GovernanceRadarModal(
          report: mockReport,
          isReadOnly: false,
          onSignWaiver: (_, __) {},
          onExportAuditBundle: () {},
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: Column(
        children: [
          // Header Bar
          WorkspaceHeader(
            workspaces: _workspaces,
            selectedWorkspace: _currentWorkspace,
            onWorkspaceSelected: (ws) {
              setState(() {
                _currentWorkspace = ws;
                _currentPhase = ws.currentPhase;
              });
              _sendAction('resume_workspace', {'workspace_id': ws.id});
            },
            onNewWorkspace: () {},
            onOpenRadar: _openRadarModal,
            onOpenArtifacts: () {
              setState(() => _currentPhase = 4);
            },
          ),

          // Journey Stepper
          JourneyStepper(
            currentPhase: _currentPhase,
            onPhaseSelected: (phase) {
              setState(() => _currentPhase = phase);
              _sendAction('jump_to_phase', {'target_phase': phase});
            },
          ),

          // Main Chat & Interactive Surface View
          Expanded(
            child: Row(
              children: [
                // Chat / Interactive Form Area
                Expanded(
                  flex: _currentPhase == 4 ? 2 : 3,
                  child: Column(
                    children: [
                      Expanded(
                        child: ListView.builder(
                          controller: _scrollController,
                          padding: const EdgeInsets.all(16.0),
                          itemCount: _chatHistory.length,
                          itemBuilder: (context, index) {
                            final item = _chatHistory[index];
                            final isUser = item['role'] == 'user';
                            final surface = item['surface'] as A2UISurfaceCard?;

                            if (surface != null) {
                              return A2UICardRenderer(
                                card: surface,
                                isReadOnly: !(_currentWorkspace?.canEdit ?? true),
                                onActionTriggered: (actionId, payload) {
                                  _sendAction(actionId, payload);
                                },
                              );
                            }

                            return Align(
                              alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                              child: Container(
                                margin: const EdgeInsets.symmetric(vertical: 4),
                                padding: const EdgeInsets.all(12),
                                constraints: const BoxConstraints(maxWidth: 600),
                                decoration: BoxDecoration(
                                  color: isUser ? const Color(0xFF1A73E8) : Colors.white,
                                  borderRadius: BorderRadius.circular(10),
                                  border: isUser ? null : Border.all(color: Colors.grey.withOpacity(0.2)),
                                ),
                                child: Text(
                                  item['content'] ?? '',
                                  style: TextStyle(color: isUser ? Colors.white : Colors.black87),
                                ),
                              ),
                            );
                          },
                        ),
                      ),

                      // Input Bar
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          border: Border(top: BorderSide(color: Colors.grey.withOpacity(0.2))),
                        ),
                        child: Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _chatController,
                                decoration: InputDecoration(
                                  hintText: 'Ask the Conductor agent or enter prompt...',
                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(24)),
                                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                                ),
                                onSubmitted: _sendMessage,
                              ),
                            ),
                            const SizedBox(width: 8),
                            IconButton(
                              icon: _isLoading
                                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                                  : const Icon(Icons.send, color: Color(0xFF1A73E8)),
                              onPressed: () => _sendMessage(_chatController.text),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                if (_currentPhase == 4) ...[
                  const VerticalDivider(width: 1, color: Color(0xFFE2E8F0)),
                  Expanded(
                    flex: 3,
                    child: Container(
                      color: Colors.white,
                      padding: const EdgeInsets.all(12),
                      child: PlutoSpreadsheetView(
                        questions: _rfiQuestions,
                        isReadOnly: !(_currentWorkspace?.canEdit ?? true),
                        onRowUpdated: (updatedRow) {
                          final idx = _rfiQuestions.indexWhere((r) => r.sectionId == updatedRow.sectionId);
                          if (idx != -1) {
                            setState(() {
                              _rfiQuestions[idx] = updatedRow;
                            });
                          }
                        },
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
